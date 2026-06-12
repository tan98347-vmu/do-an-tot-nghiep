# compliance_checker.py được thiết kế để đánh giá mức độ tuân thủ của một văn bản dựa trên các yêu cầu đã được định nghĩa trước đó. Nó sử dụng một mô hình ngôn ngữ lớn (LLM) để phân tích văn bản và so sánh với các yêu cầu, sau đó trả về một kết quả dưới dạng JSON cho biết liệu văn bản có tuân thủ hay không và nếu không, những mục nào đang thiếu và giải thích lý do. Các chức năng chính của ComplianceChecker bao gồm việc chia nhỏ văn bản thành các phần nhỏ hơn nếu cần thiết, xây dựng prompt cho LLM, gọi LLM và xử lý phản hồi để đảm bảo rằng nó trả về dữ liệu hợp lệ theo schema đã định nghĩa.


from __future__ import annotations

import concurrent.futures
import hashlib
import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from accounts.tenancy import resolve_ai_config
from ai_engine.rag_engine import get_llm

JSON_SCHEMA_PROMPT = (
    'Bạn là hệ thống đánh giá tuân thủ.\n'
    'Hãy đối chiếu VĂN BẢN với CÁC YÊU CẦU trong prompt quy trình.\n'
    'TRẢ VỀ DUY NHẤT JSON theo schema:\n'
    '{\n'
    '  "passed": true | false,\n'
    '  "items_missing": [{"requirement": "...", "explanation": "..."}]\n'
    '}\n'
    'NGHIÊM CẤM trả thêm văn bản ngoài JSON.'
)

_CODE_FENCE_RE = re.compile(r'^\s*```(?:json)?\s*|\s*```\s*$', re.IGNORECASE)


# class ComplianceLLMError là lỗi chung cho luồng kiểm tra tuân thủ bằng LLM (vd LLM trả JSON không hợp lệ kể cả sau khi đã thử lại).
# vd: LLM trả JSON sai schema cả sau khi retry -> ném ComplianceLLMError.
class ComplianceLLMError(Exception):
    pass


# class ComplianceLLMTimeout là lỗi con của ComplianceLLMError, báo LLM không phản hồi kịp trong thời gian timeout cho phép.
# vd: LLM treo quá timeout_seconds (vd 30s) -> ném ComplianceLLMTimeout và hủy lời gọi.
class ComplianceLLMTimeout(ComplianceLLMError):
    pass

# class ComplianceChecker là một lớp để kiểm tra mức độ tuân thủ của một văn bản dựa trên các yêu cầu đã được định nghĩa trước đó. Nó sử dụng một mô hình ngôn ngữ lớn (LLM) để phân tích văn bản và so sánh với các yêu cầu, sau đó trả về một kết quả dưới dạng JSON cho biết liệu văn bản có tuân thủ hay không và nếu không, những mục nào đang thiếu và giải thích lý do. Lớp này bao gồm các phương thức để xây dựng prompt cho LLM, gọi LLM và xử lý phản hồi để đảm bảo rằng nó trả về dữ liệu hợp lệ theo schema đã định nghĩa.
# vd: ComplianceChecker(prompt, content).run() -> {'passed':False,'items_missing':[{requirement,explanation}]}.
class ComplianceChecker:
    # def __init__ để khởi tạo bộ kiểm tra tuân thủ: lưu prompt quy trình, nội dung văn bản, người dùng và timeout; chọn model rồi tạo LLM (temperature=0) dùng cho việc đối chiếu.
    # vd: ComplianceChecker(prompt, content, user=u, timeout_seconds=30) -> sẵn sàng gọi .run().
    def __init__(
        self,
        prompt,
        content_text: str,
        *,
        user=None,
        model_override: str | None = None,
        timeout_seconds: int = 30,
    ):
        self.prompt = prompt
        self.content = str(content_text or '')
        self.user = user
        self.timeout_seconds = max(int(timeout_seconds or 30), 1)
        self.model_name = (
            model_override
            or resolve_ai_config(user=user).ai_model
            or 'kimi-k2.6:cloud'
        )
        self._llm = get_llm(
            user=user,
            model_override=self.model_name,
            temperature_override=0,
        )
# def content_hash để tạo một hàm băm duy nhất cho nội dung văn bản và prompt liên quan, giúp xác định xem cùng một nội dung đã được kiểm tra trước đó hay chưa. Hàm này sử dụng thuật toán SHA-256 để tạo ra một chuỗi băm từ nội dung văn bản và một phần của prompt (ví dụ: prompt ID hoặc khóa chính), đảm bảo rằng mỗi lần kiểm tra tuân thủ với cùng một nội dung và prompt sẽ có cùng một giá trị băm, giúp tối ưu hóa quá trình kiểm tra bằng cách tránh việc phải gọi LLM nhiều lần cho cùng một nội dung đã được đánh giá trước đó.
    # vd: cùng content + prompt -> cùng hash, dùng để cache, tránh chấm lại bằng LLM.
    def content_hash(self) -> str:
        hasher = hashlib.sha256()
        hasher.update(self.content.encode('utf-8'))
        hasher.update(str(getattr(self.prompt, 'pk', '')).encode('utf-8'))
        return hasher.hexdigest()
# def run là phương thức chính để thực hiện quá trình kiểm tra tuân thủ. Nó kiểm tra xem nội dung văn bản có trống hay không, nếu có thì trả về kết quả không tuân thủ với lý do cụ thể. Nếu nội dung không trống, nó sẽ chia nhỏ nội dung thành các phần nếu cần thiết và gọi phương thức _run_chunk cho từng phần để đánh giá mức độ tuân thủ. Kết quả từ tất cả các phần sẽ được tổng hợp lại, loại bỏ trùng lặp và trả về một kết quả cuối cùng cho biết liệu văn bản có tuân thủ hay không và nếu không, những mục nào đang thiếu và giải thích lý do.
    # vd: văn bản trống -> {'passed':False, items_missing:[{requirement:'Nội dung văn bản',...}]}.
    def run(self) -> dict:
        if not self.content.strip():
            return {
                'passed': False,
                'items_missing': [
                    {
                        'requirement': 'Nội dung văn bản',
                        'explanation': 'Văn bản không có nội dung.',
                    },
                ],
            }

        chunks = self._chunk_content(self.content)
        if len(chunks) == 1:
            return self._run_chunk(chunks[0], 1, 1)

        merged_items = []
        all_passed = True
        for index, chunk in enumerate(chunks, start=1):
            result = self._run_chunk(chunk, index, len(chunks))
            all_passed = all_passed and bool(result['passed'])
            merged_items.extend(result['items_missing'])

        deduped_items = self._dedupe_items(merged_items)
        if all_passed and not deduped_items:
            return {'passed': True, 'items_missing': []}
        if not deduped_items:
            deduped_items = [
                {
                    'requirement': 'Tuân thủ đầy đủ yêu cầu',
                    'explanation': 'Hệ thống không nhận được danh sách mục thiếu rõ ràng.',
                },
            ]
        return {'passed': False, 'items_missing': deduped_items}
# def _run_chunk để đánh giá mức độ tuân thủ của một phần nội dung văn bản bằng cách xây dựng prompt cho LLM, gọi LLM và xử lý phản hồi để đảm bảo rằng nó trả về dữ liệu hợp lệ theo schema đã định nghĩa. Nếu phản hồi từ LLM không phải là JSON hợp lệ hoặc không tuân thủ schema, phương thức này sẽ thử gọi lại LLM với một prompt bổ sung yêu cầu trả về JSON hợp lệ. Nếu vẫn không nhận được phản hồi hợp lệ sau lần thử lại, phương thức sẽ ném ra một ngoại lệ ComplianceLLMError để báo lỗi.
    # vd: 1 phần văn bản -> gọi LLM, parse JSON; sai thì retry 1 lần rồi mới báo lỗi.
    def _run_chunk(self, chunk: str, index: int, total: int) -> dict:
        prompt_text = self._build_prompt(chunk, index=index, total=total)
        raw = self._invoke(prompt_text)
        try:
            return self._validate(json.loads(self._strip_fence(raw)))
        except Exception:
            retry_raw = self._invoke(
                f'{prompt_text}\n\nLAN TRUOC TRA KHONG DUNG JSON. TRA LAI DUNG JSON THEO SCHEMA.'
            )
            try:
                return self._validate(json.loads(self._strip_fence(retry_raw)))
            except Exception as exc:
                raise ComplianceLLMError(
                    f'LLM returned invalid JSON after retry: {exc}'
                ) from exc
# def _build_prompt để xây dựng một chuỗi prompt cho LLM bằng cách kết hợp một phần nội dung văn bản cần kiểm tra với các yêu cầu và quy trình đã được định nghĩa trước đó. Prompt này được thiết kế để hướng dẫn LLM trong việc đánh giá mức độ tuân thủ của văn bản dựa trên các yêu cầu cụ thể, đồng thời cung cấp ngữ cảnh rõ ràng về phần nội dung đang được kiểm tra (ví dụ: chỉ rõ đây là phần nào trong tổng số bao nhiêu phần). Kết quả của hàm này là một chuỗi văn bản hoàn chỉnh được sử dụng làm input cho LLM để thực hiện quá trình đánh giá tuân thủ.
    # vd: ghép JSON schema + yêu cầu (system/rules) + phần văn bản (i/total) thành prompt.
    def _build_prompt(self, chunk: str, *, index: int, total: int) -> str:
        system_content = str(getattr(self.prompt, 'system_content', '') or '').strip()
        rules_content = str(getattr(self.prompt, 'rules_content', '') or '').strip()
        return (
            f'{JSON_SCHEMA_PROMPT}\n\n'
            f'=== YEU CAU (Prompt quy trinh) ===\n'
            f'{system_content}\n\n{rules_content}\n\n'
            f'=== PHAN VAN BAN CAN KIEM TRA ({index}/{total}) ===\n'
            f'{chunk}'
        ).strip()

    # def _invoke để gọi LLM với prompt đã dựng trong một thread riêng có timeout; trả về nội dung text, hoặc ném ComplianceLLMTimeout nếu vượt quá thời gian cho phép.
    # vd: _invoke(prompt_text) trả chuỗi JSON từ LLM; nếu quá 30s -> ComplianceLLMTimeout.
    def _invoke(self, text: str) -> str:
        messages = [
            SystemMessage(content='Bạn chỉ được trả về JSON hợp lệ.'),
            HumanMessage(content=text),
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._llm.invoke, messages)
            try:
                response = future.result(timeout=self.timeout_seconds)
            except concurrent.futures.TimeoutError as exc:
                future.cancel()
                raise ComplianceLLMTimeout(
                    f'LLM timeout sau {self.timeout_seconds} giây.'
                ) from exc
        return str(getattr(response, 'content', '') or '').strip()
# def _strip_fence để loại bỏ các dấu hiệu định dạng mã (code fence) như ``` hoặc ```json từ một chuỗi văn bản, giúp chuẩn hóa phản hồi từ LLM trước khi cố gắng phân tích nó như JSON. Hàm này sử dụng một biểu thức chính quy để tìm và loại bỏ các dấu hiệu này ở đầu và cuối chuỗi, sau đó trả về chuỗi đã được làm sạch và chuẩn hóa, sẵn sàng để phân tích tiếp theo.
    # vd: '```json {..} ```' -> '{..}'.
    def _strip_fence(self, value: str) -> str:
        cleaned = str(value or '').strip()
        return _CODE_FENCE_RE.sub('', cleaned).strip()
# def _validate để kiểm tra xem phản hồi từ LLM có tuân thủ schema đã định nghĩa hay không bằng cách xác minh rằng nó là một đối tượng JSON có chứa các trường 'passed' và 'items_missing' với kiểu dữ liệu đúng. Nếu phản hồi không tuân thủ schema, hàm này sẽ ném ra một ngoại lệ ValueError với thông báo lỗi cụ thể. Nếu phản hồi tuân thủ schema, hàm sẽ trả về một đối tượng dict đã được chuẩn hóa, đảm bảo rằng nếu 'passed' là True thì 'items_missing' sẽ là một danh sách rỗng, và nếu 'passed' là False nhưng không có mục nào trong 'items_missing', nó sẽ thêm một mục mặc định để đảm bảo rằng kết quả luôn có thông tin rõ ràng về lý do tại sao văn bản không tuân thủ.
    # vd: payload thiếu 'passed' -> ValueError; hợp lệ -> chuẩn hóa items_missing.
    def _validate(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            raise ValueError('Payload must be an object.')
        passed = payload.get('passed')
        items_missing = payload.get('items_missing')
        if not isinstance(passed, bool):
            raise ValueError('passed must be bool.')
        if not isinstance(items_missing, list):
            raise ValueError('items_missing must be list.')

        normalized_items = []
        for item in items_missing:
            if not isinstance(item, dict):
                raise ValueError('items_missing item must be object.')
            requirement = str(item.get('requirement', '') or '').strip()
            explanation = str(item.get('explanation', '') or '').strip()
            if not requirement or not explanation:
                raise ValueError('items_missing item missing requirement/explanation.')
            normalized_items.append(
                {
                    'requirement': requirement,
                    'explanation': explanation,
                }
            )

        if passed:
            return {'passed': True, 'items_missing': []}
        if not normalized_items:
            normalized_items = [
                {
                    'requirement': 'Tuân thủ đầy đủ yêu cầu',
                    'explanation': 'Hệ thống không trả về mục thiếu cụ thể.',
                },
            ]
        return {'passed': False, 'items_missing': normalized_items}
# def _chunk_content để chia nhỏ nội dung văn bản thành các phần nhỏ hơn nếu độ dài của nội dung vượt quá một giới hạn nhất định (mặc định là 30.000 ký tự). Hàm này đảm bảo rằng các phần được chia nhỏ một cách hợp lý, ưu tiên chia tại các dấu xuống dòng nếu có thể để giữ nguyên ngữ cảnh. Kết quả trả về là một danh sách các chuỗi, mỗi chuỗi là một phần của nội dung đã được chuẩn hóa và sẵn sàng để kiểm tra tuân thủ.
    # vd: văn bản 70k ký tự -> chia ~3 phần <=30k, ưu tiên cắt ở dấu xuống dòng.
    def _chunk_content(self, text: str, *, limit: int = 30000) -> list[str]:
        normalized = str(text or '').strip()
        if len(normalized) <= limit:
            return [normalized]
        chunks = []
        start = 0
        while start < len(normalized):
            end = min(len(normalized), start + limit)
            if end < len(normalized):
                split_at = normalized.rfind('\n', start, end)
                if split_at > start + (limit // 2):
                    end = split_at
            chunks.append(normalized[start:end].strip())
            start = end
        return [chunk for chunk in chunks if chunk]
# def _dedupe_items để loại bỏ các mục trùng lặp trong danh sách các mục thiếu được trả về từ LLM bằng cách sử dụng một tập hợp (set) để theo dõi các cặp yêu cầu và giải thích đã thấy. Hàm này duyệt qua danh sách các mục, tạo một khóa duy nhất cho mỗi mục dựa trên yêu cầu và giải thích (được chuẩn hóa bằng cách loại bỏ khoảng trắng và chuyển thành chữ thường), và chỉ thêm mục vào kết quả cuối cùng nếu cặp yêu cầu-giải thích đó chưa từng xuất hiện trước đó. Kết quả trả về là một danh sách các mục đã được loại bỏ trùng lặp, giúp đảm bảo rằng kết quả cuối cùng không chứa các mục thiếu giống nhau nhiều lần.
    # vd: 2 mục cùng (requirement, explanation) -> chỉ giữ 1.
    def _dedupe_items(self, items: list[dict]) -> list[dict]:
        deduped = []
        seen = set()
        for item in items:
            key = (
                str(item.get('requirement', '')).strip().casefold(),
                str(item.get('explanation', '')).strip().casefold(),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

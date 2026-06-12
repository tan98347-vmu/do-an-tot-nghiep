"""
doc_creator.py là gì?

  ai_engine/doc_creator.py:1 là service biến yêu cầu bằng ngôn ngữ tự nhiên thành một bản ghi Document và file DOCX thật.

  Ví dụ:

  “Tạo đơn xin nghỉ ngày 20/6 vì lý do cá nhân”

  File này sẽ:

  1. Tìm những mẫu người dùng được phép sử dụng.
  2. Nhờ LLM chọn mẫu phù hợp.
  3. Trích dữ liệu từ yêu cầu.
  4. Điền thêm dữ liệu hồ sơ/công ty vào các biến còn trống.
  5. Render nội dung và file DOCX.
  6. Lưu Document vào database.

  Nó chỉ tạo văn bản dựa trên DocumentTemplate có sẵn, không tự tạo cấu trúc DOCX hoàn toàn mới. Nếu không tìm được mẫu phù hợp, nó sẽ trả về lỗi.

   ## Luồng xử lý chính

  Yêu cầu người dùng
      ↓
  is_document_creation_request()
      ↓
  Lấy các template người dùng được phép xem
      ↓
  Gửi danh sách template + yêu cầu cho LLM
      ↓
  LLM trả JSON: template_id, title, variables
      ↓
  Kiểm tra và làm sạch variables
      ↓
  Điền biến trống từ hồ sơ/công ty
      ↓
  template.render_as_docx()
      ↓
  Tạo Document + lưu file DOCX
      ↓
  Trả kết quả cho Chat/Assistant

  note : Luồng “Sinh văn bản với mẫu” không dùng hàm này, nhưng vẫn tái sử dụng một số helper JSON trong doc_creator.py.
"""

import json
import logging
import re
import unicodedata

from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

# def _ascii_safe_name để tạo một tên an toàn cho tài liệu bằng cách loại bỏ các ký tự Unicode đặc biệt và thay thế chúng bằng các ký tự ASCII tương đương. Hàm này giúp đảm bảo rằng tên tài liệu được lưu trữ và xử lý một cách an toàn trong hệ thống, tránh các vấn đề liên quan đến định dạng tên file hoặc xử lý chuỗi không mong muốn. Kết quả của hàm này là một chuỗi tên đã được làm sạch và an toàn để sử dụng trong hệ thống lưu trữ và quản lý tài liệu.
# vd: 'Đơn xin nghỉ.docx' -> 'Don_xin_nghi.docx' (tên file an toàn).
def _ascii_safe_name(title):
    title = title.replace('\u0111', 'd').replace('\u0110', 'D')
    normalized = unicodedata.normalize('NFD', title)
    ascii_str = ''.join(
        ch for ch in normalized
        if unicodedata.category(ch) != 'Mn' and ord(ch) < 128
    )
    safe = ''.join(ch if ch.isalnum() or ch in ' _-' else '_' for ch in ascii_str)
    return safe.strip('_').strip() or 'document'

# def _normalize_for_intent_match để chuẩn hóa một chuỗi văn bản bằng cách loại bỏ các ký tự Unicode đặc biệt, chuyển đổi sang chữ thường và loại bỏ các khoảng trắng thừa. Hàm này giúp chuẩn hóa văn bản đầu vào để dễ dàng so sánh và tìm kiếm các mẫu ý định trong quá trình xử lý ngôn ngữ tự nhiên, đặc biệt khi làm việc với các yêu cầu người dùng có thể có nhiều biến thể về cách viết hoặc định dạng. Kết quả của hàm này là một chuỗi đã được chuẩn hóa, giúp cải thiện độ chính xác của việc nhận diện ý định và trích xuất thông tin từ văn bản đầu vào.
# vd: 'Tạo Đơn' -> 'tao don' (bỏ dấu, chữ thường) để dò ý định.
def _normalize_for_intent_match(value: str) -> str:
    text = str(value or '').strip().casefold()
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    return ' '.join(text.split())

# _CREATION_VERBS và _DOC_NOUNS là các biểu thức chính quy được sử dụng để xác định các động từ liên quan đến việc tạo tài liệu và các danh từ liên quan đến loại tài liệu trong quá trình phân tích yêu cầu người dùng. _CREATION_VERBS bao gồm các động từ như "tạo", "soạn", "viết", "lập", "làm", "điền", "in", "xuất", "generate", "draft", "create", "fill" để nhận diện các yêu cầu liên quan đến việc tạo hoặc điền thông tin vào tài liệu. _DOC_NOUNS bao gồm các danh từ như "văn bản", "đơn", "hợp đồng", "tài liệu", "phiếu", "mẫu", "quyết định", "biên bản", "thư", "báo cáo", "hóa đơn", "đề xuất", "đề nghị", "thông báo", "tờ trình", "giấy tờ", "chứng từ", "hồ sơ", "bảng", "nội dung" để nhận diện các loại tài liệu mà người dùng có thể yêu cầu tạo hoặc điền thông tin vào. Các biểu thức chính quy này được sử dụng trong hàm is_document_creation_request để xác định xem một yêu cầu có phải là yêu cầu tạo tài liệu hay không dựa trên sự xuất hiện của các động từ và danh từ này trong văn bản yêu cầu.
_CREATION_VERBS = (
    r'tao|soan|viet|lap|lam|dien|in|xuat|generate|draft|create|fill'
)
_DOC_NOUNS = (
    r'van ban|don|hop dong|tai lieu|phieu|mau|quyet dinh|bien ban|thu|bao cao|'
    r'hoa don|de xuat|de nghi|thong bao|to trinh|giay to|chung tu|ho so|bang|noi dung|document'
)
_CREATION_PATTERN = re.compile(
    rf'\b({_CREATION_VERBS})\b.*\b({_DOC_NOUNS})\b',
    re.IGNORECASE | re.DOTALL,
)

# def _extract_json_object để trích xuất một đối tượng JSON từ một chuỗi đầu vào bằng cách tìm kiếm cặp dấu ngoặc nhọn mở và đóng. Hàm này duyệt qua chuỗi bắt đầu từ vị trí của dấu ngoặc nhọn mở đầu tiên, theo dõi độ sâu của các dấu ngoặc và trạng thái của chuỗi để đảm bảo rằng nó chỉ trả về phần nội dung JSON hợp lệ. Nếu không tìm thấy dấu ngoặc nhọn mở nào, nó sẽ trả về toàn bộ chuỗi đầu vào. Kết quả của hàm này là một chuỗi chứa đối tượng JSON đã được trích xuất, hoặc toàn bộ chuỗi nếu không tìm thấy đối tượng JSON nào.
# vd: nếu đầu vào là "Here is the data: { "name": "Alice", "age": 30 } and some extra text", hàm sẽ trả về "{ "name": "Alice", "age": 30 }".
def _extract_json_object(raw: str) -> str:
    start = raw.find('{')
    if start == -1:
        return raw

    depth = 0
    in_string = False
    escape = False
    for index, ch in enumerate(raw[start:], start):
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return raw[start:index + 1]
    return raw[start:]

# def _repair_json để sửa chữa một chuỗi JSON thô bằng cách đảm bảo rằng tất cả các dấu ngoặc nhọn mở đều có dấu ngoặc nhọn đóng tương ứng. Hàm này duyệt qua chuỗi, theo dõi độ sâu của các dấu ngoặc và trạng thái của chuỗi để xác định nếu có bất kỳ dấu ngoặc nhọn mở nào chưa được đóng. Nếu phát hiện ra rằng có nhiều dấu ngoặc nhọn mở hơn dấu ngoặc nhọn đóng, nó sẽ tự động thêm các dấu ngoặc nhọn đóng vào cuối chuỗi để đảm bảo rằng chuỗi JSON trở nên hợp lệ. Kết quả của hàm này là một chuỗi JSON đã được sửa chữa, sẵn sàng để được phân tích cú pháp mà không 

# vd: chuỗi JSON thiếu ngoặc/đuôi thừa -> vá lại thành JSON hợp lệ trước khi parse.
def _repair_json(raw: str) -> str:
    depth = 0
    in_string = False
    escape = False
    for ch in raw:
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
    if depth > 0:
        raw = raw.rstrip() + ('}' * depth)
    return raw

# def _parse_llm_json_payload để phân tích một chuỗi đầu vào thô từ LLM và trích xuất một đối tượng JSON từ đó. Hàm này xử lý các trường hợp phổ biến khi LLM trả về JSON được bao quanh bởi các khối mã (code blocks) hoặc có chứa các phần văn bản không liên quan. Nó sử dụng hàm _extract_json_object để trích xuất phần JSON chính xác và hàm _repair_json để đảm bảo rằng chuỗi JSON đã được sửa chữa nếu có bất kỳ dấu ngoặc nhọn nào bị thiếu. Kết quả của hàm này là một đối tượng Python được phân tích từ chuỗi JSON đã được trích xuất và sửa chữa, sẵn sàng để sử dụng trong quá trình tạo tài liệu hoặc các mục đích khác.
# vd : nếu đầu vào là "Here is the response: ```json { "template_id": 123, "variables": { "name": "Alice" } } ```", hàm sẽ trích xuất và phân tích chuỗi JSON để trả về một đối tượng Python tương ứng với nội dung JSON đó.
def _parse_llm_json_payload(raw: str):
    json_text = raw or ''
    if '```json' in json_text:
        json_text = json_text.split('```json', 1)[1].split('```', 1)[0].strip()
    elif '```' in json_text:
        json_text = json_text.split('```', 1)[1].split('```', 1)[0].strip()
    json_text = _extract_json_object(json_text)
    json_text = _repair_json(json_text)
    return json.loads(json_text)

# def is_document_creation_request để xác định xem một chuỗi văn bản có phải là một yêu cầu tạo tài liệu hay không bằng cách chuẩn hóa chuỗi và kiểm tra sự xuất hiện của các động từ liên quan đến việc tạo tài liệu và các danh từ liên quan đến loại tài liệu. Hàm này sử dụng biểu thức chính quy đã được định nghĩa trước đó để tìm kiếm các mẫu ý định trong văn bản đầu vào, giúp xác định xem người dùng có đang yêu cầu tạo một tài liệu mới hay không. Kết quả của hàm này là một giá trị boolean, trả về True nếu chuỗi văn bản được xác định là một yêu cầu tạo tài liệu, và False nếu không phải.
# vd: nếu đầu vào là "Tạo đơn xin nghỉ ngày 20/6 vì lý do cá nhân", hàm sẽ trả về True vì có chứa động từ "tạo" và danh từ "đơn" liên quan đến việc tạo tài liệu.
def is_document_creation_request(text: str) -> bool:
    normalized = _normalize_for_intent_match(text)
    return bool(_CREATION_PATTERN.search(normalized))

# def _get_templates_for_user để lấy danh sách các mẫu tài liệu mà người dùng có quyền truy cập. Hàm này gọi một hàm khác để truy vấn cơ sở dữ liệu và trả về các mẫu tài liệu phù hợp với quyền của người dùng. Kết quả của hàm này là một queryset hoặc danh sách các đối tượng mẫu tài liệu mà người dùng có thể sử dụng để tạo tài liệu mới dựa trên yêu cầu của họ.
# vd: user phòng Kế toán -> chỉ trả về các mẫu user được phép dùng.
def _get_templates_for_user(user):
    from accounts.permissions import get_accessible_templates
    return get_accessible_templates(user)


_EMPTY_VARIABLE_SENTINELS = {
    '',
    '[chua cung cap]',
    'chua cung cap',
    'khong ro',
    'unknown',
    'n/a',
    'null',
    'none',
}

# def _normalize_generated_variable_value để chuẩn hóa giá trị của các biến được tạo ra từ LLM bằng cách loại bỏ các ký tự không mong muốn, chuyển đổi sang chuỗi và kiểm tra xem giá trị đó có phải là một trong những giá trị đặc biệt được định nghĩa trước đó hay không. Nếu giá trị sau khi chuẩn hóa nằm trong danh sách các giá trị đặc biệt, hàm sẽ trả về một chuỗi rỗng, ngược lại nó sẽ trả về giá trị đã được chuẩn hóa. Kết quả của hàm này là một chuỗi đã được làm sạch và chuẩn hóa, sẵn sàng để sử dụng trong quá trình điền thông tin vào mẫu tài liệu.
# vd: '  Nguyen Van A ' -> 'Nguyen Van A'; 'N/A' -> ''.
def _normalize_generated_variable_value(value) -> str:
    normalized = str(value or '').strip()
    folded = _normalize_for_intent_match(normalized)
    if folded in _EMPTY_VARIABLE_SENTINELS:
        return ''
    return normalized

# def _sanitize_template_variables để làm sạch và chuẩn hóa các biến mẫu được tạo ra từ LLM bằng cách đảm bảo rằng tất cả các biến đều có giá trị chuỗi đã được chuẩn hóa. Hàm này nhận vào danh sách các tên biến mẫu và một từ điển chứa các giá trị thô của các biến đó, sau đó sử dụng hàm _normalize_generated_variable_value để chuẩn hóa từng giá trị của biến. Kết quả của hàm này là một từ điển mới chứa các tên biến mẫu và giá trị đã được làm sạch và chuẩn hóa, sẵn sàng để sử dụng trong quá trình điền thông tin vào mẫu tài liệu.
# nó khác với _normalize_generated_variable_value ở chỗ hàm này xử lý một tập hợp các biến và đảm bảo rằng tất cả chúng đều được chuẩn hóa, trong khi _normalize_generated_variable_value chỉ xử lý một giá trị đơn lẻ của một biến.
# vd: {'ho_ten':' A '} với biến ['ho_ten','gioi_tinh'] -> {'ho_ten':'A','gioi_tinh':''}.
def _sanitize_template_variables(template_variables, raw_variables) -> dict:
    if not isinstance(raw_variables, dict):
        raw_variables = {}
    return {
        variable_name: _normalize_generated_variable_value(raw_variables.get(variable_name, ''))
        for variable_name in template_variables
    }

# def _prefill_blank_variables_from_effective_context để điền các biến mẫu còn trống bằng cách sử dụng ngữ cảnh hiệu quả của người dùng, bao gồm thông tin từ hồ sơ cá nhân và công ty. Hàm này nhận vào mẫu tài liệu, danh sách các biến mẫu, từ điển chứa các giá trị hiện tại của các biến, thông tin người dùng và một số tùy chọn khác để xác định cách thức điền các biến còn trống. Nó sử dụng một mô hình ngôn ngữ lớn (LLM) để phân tích ngữ cảnh hiệu quả và điền các biến còn trống một cách chính xác dựa trên thông tin có sẵn. Kết quả của hàm này là một từ điển mới chứa các tên biến mẫu và giá trị đã được điền đầy đủ, sẵn sàng để sử dụng trong quá trình tạo tài liệu.
# có sử dụng các hàm helper như _parse_llm_json_payload và _sanitize_template_variables để đảm bảo rằng dữ liệu được trích xuất từ LLM là chính xác và an toàn để sử dụng trong mẫu tài liệu. Hàm này giúp tối ưu hóa quá trình tạo tài liệu bằng cách tận dụng thông tin ngữ cảnh có sẵn của người dùng, giảm thiểu việc phải yêu cầu người dùng cung cấp thông tin đã có sẵn trong hồ sơ cá nhân hoặc công ty của họ.

# vd: biến 'phong_ban' còn trống -> điền theo hồ sơ/công ty của user nếu có.
def _prefill_blank_variables_from_effective_context(
    *,
    tmpl,
    template_variables,
    variables: dict,
    user,
    model_override=None,
    temperature_override=None,
    allow_cloud_model=True,
    use_profile: bool = True,
    use_company: bool = True,
):
    from accounts.tenancy import build_effective_ai_context
    from ai_engine.rag_engine import get_llm
    from langchain_core.messages import HumanMessage, SystemMessage

    if not use_profile and not use_company:
        return variables

    blank_vars = [
        variable_name
        for variable_name in template_variables
        if not str(variables.get(variable_name, '')).strip()
    ]
    if not blank_vars:
        return variables

    effective_context = build_effective_ai_context(
        user=user,
        include_profile=use_profile,
        include_company=use_company,
    ).strip()
    if not effective_context:
        return variables

    current_values_desc = '\n'.join(
        f'- {variable_name}: "{variables.get(variable_name, "")}"'
        for variable_name in template_variables
    )
    blank_vars_desc = '\n'.join(f'- {variable_name}' for variable_name in blank_vars)
    system_prompt = (
        'You fill missing document template variables from the provided employee and company context.\n'
        'You may only fill variables that are currently blank.\n'
        'Never modify or overwrite any non-empty value that already exists.\n'
        'Prefer employee-profile context for person/employee fields.\n'
        'Prefer company context for organization fields.\n'
        "If the context does not contain a value, return ''.\n"
        'Return pure JSON only.'
    )
    human_prompt = (
        f'TEMPLATE TITLE:\n{tmpl.title}\n\n'
        f'TEMPLATE CONTENT PREVIEW:\n{(tmpl.content or "")[:800]}\n\n'
        f'CURRENT VARIABLE VALUES:\n{current_values_desc}\n\n'
        f'ONLY FILL THESE BLANK VARIABLES:\n{blank_vars_desc}\n\n'
        f'EFFECTIVE CONTEXT:\n{effective_context[:4000]}\n\n'
        'Return JSON: {"variable_name": "value", ...}'
    )

    llm = get_llm(
        user,
        model_override=model_override,
        temperature_override=temperature_override,
        allow_cloud_model=allow_cloud_model,
    )
    raw = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ]).content.strip()
    extracted = _parse_llm_json_payload(raw)
    sanitized = _sanitize_template_variables(template_variables, extracted)

    result = dict(variables)
    for variable_name in blank_vars:
        value = sanitized.get(variable_name, '')
        if value:
            result[variable_name] = value
    return result

# def _build_template_selection_rules để xây dựng một chuỗi quy tắc hướng dẫn LLM trong việc chọn mẫu tài liệu phù hợp dựa trên yêu cầu của người dùng và các thông tin liên quan. Hàm này kết hợp một tập hợp các quy tắc cơ bản đã được định nghĩa trước đó với bất kỳ quy tắc bổ sung nào mà người dùng có thể cung cấp thông qua tham số user_extra_rules. Kết quả của hàm này là một chuỗi văn bản chứa tất cả các quy tắc cần thiết để hướng dẫn LLM trong quá trình lựa chọn mẫu tài liệu, giúp đảm bảo rằng LLM chỉ sử dụng thông tin rõ ràng và không tự ý suy luận hoặc thêm thắt thông tin khi chọn mẫu.
# vd: nếu user_extra_rules là "Hãy ưu tiên các mẫu có chứa biến 'ngay_thang' nếu yêu cầu có đề cập đến ngày tháng.", thì kết quả của hàm sẽ là một chuỗi quy tắc bao gồm cả các quy tắc cơ bản và quy tắc bổ sung này, giúp LLM hiểu rõ hơn về cách chọn mẫu tài liệu phù hợp với yêu cầu của người dùng.
def _build_template_selection_rules(user_extra_rules=None) -> str:
    base_rules = (
        '- Only fill variables with data explicitly stated in the user request or attached content.\n'
        "- If the user did not provide a value, leave it as ''.\n"
        '- Do not use employee/company context in this first pass; the system will prefill remaining blanks later.\n'
        '- Do not infer, invent, or guess missing facts.\n'
        '- Choose the best template using title, description, variables, and content preview.\n'
        '- Return pure JSON only.'
    )
    if user_extra_rules and str(user_extra_rules).strip():
        return f'{base_rules}\n{str(user_extra_rules).strip()}'
    return base_rules

# def create_document_from_intent là hàm chính để tạo một tài liệu mới dựa trên yêu cầu của người dùng bằng cách sử dụng các mẫu tài liệu có sẵn và một mô hình ngôn ngữ lớn (LLM) để phân tích yêu cầu và điền thông tin vào mẫu. Hàm này thực hiện các bước sau:
# 1. Lấy danh sách các mẫu tài liệu mà người dùng có quyền truy cập
# 2. Xây dựng một prompt hệ thống để hướng dẫn LLM trong việc chọn mẫu tài liệu phù hợp và trích xuất thông tin từ yêu cầu của người dùng
# 3. Gọi LLM với prompt và yêu cầu của người dùng để nhận được một phản hồi chứa thông tin về mẫu tài liệu được chọn và các biến cần điền
# 4. Phân tích phản hồi từ LLM để trích xuất thông tin và làm sạch các biến
# 5. Điền các biến còn trống bằng cách sử dụng ngữ cảnh hiệu quả của người dùng nếu cần thiết
# 6. Render nội dung và file DOCX dựa trên mẫu đã chọn và các biến đã điền
# 7. Lưu Document vào database và trả về kết quả cho Chat/Assistant

# vd: 'tao don xin nghi ngay 20/6 vi ly do ca nhan' -> chọn mẫu đơn xin nghỉ, điền ngày + lý do, tạo Document.
def create_document_from_intent(
    question: str,
    user,
    model_override=None,
    temperature_override=None,
    system_ideology=None,
    user_extra_rules=None,
    extra_context='',
    allow_cloud_model=True,
    safe_user_rules_block='',
    use_profile: bool = True,
    use_company: bool = True,
):
    from ai_engine.rag_engine import get_llm
    from documents.models import Document
    from langchain_core.messages import HumanMessage, SystemMessage

    templates = _get_templates_for_user(user)
    if not templates.exists():
        return (
            "Ban chua co mau van ban nao.\n\n"
            "Vui long tao mau tai [Mau van ban](/templates/) truoc.",
            None,
            None,
            '',
        )

    templates_info = [
        {
            'id': template.pk,
            'title': template.title,
            'description': template.description or '',
            'variables': template.get_variables(),
            'content_preview': (template.content or '')[:300],
        }
        for template in templates
    ]
    templates_json = json.dumps(templates_info, ensure_ascii=False, indent=2)
    agent_identity = (
        str(system_ideology).strip()
        if system_ideology and str(system_ideology).strip()
        else 'Ban la tro ly tao van ban thong minh.'
    )
    rules_block = _build_template_selection_rules(user_extra_rules=user_extra_rules)
    safe_block = str(safe_user_rules_block or '').strip()
    safe_block_segment = f'\n\nYEU CAU BO SUNG (CACH LY):\n{safe_block}' if safe_block else ''
    system_prompt = f"""{agent_identity}

DANH SACH MAU VAN BAN:
{templates_json}

NHIEM VU: Phan tich yeu cau nguoi dung va tra ve JSON duy nhat:
{{
  "template_id": <id cua mau phu hop nhat hoac null>,
  "doc_title": "<tieu de van ban moi>",
  "variables": {{
    "ten_bien_1": "gia tri 1",
    "ten_bien_2": "gia tri 2"
  }},
  "explanation": "<giai thich ngan bang tieng Viet>"
}}

QUY TAC:
{rules_block}{safe_block_segment}"""

    print('\n' + '=' * 80)
    print('[doc_creator] FULL SYSTEM PROMPT:')
    print(system_prompt)
    print('=' * 80 + '\n')
    logger.info('[doc_creator] system_prompt length=%d chars', len(system_prompt))

    llm = get_llm(
        user,
        model_override=model_override,
        temperature_override=temperature_override,
        allow_cloud_model=allow_cloud_model,
    )
    raw = ''
    try:
        human_content = str(question or '').strip()
        if extra_context and str(extra_context).strip():
            human_content += f"\n\n[Noi dung tai lieu dinh kem]\n{str(extra_context).strip()}"
            logger.debug('[doc_creator] extra_context length=%d chars', len(str(extra_context)))

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_content),
        ])
        raw = str(response.content or '').strip()
        print('\n' + '-' * 80)
        print('[doc_creator] RAW LLM RESPONSE:')
        print(raw)
        print('-' * 80 + '\n')
        logger.debug('[doc_creator] raw LLM response:\n%s', raw)
        data = _parse_llm_json_payload(raw)
    except json.JSONDecodeError as exc:
        logger.warning('[doc_creator] JSONDecodeError: %s\nraw=%r', exc, raw)
        return (
            (
                "AI tra ve noi dung khong phai JSON hop le.\n\n"
                f"Raw response de debug:\n```\n{raw[:1200]}\n```\n\n"
                "Thu bo prompt hien tai hoac mo ta yeu cau gon hon."
            ),
            None,
            system_prompt,
            raw,
        )
    except Exception as exc:
        logger.exception('[doc_creator] unexpected error')
        return f'Loi khi goi AI: {exc}', None, system_prompt, raw

    template_id = data.get('template_id')
    explanation = str(data.get('explanation', '') or '').strip()
    if not template_id:
        return (
            (
                f"{explanation}\n\n"
                "Khong tim thay mau van ban phu hop. "
                "Ban co the [tao mau moi](/templates/create/) hoac mo ta cu the hon."
            ),
            None,
            system_prompt,
            raw,
        )

    tmpl = _get_templates_for_user(user).filter(pk=template_id).first()
    if not tmpl:
        return (
            f'Mau ID={template_id} khong ton tai hoac ban khong co quyen truy cap.',
            None,
            system_prompt,
            raw,
        )

    template_variables = list(tmpl.get_variables())
    variables = _sanitize_template_variables(template_variables, data.get('variables', {}))
    variables = _prefill_blank_variables_from_effective_context(
        tmpl=tmpl,
        template_variables=template_variables,
        variables=variables,
        user=user,
        model_override=model_override,
        temperature_override=temperature_override,
        allow_cloud_model=allow_cloud_model,
        use_profile=use_profile,
        use_company=use_company,
    )
    doc_title = str(data.get('doc_title') or f'Van ban tu {tmpl.title}').strip()

    try:
        docx_bytes = tmpl.render_as_docx(variables)
        plain_content = tmpl.render(variables)
    except Exception as exc:
        return f'Loi khi tao file DOCX: {exc}', None, system_prompt, raw

    from documents.runtime_helpers import resolve_document_company_for_generation

    doc = Document(
        title=doc_title,
        content=plain_content,
        template=tmpl,
        owner=user,
        company=resolve_document_company_for_generation(user, tmpl),
    )
    safe_name = _ascii_safe_name(doc_title)
    doc.output_file.save(
        f'{safe_name}.docx',
        ContentFile(docx_bytes.read()),
        save=False,
    )
    doc.save()

    if variables:
        var_lines = '\n'.join(f'- **{key}**: {value}' for key, value in variables.items())
    else:
        var_lines = '_(khong co bien nao)_'

    answer = (
        f"{explanation}\n\n"
        f"---\n"
        f"**Van ban da tao:** [{doc_title}](/documents/{doc.pk}/)\n\n"
        f"**Mau su dung:** {tmpl.title}\n\n"
        f"**Thong tin da dien:**\n{var_lines}\n\n"
        f"[Tai xuong DOCX](/documents/{doc.pk}/download/) | "
        f"[Xem chi tiet](/documents/{doc.pk}/)"
    )
    return answer, doc, system_prompt, raw

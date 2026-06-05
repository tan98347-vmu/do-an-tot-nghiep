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


class ComplianceLLMError(Exception):
    pass


class ComplianceLLMTimeout(ComplianceLLMError):
    pass


class ComplianceChecker:
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

    def content_hash(self) -> str:
        hasher = hashlib.sha256()
        hasher.update(self.content.encode('utf-8'))
        hasher.update(str(getattr(self.prompt, 'pk', '')).encode('utf-8'))
        return hasher.hexdigest()

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

    def _strip_fence(self, value: str) -> str:
        cleaned = str(value or '').strip()
        return _CODE_FENCE_RE.sub('', cleaned).strip()

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

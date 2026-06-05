"""Pipeline trich xuat noi dung tu attachment (PDF + anh) cho ChatAI / VoiceAI.

Khi user dinh kem PDF/anh vao mot turn ChatAI/VoiceAI, helper o day se:
  1. Trich text raw tu PDF (qua `extract_pdf_text` cua rag_engine).
  2. OCR text tu anh (qua `_extract_text_from_image_with_glm_ocr` cua api.views.ai_doc).
  3. Ghep tat ca thanh mot khoi text duy nhat de truyen vao `extra_context`
     cua `create_document_from_intent`.

Thiet ke per-turn: pipeline khong luu tru gi vao DB - bytes hoac path tam thoi
duoc xu ly trong cung context request.
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional, Sequence

logger = logging.getLogger('ai_engine.chat_attachment_pipeline')


def _truncate_text(text: str, limit: int = 6000) -> str:
    text = str(text or '').strip()
    if len(text) <= limit:
        return text
    return text[:limit] + '\n[...cat bot...]'


def _safe_pdf_extract(pdf_file_obj) -> str:
    try:
        from ai_engine.rag_engine import extract_pdf_text
        text = extract_pdf_text(pdf_file_obj) or ''
        return str(text).strip()
    except Exception as exc:
        logger.warning('PDF extract failed: %s', exc)
        return ''


def _safe_image_extract(image_file_obj, *, user) -> str:
    try:
        from api.views.ai_doc import _extract_text_from_image_with_glm_ocr
        text = _extract_text_from_image_with_glm_ocr(
            image_file_obj,
            user=user,
            flow='chat_attachment',
            started_at=time.time(),
        ) or ''
        return str(text).strip()
    except Exception as exc:
        logger.warning('Image OCR failed: %s', exc)
        return ''


def build_attachment_context(
    *,
    user,
    pdf_files: Sequence = (),
    image_files: Sequence = (),
    task_id: Optional[str] = None,
    progress_start: int = 5,
    progress_end: int = 40,
) -> str:
    """Trich xuat va ghep noi dung tu attachments thanh mot khoi text.

    Args:
        user: Django User dang yeu cau (de chon OCR model phu hop).
        pdf_files: list of uploaded PDF file-like objects (Django UploadedFile).
        image_files: list of uploaded image file-like objects.
        task_id: optional AI task id de stream progress qua `update_progress`.
        progress_start/end: phan tram bao cao cho stage trich xuat attachment.

    Returns:
        Mot chuoi tong hop dang:
            === ATTACHMENT 1 (PDF: foo.pdf) ===
            ...text...

            === ATTACHMENT 2 (IMAGE: bar.jpg) ===
            ...text...
        Tra ve chuoi rong neu khong co attachment / khong trich duoc gi.
    """
    pdf_files = [f for f in (pdf_files or []) if f is not None]
    image_files = [f for f in (image_files or []) if f is not None]
    total = len(pdf_files) + len(image_files)
    if total == 0:
        return ''

    update_progress = None
    if task_id:
        try:
            from ai_tasks.services.task_runner import update_progress as _up
            update_progress = _up
        except Exception:
            update_progress = None

    def _report(percent: int, stage: str, detail: str = ''):
        if update_progress is not None:
            try:
                update_progress(task_id, percent, stage, detail)
            except Exception:
                pass

    span = max(progress_end - progress_start, 1)
    parts: List[str] = []
    done = 0
    _report(progress_start, 'Nhan dinh kem', f'{total} tep')

    for i, pdf in enumerate(pdf_files):
        done += 1
        percent = progress_start + int(span * done / max(total, 1))
        name = getattr(pdf, 'name', f'pdf_{i + 1}.pdf') or f'pdf_{i + 1}.pdf'
        _report(percent, f'Trich xuat PDF {i + 1}/{len(pdf_files)}', name)
        text = _safe_pdf_extract(pdf)
        if text:
            parts.append(f'=== ATTACHMENT {done} (PDF: {name}) ===\n{_truncate_text(text)}')

    for i, img in enumerate(image_files):
        done += 1
        percent = progress_start + int(span * done / max(total, 1))
        name = getattr(img, 'name', f'image_{i + 1}.png') or f'image_{i + 1}.png'
        _report(percent, f'Trich xuat anh {i + 1}/{len(image_files)}', name)
        text = _safe_image_extract(img, user=user)
        if text:
            parts.append(f'=== ATTACHMENT {done} (IMAGE: {name}) ===\n{_truncate_text(text)}')

    if parts:
        _report(progress_end, 'Da tong hop dinh kem', f'{len(parts)} tep co noi dung')
    else:
        _report(progress_end, 'Khong trich duoc dinh kem', 'Bo qua attachment')
    return '\n\n'.join(parts).strip()

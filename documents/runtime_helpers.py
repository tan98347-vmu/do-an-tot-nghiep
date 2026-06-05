import unicodedata
from urllib.parse import quote

from django.utils import timezone

from .models import DocumentNumberConfig


def _ascii_safe_name(title):
    title = str(title or '')
    title = title.replace('\u0111', 'd').replace('\u0110', 'D')
    normalized = unicodedata.normalize('NFD', title)
    ascii_str = ''.join(
        c for c in normalized
        if unicodedata.category(c) != 'Mn' and ord(c) < 128
    )
    safe = ''.join(c if c.isalnum() or c in ' _-' else '_' for c in ascii_str)
    return safe.strip('_').strip() or 'document'


def _auto_doc_number(department, category=None):
    if not department:
        return ''

    year = timezone.now().year
    qs = DocumentNumberConfig.objects.filter(department=department, year=year)
    if category:
        qs_cat = qs.filter(category=category)
        if qs_cat.exists():
            return qs_cat.first().next_number()

    qs_any = qs.filter(category__isnull=True)
    if qs_any.exists():
        return qs_any.first().next_number()
    return ''


def _extract_text_from_docx(docx_file):
    try:
        import docx as python_docx
        from docx.table import Table as _Table
        from docx.text.paragraph import Paragraph as _Para

        docx_file.seek(0)
        doc = python_docx.Document(docx_file)
        parts = []
        for child in doc.element.body:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if tag == 'p':
                paragraph = _Para(child, doc)
                if paragraph.text.strip():
                    parts.append(paragraph.text)
            elif tag == 'tbl':
                table = _Table(child, doc)
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            if paragraph.text.strip():
                                parts.append(paragraph.text)
        return '\n'.join(parts)
    except Exception:
        return ''


def safe_attachment_filename(name: str) -> str:
    normalized = str(name or '').strip() or 'file'
    ascii_part = ''.join(
        char if char.isalnum() or char in '._-' else '_'
        for char in unicodedata.normalize('NFKD', normalized)
        if ord(char) < 128
    ).strip('._')[:120] or 'file'
    utf8_part = quote(normalized, safe='')
    return f'filename="{ascii_part}"; filename*=UTF-8\'\'{utf8_part}'

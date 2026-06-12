"""
  rag_index.py
  = Người xây và bảo trì thư viện vector

  rag_search.py
  = Người tìm đúng sách và đúng đoạn trong thư viện

  rag_engine.py
  = Người đưa các đoạn đó cho LLM và yêu cầu LLM trả lời
"""

import logging
import re
import unicodedata

from django.conf import settings
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import F, FloatField, Func, Q, TextField, Value
from django.db.models.functions import Cast, Coalesce, Concat, Lower
from langchain_community.vectorstores import PGVector

from accounts.permissions import get_accessible_documents, get_accessible_templates
from accounts.tenancy import get_user_company
from document_templates.models import DocumentTemplate, STATUS_REJECTED
from documents.models import Document

from .rag_index import (
    document_collection_names_for_companies,
    template_collection_names_for_companies,
)

_logger = logging.getLogger('ai_engine')
_SEMANTIC_FETCH_STEPS = (64, 128, 256)
_SEMANTIC_TARGET_MULTIPLIER = 4
_SEMANTIC_TARGET_MIN = 12
_TERM_ALLOWLIST = {'hd', 'cv', 'nda', 'nca', 'bhxh', 'bhyt', 'mst', 'gtgt'}
_STOPWORDS = {
    'a', 'an', 'and', 'cho', 'co', 'cua', 'da', 'de', 'duoc', 'gi', 'giua', 'hay',
    'khi', 'khong', 'la', 'lam', 'loai', 'ma', 'mot', 'nao', 'nay', 'nhung', 'noi',
    'o', 'or', 'sau', 'se', 'so', 'tai', 'tat', 'the', 'thi', 'tren', 'trong', 'tu',
    've', 'va', 'vay', 'voi',
}

# class Unaccent là wrapper hàm SQL UNACCENT của PostgreSQL để so khớp không phân biệt dấu ngay trong truy vấn ORM.
# vd: Unaccent(F('title')) -> so khớp 'hđ' với 'hd' bất kể dấu.
class Unaccent(Func):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Lop `Unaccent` dong goi mot cum hanh vi hoac cau hinh backend cua file `ai_engine/rag_search.py`.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: To chuc logic lien quan toi `Unaccent` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
    """
    function = 'UNACCENT'
    output_field = TextField()

# def _rag_search_debug để in log debug cho luồng tìm kiếm hybrid (keyword + semantic).
# vd: in '[RAG_HYBRID] keyword hits=3 semantic hits=5'.
def _rag_search_debug(message):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_rag_search_debug` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem tim kiem hoac loc du lieu theo cau hoi dau vao trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tim kiem hoac loc du lieu theo cau hoi dau vao roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_strip_html_text`, `_normalize_search_text`, `_query_terms` trong module nay.
    Tac dung: Don buoc tim kiem hoac loc du lieu theo cau hoi dau vao xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    print(f'[RAG_HYBRID] {message}', flush=True)

# def _strip_html_text để bỏ thẻ HTML/script/style và gộp khoảng trắng, lấy text thuần để tìm kiếm/preview.
# vd: '<p>Hợp <b>đồng</b></p>' -> 'Hợp đồng'.
def _strip_html_text(value):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_strip_html_text` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem loai bo dinh dang hoac ky tu du khoi du lieu trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can loai bo dinh dang hoac ky tu du khoi du lieu roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_normalize_search_text`, `_query_terms` trong module nay.
    Tac dung: Don buoc loai bo dinh dang hoac ky tu du khoi du lieu xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    from html import unescape

    value = re.sub(r'(?is)<script.*?>.*?</script>', ' ', value or '')
    value = re.sub(r'(?is)<style.*?>.*?</style>', ' ', value)
    value = re.sub(r'(?s)<[^>]+>', ' ', value)
    value = unescape(value)
    return re.sub(r'\s+', ' ', value).strip()

# def _normalize_search_text để chuẩn hóa text về dạng không dấu, chữ thường, chỉ giữ chữ-số (đổi đ→d) phục vụ so khớp.
# vd: 'Hợp Đồng Thuê' -> 'hop dong thue'.
def _normalize_search_text(value):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_normalize_search_text` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem chuan hoa du lieu dau vao hoac du lieu trung gian trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can chuan hoa du lieu dau vao hoac du lieu trung gian roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_query_terms` trong module nay.
    Tac dung: Don buoc chuan hoa du lieu dau vao hoac du lieu trung gian xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    value = (value or '').replace('đ', 'd').replace('Đ', 'D')
    normalized = unicodedata.normalize('NFKD', value)
    normalized = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.lower()
    normalized = re.sub(r'[^0-9a-z]+', ' ', normalized)
    return ' '.join(normalized.split())

# def _query_terms để tách câu hỏi thành danh sách từ khóa đã chuẩn hóa (bỏ stopword và từ quá ngắn, trừ allowlist), khử trùng lặp.
# vd: 'mẫu đơn xin nghỉ phép' -> ['mau','don','xin','nghi','phep'] (bỏ stopword).
def _query_terms(question):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_query_terms` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem tim kiem hoac loc du lieu theo cau hoi dau vao trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tim kiem hoac loc du lieu theo cau hoi dau vao roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc tim kiem hoac loc du lieu theo cau hoi dau vao xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    normalized = _normalize_search_text(question)
    results = []
    seen = set()
    for part in re.split(r'[^0-9a-z]+', normalized):
        if not part:
            continue
        if part not in _TERM_ALLOWLIST and len(part) < 2:
            continue
        if part not in _TERM_ALLOWLIST and part in _STOPWORDS:
            continue
        if part in seen:
            continue
        seen.add(part)
        results.append(part)
    return results

# def _minimum_relevance_score để tính ngưỡng điểm liên quan tối thiểu theo số từ khóa và nguồn (template/document) nhằm loại kết quả quá yếu.
# vd: 3 từ khóa, template -> ngưỡng ~38 điểm (loại kết quả thấp hơn).
def _minimum_relevance_score(question, *, source='template'):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_minimum_relevance_score` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    term_count = len(_query_terms(question))
    if term_count <= 0:
        return 0
    base = 28 if source == 'template' else 24
    step = 5 if source == 'template' else 4
    return min(52, base + max(0, term_count - 1) * step)

# def _normalize_with_index_map để chuẩn hóa text nhưng vẫn giữ bản đồ vị trí ký tự gốc, giúp tìm và cắt đoạn preview đúng chỗ khớp trong văn bản gốc.
# vd: tìm 'hop dong' ở bản chuẩn hóa rồi map ngược về vị trí trong text gốc có dấu để cắt preview.
def _normalize_with_index_map(value):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_normalize_with_index_map` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem chuan hoa du lieu dau vao hoac du lieu trung gian trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can chuan hoa du lieu dau vao hoac du lieu trung gian roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc chuan hoa du lieu dau vao hoac du lieu trung gian xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    normalized_chars = []
    index_map = []
    previous_space = False
    for index, char in enumerate(value or ''):
        if char in {'đ', 'Đ'}:
            expanded = 'd'
        else:
            expanded = unicodedata.normalize('NFKD', char)
        for expanded_char in expanded:
            if unicodedata.combining(expanded_char):
                continue
            lowered = expanded_char.lower()
            if lowered.isalnum():
                normalized_chars.append(lowered)
                index_map.append(index)
                previous_space = False
                continue
            if lowered.isspace() and not previous_space and normalized_chars:
                normalized_chars.append(' ')
                index_map.append(index)
                previous_space = True
    return ''.join(normalized_chars).strip(), index_map

# def _find_match_span để tìm khoảng (vị trí đầu–cuối) trong text khớp tốt nhất với từ khóa câu hỏi.
# vd: text dài + 'nghi phep' -> trả (start, end) quanh cụm khớp.
def _find_match_span(text, question):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_find_match_span` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    normalized_text, index_map = _normalize_with_index_map(text)
    if not normalized_text or not index_map:
        return None

    targets = []
    phrase = _normalize_search_text(question)
    if phrase:
        targets.append(phrase)
    targets.extend(_query_terms(question))

    for target in targets:
        hit_index = normalized_text.find(target)
        if hit_index < 0:
            continue
        end_index = hit_index + len(target) - 1
        if end_index >= len(index_map):
            continue
        return index_map[hit_index], index_map[end_index] + 1
    return None

# def _extract_relevant_preview để cắt một đoạn preview quanh chỗ khớp (ưu tiên đoạn semantic nếu có), giới hạn max_chars.
# vd: -> '...được nghỉ phép năm 12 ngày...' (đoạn quanh từ khóa, <=600 ký tự).
def _extract_relevant_preview(text, question, *, semantic_chunk='', max_chars=600):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_extract_relevant_preview` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem trich xuat noi dung hoac gia tri trung gian trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can trich xuat noi dung hoac gia tri trung gian roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc trich xuat noi dung hoac gia tri trung gian xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    plain = _strip_html_text(text or '').strip()
    semantic_plain = _strip_html_text(semantic_chunk or '').strip()
    if not plain:
        return semantic_plain[:max_chars].strip()

    span = _find_match_span(plain, question)
    if span:
        start, end = span
        window_start = max(0, start - 160)
        window_end = min(len(plain), max(end + 320, window_start + max_chars))
        snippet = plain[window_start:window_end].strip()
        if window_start > 0:
            snippet = f'...{snippet}'
        if window_end < len(plain):
            snippet = f'{snippet}...'
        return snippet

    if semantic_plain:
        return semantic_plain[:max_chars].strip()
    return plain[:max_chars].strip()

# def _semantic_bonus_for_rank để cộng điểm thưởng theo thứ hạng semantic (rank càng cao thì thưởng càng lớn).
# vd: rank 0 (khớp nhất) -> cộng nhiều điểm; rank thấp -> cộng ít.
def _semantic_bonus_for_rank(rank):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_semantic_bonus_for_rank` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if rank is None:
        return 0
    return max(0, 48 - int(rank) * 4)

# def _similarity_expression để dựng biểu thức ORM tính độ tương đồng (similarity) giữa một cột và cụm từ truy vấn.
# vd: similarity(title, 'hop dong') dùng để annotate điểm.
def _similarity_expression(expression, phrase):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_similarity_expression` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if phrase:
        return TrigramSimilarity(expression, Value(phrase, output_field=TextField()))
    return Value(0.0, output_field=FloatField())

# def _unaccent_expr để bọc một biểu thức cột bằng UNACCENT (bỏ dấu) cho so khớp không dấu.
# vd: -> UNACCENT(lower(title)) để so khớp không dấu.
def _unaccent_expr(expression):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_unaccent_expr` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return Lower(Unaccent(expression))

# def _text_expr để dựng biểu thức text đã chuẩn hóa (unaccent + lower) cho một field phục vụ tìm kiếm.
# vd: -> unaccent(lower(field)) cho field tìm kiếm.
def _text_expr(field_name):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_text_expr` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return Coalesce(
        Cast(F(field_name), output_field=TextField()),
        Value('', output_field=TextField()),
        output_field=TextField(),
    )

# def _space_expr để tạo biểu thức khoảng trắng dùng ghép/nối chuỗi trong truy vấn SQL.
# vd: dùng nối 'title' + ' ' + 'description' khi tính similarity gộp.
def _space_expr():
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_space_expr` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return Value(' ', output_field=TextField())

# def _semantic_rank_map để chạy tìm kiếm semantic (vector) trên một collection và trả map {object_id: thứ hạng} cho fetch_k kết quả đầu.
# vd: -> {5:0, 9:1, 12:2} (mẫu #5 khớp semantic nhất).
def _semantic_rank_map(question, collection_name, *, fetch_k=64):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_semantic_rank_map` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    from .rag_engine import get_embeddings

    fetch_k = max(1, int(fetch_k or 1))
    try:
        vs = PGVector(
            collection_name=collection_name,
            connection_string=settings.PGVECTOR_CONNECTION_STRING,
            embedding_function=get_embeddings(),
        )
        docs = vs.similarity_search(question, k=fetch_k)
    except Exception as exc:
        _rag_search_debug(
            f'semantic_search_failed | collection={collection_name} | fetch_k={fetch_k} | error={exc!r}'
        )
        return {}

    rank_map = {}
    for rank, doc in enumerate(docs):
        metadata = getattr(doc, 'metadata', {}) or {}
        raw_id = metadata.get('id')
        try:
            obj_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        previous = rank_map.get(obj_id)
        if previous is not None and rank >= previous['rank']:
            continue
        rank_map[obj_id] = {
            'rank': rank,
            'metadata': metadata,
            'chunk_text': _strip_html_text(getattr(doc, 'page_content', '') or ''),
        }

    _rag_search_debug(
        f'semantic_search_ok | collection={collection_name} | fetch_k={fetch_k} | '
        f'raw_hits={len(docs)} | accessible_candidates={len(rank_map)}'
    )
    return rank_map

# def _semantic_collection_names để xác định danh sách collection vector cần tìm semantic theo phạm vi (công ty + legacy).
# vd: user công ty 1 -> ['company_1_template_rag_kb','template_rag_kb'].
def _semantic_collection_names(
    base_qs,
    collection_names_for_companies,
    *,
    user=None,
    include_legacy=True,
):
    if user is not None:
        company = get_user_company(user)
        if company is None:
            return []
        return collection_names_for_companies([company.pk], include_legacy=include_legacy)
    try:
        company_ids = list(
            base_qs.order_by().values_list('company_id', flat=True).distinct()
        )
    except Exception as exc:
        _rag_search_debug(f'semantic_company_scope_failed | error={exc!r}')
        company_ids = []
    return collection_names_for_companies(company_ids, include_legacy=include_legacy)


# def _progressive_semantic_hits để gom kết quả semantic từ nhiều collection theo kiểu tăng dần cho tới khi đủ k, chỉ lấy trong queryset mà user được phép truy cập.
# vd: gom dần từ các collection tới khi đủ k=10 kết quả user được phép xem.
def _progressive_semantic_hits(question, collection_names, base_qs, k):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_progressive_semantic_hits` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    target_count = max(int(k or 1) * _SEMANTIC_TARGET_MULTIPLIER, _SEMANTIC_TARGET_MIN)
    accessible_hits = {}
    if isinstance(collection_names, str):
        collection_names = [collection_names]
    for fetch_k in _SEMANTIC_FETCH_STEPS:
        for collection_priority, collection_name in enumerate(collection_names):
            raw_hits = _semantic_rank_map(question, collection_name, fetch_k=fetch_k)
            if not raw_hits:
                continue
            accessible_map = base_qs.filter(pk__in=list(raw_hits.keys())).in_bulk()
            for obj_id, obj in accessible_map.items():
                hit = raw_hits.get(obj_id)
                if hit is None:
                    continue
                ranked_hit = {
                    **hit,
                    'collection': collection_name,
                    'collection_priority': collection_priority,
                }
                previous = accessible_hits.get(obj_id)
                if previous is None or (
                    collection_priority,
                    hit['rank'],
                ) < (
                    previous.get('collection_priority', 999),
                    previous['rank'],
                ):
                    accessible_hits[obj_id] = ranked_hit
            _rag_search_debug(
                f'semantic_progressive | collection={collection_name} | fetch_k={fetch_k} | '
                f'accessible={len(accessible_hits)} | target={target_count}'
            )
        if len(accessible_hits) >= target_count:
            break
    return accessible_hits

# def _template_secondary_text để gom các trường phụ của mẫu (mô tả, danh mục, phòng ban…) thành text bổ trợ cho tìm kiếm.
# vd: -> 'Don xin nghi | Nhan su | Phong HC' (mô tả + danh mục + phòng ban).
def _template_secondary_text(template):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_template_secondary_text` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi mau van ban trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly du lieu hoac thao tac lien quan toi mau van ban roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc xu ly du lieu hoac thao tac lien quan toi mau van ban xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    tags = ' '.join(
        str(tag).strip()
        for tag in (getattr(template, 'tags', None) or [])
        if str(tag).strip()
    )
    variables = ' '.join(sorted(template.get_variables()))
    category_name = template.category.name if template.category_id and getattr(template, 'category', None) else ''
    department_name = template.department.name if template.department_id and getattr(template, 'department', None) else ''
    group_name = template.group.name if template.group_id and getattr(template, 'group', None) else ''
    return ' '.join(
        part
        for part in [
            template.description or '',
            template.notes or '',
            category_name,
            department_name,
            group_name,
            tags,
            variables,
        ]
        if part
    ).strip()

# def _document_secondary_text để gom các trường phụ của tài liệu thành text bổ trợ cho tìm kiếm.
# vd: gom tiêu đề phụ/danh mục của văn bản cho tìm kiếm.
def _document_secondary_text(document):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_document_secondary_text` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi van ban trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly du lieu hoac thao tac lien quan toi van ban roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc xu ly du lieu hoac thao tac lien quan toi van ban xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    template_title = document.template.title if document.template_id and getattr(document, 'template', None) else ''
    category_name = document.category.name if document.category_id and getattr(document, 'category', None) else ''
    department_name = document.department.name if document.department_id and getattr(document, 'department', None) else ''
    return ' '.join(
        part
        for part in [
            document.notes or '',
            document.doc_number or '',
            template_title,
            category_name,
            department_name,
        ]
        if part
    ).strip()

# def _template_content_for_search để lấy nội dung mẫu (đã bỏ HTML) dùng cho so khớp và preview.
# vd: '<p>Kinh gui</p>' -> 'Kinh gui'.
def _template_content_for_search(template):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_template_content_for_search` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem tim kiem hoac loc du lieu theo cau hoi dau vao trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tim kiem hoac loc du lieu theo cau hoi dau vao roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc tim kiem hoac loc du lieu theo cau hoi dau vao xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    text = _strip_html_text(template.content or '')
    text = re.sub(r'\{\{\s*[\w.\-]+\s*\}\}', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

# def _document_content_for_search để lấy nội dung tài liệu (đã bỏ HTML) dùng cho so khớp và preview.
# vd: nội dung văn bản đã bỏ HTML.
def _document_content_for_search(document):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_document_content_for_search` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem tim kiem hoac loc du lieu theo cau hoi dau vao trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tim kiem hoac loc du lieu theo cau hoi dau vao roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc tim kiem hoac loc du lieu theo cau hoi dau vao xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return _strip_html_text(document.content or '')

# def _relevance_score để tính điểm liên quan tổng hợp từ khớp tiêu đề, text phụ, nội dung và độ tương đồng semantic.
# vd: khớp tiêu đề mạnh + semantic cao -> điểm tổng lớn, xếp trên.
def _relevance_score(question, *, title='', secondary='', content='', title_similarity=0.0, secondary_similarity=0.0):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_relevance_score` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    question_norm = _normalize_search_text(question)
    terms = _query_terms(question)
    title_norm = _normalize_search_text(title)
    secondary_norm = _normalize_search_text(secondary)
    content_norm = _normalize_search_text(content)

    score = 0
    matched_terms = set()
    if question_norm:
        if question_norm == title_norm:
            score += 220
        elif question_norm in title_norm:
            score += 150
        if question_norm in secondary_norm:
            score += 72
        if question_norm in content_norm:
            score += 48

    for term in terms:
        matched = False
        if term in title_norm:
            score += 28
            matched = True
        if term in secondary_norm:
            score += 16
            matched = True
        if term in content_norm:
            score += 8
            matched = True
        if matched:
            matched_terms.add(term)

    if terms:
        coverage = len(matched_terms) / len(terms)
        score += int(coverage * 48)

    score += int(float(title_similarity or 0.0) * 80)
    score += int(float(secondary_similarity or 0.0) * 40)
    return score

# def _template_candidate_queryset để dựng queryset ứng viên mẫu theo từ khóa (lọc + annotate điểm tương đồng), giới hạn limit.
# vd: 'nghi phep', limit 20 -> 20 mẫu ứng viên kèm điểm tương đồng.
def _template_candidate_queryset(base_qs, question, limit):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_template_candidate_queryset` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem tim tap ung vien phu hop voi dieu kien nghiep vu trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tim tap ung vien phu hop voi dieu kien nghiep vu roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc tim tap ung vien phu hop voi dieu kien nghiep vu xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    phrase = _normalize_search_text(question)
    terms = _query_terms(question)
    title_expr = _unaccent_expr(_text_expr('title'))
    secondary_expr = _unaccent_expr(
        Concat(
            _text_expr('description'),
            _space_expr(),
            _text_expr('notes'),
            _space_expr(),
            _text_expr('category__name'),
            _space_expr(),
            _text_expr('department__name'),
            _space_expr(),
            _text_expr('group__name'),
            output_field=TextField(),
        )
    )
    content_expr = _unaccent_expr(_text_expr('content'))
    qs = base_qs.annotate(
        search_title=title_expr,
        search_secondary=secondary_expr,
        search_content=content_expr,
        title_similarity=_similarity_expression(title_expr, phrase),
        secondary_similarity=_similarity_expression(secondary_expr, phrase),
    )

    if phrase or terms:
        filter_q = Q()
        if phrase:
            filter_q |= Q(search_title__contains=phrase) | Q(search_secondary__contains=phrase)
            filter_q |= Q(search_content__contains=phrase)
            filter_q |= Q(title_similarity__gte=0.18) | Q(secondary_similarity__gte=0.12)
        for term in terms[:10]:
            filter_q |= Q(search_title__contains=term) | Q(search_secondary__contains=term)
            filter_q |= Q(search_content__contains=term)
        qs = qs.filter(filter_q)

    return qs.order_by('-title_similarity', '-secondary_similarity', '-updated_at')[:limit]

# def _document_candidate_queryset để dựng queryset ứng viên tài liệu theo từ khóa (lọc + annotate điểm), giới hạn limit.
# vd: 'hop dong', limit 20 -> 20 văn bản ứng viên kèm điểm.
def _document_candidate_queryset(base_qs, question, limit):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_document_candidate_queryset` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem tim tap ung vien phu hop voi dieu kien nghiep vu trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tim tap ung vien phu hop voi dieu kien nghiep vu roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc tim tap ung vien phu hop voi dieu kien nghiep vu xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    phrase = _normalize_search_text(question)
    terms = _query_terms(question)
    title_expr = _unaccent_expr(_text_expr('title'))
    secondary_expr = _unaccent_expr(
        Concat(
            _text_expr('notes'),
            _space_expr(),
            _text_expr('doc_number'),
            _space_expr(),
            _text_expr('template__title'),
            _space_expr(),
            _text_expr('category__name'),
            _space_expr(),
            _text_expr('department__name'),
            output_field=TextField(),
        )
    )
    content_expr = _unaccent_expr(_text_expr('content'))
    qs = base_qs.annotate(
        search_title=title_expr,
        search_secondary=secondary_expr,
        search_content=content_expr,
        title_similarity=_similarity_expression(title_expr, phrase),
        secondary_similarity=_similarity_expression(secondary_expr, phrase),
    )

    if phrase or terms:
        filter_q = Q()
        if phrase:
            filter_q |= Q(search_title__contains=phrase) | Q(search_secondary__contains=phrase)
            filter_q |= Q(search_content__contains=phrase)
            filter_q |= Q(title_similarity__gte=0.18) | Q(secondary_similarity__gte=0.12)
        for term in terms[:10]:
            filter_q |= Q(search_title__contains=term) | Q(search_secondary__contains=term)
            filter_q |= Q(search_content__contains=term)
        qs = qs.filter(filter_q)

    return qs.order_by('-title_similarity', '-secondary_similarity', '-updated_at')[:limit]

# def _template_context để dựng khối ngữ cảnh + citation cho một mẫu khớp (tiêu đề, URL, đoạn preview).
# vd: -> {'context':'[Mau: Don xin nghi] ...','citation':{title,url:'/templates/5'}}.
def _template_context(template, question, semantic_chunk=''):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_template_context` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem chuan bi ngu canh cho buoc xu ly phia sau trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can chuan bi ngu canh cho buoc xu ly phia sau roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc chuan bi ngu canh cho buoc xu ly phia sau xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    preview = _extract_relevant_preview(
        _template_content_for_search(template),
        question,
        semantic_chunk=semantic_chunk,
    )
    return f'[Mau van ban: {template.title}]\n{preview or template.title}'

# def _document_context để dựng khối ngữ cảnh + citation cho một tài liệu khớp.
# vd: -> {'context':'[Van ban: HD thue nha] ...','citation':{url:'/documents/9'}}.
def _document_context(document, question, semantic_chunk=''):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_document_context` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem chuan bi ngu canh cho buoc xu ly phia sau trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can chuan bi ngu canh cho buoc xu ly phia sau roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc chuan bi ngu canh cho buoc xu ly phia sau xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    preview = _extract_relevant_preview(
        _document_content_for_search(document),
        question,
        semantic_chunk=semantic_chunk,
    )
    return f'[Van ban: {document.title}]\n{preview or document.title}'

# def _db_search_templates là tìm kiếm hybrid mẫu văn bản trong DB: kết hợp khớp từ khóa (SQL) và semantic (vector), chấm điểm, lọc theo ngưỡng và phạm vi truy cập của user, trả top-k ngữ cảnh + citations.
# vd: 'mau don xin nghi' -> top-k mẫu liên quan (ngữ cảnh + citation) user được xem.
def _db_search_templates(question, user, k):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_db_search_templates` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem tim kiem hoac loc du lieu theo cau hoi dau vao trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tim kiem hoac loc du lieu theo cau hoi dau vao roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc tim kiem hoac loc du lieu theo cau hoi dau vao xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    k = max(1, int(k or 1))
    base_qs = (
        get_accessible_templates(user)
        .exclude(status=STATUS_REJECTED)
        .select_related('category', 'department', 'group')
    )
    lexical_candidates = list(_template_candidate_queryset(base_qs, question, limit=max(k * 12, 80)))
    semantic_hits = _progressive_semantic_hits(
        question,
        _semantic_collection_names(
            base_qs,
            template_collection_names_for_companies,
            user=user,
            include_legacy=False,
        ),
        base_qs,
        k,
    )
    semantic_objects = base_qs.filter(pk__in=list(semantic_hits.keys())).in_bulk()

    merged_candidates = {template.pk: template for template in lexical_candidates}
    for obj_id, template in semantic_objects.items():
        merged_candidates.setdefault(obj_id, template)

    _rag_search_debug(
        f'template_hybrid_pool | lexical={len(lexical_candidates)} | '
        f'semantic={len(semantic_objects)} | merged={len(merged_candidates)}'
    )

    ranked = []
    for template in merged_candidates.values():
        content = _template_content_for_search(template)
        secondary = _template_secondary_text(template)
        title_similarity = getattr(template, 'title_similarity', 0.0)
        secondary_similarity = getattr(template, 'secondary_similarity', 0.0)
        lexical_score = _relevance_score(
            question,
            title=template.title,
            secondary=secondary,
            content=content,
            title_similarity=title_similarity,
            secondary_similarity=secondary_similarity,
        )
        semantic_hit = semantic_hits.get(template.pk, {})
        semantic_rank = semantic_hit.get('rank')
        semantic_chunk = semantic_hit.get('chunk_text', '')
        semantic_bonus = _semantic_bonus_for_rank(semantic_rank)
        combined_score = lexical_score + semantic_bonus
        if lexical_score > 0 and semantic_rank is not None:
            combined_score += 8
        ranked.append(
            (
                combined_score,
                lexical_score,
                1000 - semantic_rank if semantic_rank is not None else 0,
                template.updated_at,
                template,
                semantic_rank,
                semantic_bonus,
                semantic_chunk,
            )
        )

    ranked.sort(key=lambda item: (item[0], item[1], item[2], item[3]), reverse=True)

    minimum_score = _minimum_relevance_score(question, source='template')
    semantic_gate_limit = min(max(k, 1), 3)
    results = []
    for combined_score, lexical_score, _, _, template, semantic_rank, semantic_bonus, semantic_chunk in ranked:
        if combined_score < minimum_score and not (
            semantic_rank is not None and semantic_rank < semantic_gate_limit
        ):
            continue
        search_method = (
            'keyword+vector'
            if lexical_score > 0 and semantic_rank is not None
            else 'vector'
            if semantic_rank is not None
            else 'keyword'
        )
        results.append(
            {
                'context': _template_context(template, question, semantic_chunk=semantic_chunk),
                'citation': {
                    'id': template.pk,
                    'title': template.title,
                    'route': f'/templates/{template.pk}',
                    'url': f'/templates/{template.pk}',
                    'type': 'template',
                    'source_group': 'local',
                    'status': template.get_status_display(),
                    'category': template.category.name if template.category else '',
                    'score': combined_score,
                    'keyword_score': lexical_score,
                    'semantic_rank': semantic_rank,
                    'semantic_bonus': semantic_bonus,
                    'search_method': search_method,
                },
            }
        )
        if len(results) >= k:
            break

    _rag_search_debug(
        f'template_hybrid_selected | minimum_score={minimum_score} | returned={len(results)}'
    )
    return results

# def _db_search_documents là tìm kiếm hybrid tài liệu trong DB: kết hợp khớp từ khóa và semantic, chấm điểm, lọc theo ngưỡng và quyền truy cập của user, trả top-k ngữ cảnh + citations.
# vd: 'hop dong da ky' -> top-k văn bản liên quan user được xem.
def _db_search_documents(question, user, k):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_db_search_documents` la helper noi bo trong file `ai_engine/rag_search.py`, chiu trach nhiem tim kiem hoac loc du lieu theo cau hoi dau vao trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tim kiem hoac loc du lieu theo cau hoi dau vao roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_rag_search_debug`, `_strip_html_text`, `_normalize_search_text` trong module nay.
    Tac dung: Don buoc tim kiem hoac loc du lieu theo cau hoi dau vao xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    k = max(1, int(k or 1))
    base_qs = get_accessible_documents(user).select_related(
        'category', 'department', 'template'
    )
    lexical_candidates = list(_document_candidate_queryset(base_qs, question, limit=max(k * 12, 80)))
    semantic_hits = _progressive_semantic_hits(
        question,
        _semantic_collection_names(
            base_qs,
            document_collection_names_for_companies,
            user=user,
            include_legacy=False,
        ),
        base_qs,
        k,
    )
    semantic_objects = base_qs.filter(pk__in=list(semantic_hits.keys())).in_bulk()

    merged_candidates = {document.pk: document for document in lexical_candidates}
    for obj_id, document in semantic_objects.items():
        merged_candidates.setdefault(obj_id, document)

    _rag_search_debug(
        f'document_hybrid_pool | lexical={len(lexical_candidates)} | '
        f'semantic={len(semantic_objects)} | merged={len(merged_candidates)}'
    )

    ranked = []
    for document in merged_candidates.values():
        content = _document_content_for_search(document)
        secondary = _document_secondary_text(document)
        title_similarity = getattr(document, 'title_similarity', 0.0)
        secondary_similarity = getattr(document, 'secondary_similarity', 0.0)
        lexical_score = _relevance_score(
            question,
            title=document.title,
            secondary=secondary,
            content=content,
            title_similarity=title_similarity,
            secondary_similarity=secondary_similarity,
        )
        semantic_hit = semantic_hits.get(document.pk, {})
        semantic_rank = semantic_hit.get('rank')
        semantic_chunk = semantic_hit.get('chunk_text', '')
        semantic_bonus = _semantic_bonus_for_rank(semantic_rank)
        combined_score = lexical_score + semantic_bonus
        if lexical_score > 0 and semantic_rank is not None:
            combined_score += 8
        ranked.append(
            (
                combined_score,
                lexical_score,
                1000 - semantic_rank if semantic_rank is not None else 0,
                document.updated_at,
                document,
                semantic_rank,
                semantic_bonus,
                semantic_chunk,
            )
        )

    ranked.sort(key=lambda item: (item[0], item[1], item[2], item[3]), reverse=True)

    minimum_score = _minimum_relevance_score(question, source='document')
    semantic_gate_limit = min(max(k, 1), 2)
    results = []
    for combined_score, lexical_score, _, _, document, semantic_rank, semantic_bonus, semantic_chunk in ranked:
        if combined_score < minimum_score and not (
            semantic_rank is not None and semantic_rank < semantic_gate_limit
        ):
            continue
        search_method = (
            'keyword+vector'
            if lexical_score > 0 and semantic_rank is not None
            else 'vector'
            if semantic_rank is not None
            else 'keyword'
        )
        results.append(
            {
                'context': _document_context(document, question, semantic_chunk=semantic_chunk),
                'citation': {
                    'id': document.pk,
                    'title': document.title,
                    'route': f'/documents/{document.pk}',
                    'url': f'/documents/{document.pk}',
                    'type': 'document',
                    'source_group': 'local',
                    'status': document.get_status_display(),
                    'doc_number': document.doc_number or '',
                    'score': combined_score,
                    'keyword_score': lexical_score,
                    'semantic_rank': semantic_rank,
                    'semantic_bonus': semantic_bonus,
                    'search_method': search_method,
                },
            }
        )
        if len(results) >= k:
            break

    _rag_search_debug(
        f'document_hybrid_selected | minimum_score={minimum_score} | returned={len(results)}'
    )
    return results

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

from django.conf import settings
from django.db import DatabaseError, connection
from langchain_community.vectorstores import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

from document_templates.models import DocumentTemplate, STATUS_REJECTED
from documents.models import Document

TEMPLATE_RAG_COLLECTION = 'template_rag_kb'
DOCUMENT_RAG_COLLECTION = 'document_rag_kb'

_logger = logging.getLogger('ai_engine')
_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)


# def _template_collection_name để sinh tên collection vector cho mẫu văn bản theo công ty (hoặc tên mặc định nếu không có company).
# vd: company_id=1 -> 'company_1_template_rag_kb'; None -> 'template_rag_kb'.
def _template_collection_name(company_id=None):
    if company_id:
        return f'company_{company_id}_template_rag_kb'
    return TEMPLATE_RAG_COLLECTION


# def _document_collection_name để sinh tên collection vector cho tài liệu theo công ty (hoặc tên mặc định).
# vd: company_id=1 -> 'company_1_document_rag_kb'.
def _document_collection_name(company_id=None):
    if company_id:
        return f'company_{company_id}_document_rag_kb'
    return DOCUMENT_RAG_COLLECTION


# def template_collection_names_for_companies để liệt kê các collection mẫu cần quét cho nhiều công ty (kèm collection legacy dùng chung nếu include_legacy).
# vd: [1,2] -> ['company_1_template_rag_kb','company_2_template_rag_kb','template_rag_kb'].
def template_collection_names_for_companies(company_ids, *, include_legacy=True):
    names = []
    for company_id in company_ids:
        if not company_id:
            continue
        name = _template_collection_name(company_id)
        if name not in names:
            names.append(name)
    if include_legacy and TEMPLATE_RAG_COLLECTION not in names:
        names.append(TEMPLATE_RAG_COLLECTION)
    return names


# def document_collection_names_for_companies để liệt kê các collection tài liệu cần quét cho nhiều công ty (kèm collection legacy nếu include_legacy).
# vd: [1] -> ['company_1_document_rag_kb','document_rag_kb'].
def document_collection_names_for_companies(company_ids, *, include_legacy=True):
    names = []
    for company_id in company_ids:
        if not company_id:
            continue
        name = _document_collection_name(company_id)
        if name not in names:
            names.append(name)
    if include_legacy and DOCUMENT_RAG_COLLECTION not in names:
        names.append(DOCUMENT_RAG_COLLECTION)
    return names

# def _get_embeddings để lấy hàm embedding dùng chung (từ rag_engine.get_embeddings).
# vd: -> OllamaEmbeddings dùng chung của rag_engine.
def _get_embeddings():
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_get_embeddings` la helper noi bo trong file `ai_engine/rag_index.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `purge_template_index`, `purge_document_index`, `sync_template_index` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    from .rag_engine import get_embeddings

    return get_embeddings()

# def _strip_html_text để bỏ thẻ HTML/script/style và gộp khoảng trắng, lấy text thuần để đánh chỉ mục.
# vd: '<p>Xin <b>chao</b></p>' -> 'Xin chao'.
def _strip_html_text(value):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_strip_html_text` la helper noi bo trong file `ai_engine/rag_index.py`, chiu trach nhiem loai bo dinh dang hoac ky tu du khoi du lieu trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can loai bo dinh dang hoac ky tu du khoi du lieu roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `purge_template_index`, `purge_document_index`, `sync_template_index` goi lai.
    Tac dung: Don buoc loai bo dinh dang hoac ky tu du khoi du lieu xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    from html import unescape

    value = re.sub(r'(?is)<script.*?>.*?</script>', ' ', value or '')
    value = re.sub(r'(?is)<style.*?>.*?</style>', ' ', value)
    value = re.sub(r'(?s)<[^>]+>', ' ', value)
    value = unescape(value)
    return re.sub(r'\s+', ' ', value).strip()

# def _vectorstore để tạo PGVector cho một collection cụ thể với hàm embedding tương ứng.
# vd: _vectorstore('company_1_template_rag_kb') -> PGVector của collection đó.
def _vectorstore(collection_name):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_vectorstore` la helper noi bo trong file `ai_engine/rag_index.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `purge_template_index`, `purge_document_index`, `sync_template_index` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return PGVector(
        collection_name=collection_name,
        connection_string=settings.PGVECTOR_CONNECTION_STRING,
        embedding_function=_get_embeddings(),
    )

# def _delete_embeddings_by_object_id để xóa mọi vector của một object (theo metadata id) khỏi một collection; trả số dòng đã xóa.
# vd: xóa mọi vector của mẫu #5 trong collection -> trả số dòng đã xóa.
def _delete_embeddings_by_object_id(collection_name, object_id):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_delete_embeddings_by_object_id` la helper noi bo trong file `ai_engine/rag_index.py`, chiu trach nhiem xoa hoac don du lieu khong con hieu luc trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xoa hoac don du lieu khong con hieu luc roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `purge_template_index`, `purge_document_index`, `sync_template_index` goi lai.
    Tac dung: Don buoc xoa hoac don du lieu khong con hieu luc xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if not object_id:
        return 0
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM langchain_pg_embedding AS embedding
                USING langchain_pg_collection AS collection
                WHERE embedding.collection_id = collection.uuid
                  AND collection.name = %s
                  AND embedding.cmetadata->>'id' = %s
                """,
                [collection_name, str(int(object_id))],
            )
            return cursor.rowcount or 0
    except DatabaseError as exc:
        _logger.warning(
            'rag purge by object id skipped | collection=%s | object_id=%s | error=%s',
            collection_name,
            object_id,
            exc,
        )
        return 0

# def _delete_collection_embeddings để xóa toàn bộ vector trong một collection (dùng khi rebuild lại từ đầu).
# vd: trước khi rebuild -> xóa sạch vector trong collection.
def _delete_collection_embeddings(collection_name):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_delete_collection_embeddings` la helper noi bo trong file `ai_engine/rag_index.py`, chiu trach nhiem xoa hoac don du lieu khong con hieu luc trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xoa hoac don du lieu khong con hieu luc roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `purge_template_index`, `purge_document_index`, `sync_template_index` goi lai.
    Tac dung: Don buoc xoa hoac don du lieu khong con hieu luc xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM langchain_pg_embedding AS embedding
                USING langchain_pg_collection AS collection
                WHERE embedding.collection_id = collection.uuid
                  AND collection.name = %s
                """,
                [collection_name],
            )
            return cursor.rowcount or 0
    except DatabaseError as exc:
        _logger.warning(
            'rag purge collection skipped | collection=%s | error=%s',
            collection_name,
            exc,
        )
        return 0

# def _collection_row_count để đếm số dòng vector hiện có trong một collection.
# vd: -> 1234 (số chunk đang lưu).
def _collection_row_count(collection_name):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_collection_row_count` la helper noi bo trong file `ai_engine/rag_index.py`, chiu trach nhiem dem so ban ghi hoac so muc theo dieu kien trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can dem so ban ghi hoac so muc theo dieu kien roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `purge_template_index`, `purge_document_index`, `sync_template_index` goi lai.
    Tac dung: Don buoc dem so ban ghi hoac so muc theo dieu kien xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM langchain_pg_embedding AS embedding
                JOIN langchain_pg_collection AS collection
                  ON embedding.collection_id = collection.uuid
                WHERE collection.name = %s
                """,
                [collection_name],
            )
            row = cursor.fetchone()
    except DatabaseError:
        return 0
    return int((row or [0])[0] or 0)

# def _collection_object_ids để lấy tập id object đang được đánh chỉ mục trong một collection (để so với DB tìm bản cũ/đã mất).
# vd: -> {5, 9, 12} (id mẫu/văn bản đã index).
def _collection_object_ids(collection_name):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_collection_object_ids` la helper noi bo trong file `ai_engine/rag_index.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `purge_template_index`, `purge_document_index`, `sync_template_index` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT embedding.cmetadata->>'id'
                FROM langchain_pg_embedding AS embedding
                JOIN langchain_pg_collection AS collection
                  ON embedding.collection_id = collection.uuid
                WHERE collection.name = %s
                  AND COALESCE(embedding.cmetadata->>'id', '') <> ''
                """,
                [collection_name],
            )
            rows = cursor.fetchall()
    except DatabaseError:
        return set()

    results = set()
    for raw_id, in rows:
        try:
            results.add(int(raw_id))
        except (TypeError, ValueError):
            continue
    return results

# def _template_index_text để lấy text đánh chỉ mục cho mẫu: bỏ HTML và bỏ các placeholder {{bien}} để chỉ giữ nội dung thật.
# vd: '<p>Kinh gui {{ten}}</p>' -> 'Kinh gui' (bỏ HTML + bỏ {{ten}}).
def _template_index_text(template):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_template_index_text` la helper noi bo trong file `ai_engine/rag_index.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi mau van ban trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly du lieu hoac thao tac lien quan toi mau van ban roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `purge_template_index`, `purge_document_index`, `sync_template_index` goi lai.
    Tac dung: Don buoc xu ly du lieu hoac thao tac lien quan toi mau van ban xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    text = _strip_html_text(template.content or '')
    text = re.sub(r'\{\{\s*[\w.\-]+\s*\}\}', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

# def _document_index_text để lấy text đánh chỉ mục cho tài liệu (bỏ HTML).
# vd: '<p>Noi dung</p>' -> 'Noi dung'.
def _document_index_text(document):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_document_index_text` la helper noi bo trong file `ai_engine/rag_index.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi van ban trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly du lieu hoac thao tac lien quan toi van ban roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `purge_template_index`, `purge_document_index`, `sync_template_index` goi lai.
    Tac dung: Don buoc xu ly du lieu hoac thao tac lien quan toi van ban xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return _strip_html_text(document.content or '')

# def _chunk_metadatas để nhân bản metadata cho từng chunk và gắn thêm chunk_index.
# vd: meta + 3 chunk -> [{..,'chunk_index':0},{..,1},{..,2}].
def _chunk_metadatas(metadata, chunk_count):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_chunk_metadatas` la helper noi bo trong file `ai_engine/rag_index.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `purge_template_index`, `purge_document_index`, `sync_template_index` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return [{**metadata, 'chunk_index': index} for index in range(chunk_count)]

# def _template_metadata để dựng metadata của mẫu (id, title, url, owner_id, company_id) lưu kèm vector.
# vd: -> {'id':5,'title':'Don xin nghi','url':'/templates/5','type':'template',...}.
def _template_metadata(template):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_template_metadata` la helper noi bo trong file `ai_engine/rag_index.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi mau van ban trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly du lieu hoac thao tac lien quan toi mau van ban roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `purge_template_index`, `purge_document_index`, `sync_template_index` goi lai.
    Tac dung: Don buoc xu ly du lieu hoac thao tac lien quan toi mau van ban xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return {
        'id': template.pk,
        'title': template.title,
        'url': f'/templates/{template.pk}',
        'type': 'template',
        'owner_id': template.owner_id,
        'company_id': getattr(template, 'company_id', None),
    }

# def _document_metadata để dựng metadata của tài liệu (id, title, url, owner_id, company_id) lưu kèm vector.
# vd: -> {'id':9,'title':'HD thue nha','url':'/documents/9','type':'document',...}.
def _document_metadata(document):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_document_metadata` la helper noi bo trong file `ai_engine/rag_index.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi van ban trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly du lieu hoac thao tac lien quan toi van ban roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `purge_template_index`, `purge_document_index`, `sync_template_index` goi lai.
    Tac dung: Don buoc xu ly du lieu hoac thao tac lien quan toi van ban xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return {
        'id': document.pk,
        'title': document.title,
        'url': f'/documents/{document.pk}',
        'type': 'document',
        'owner_id': document.owner_id,
        'company_id': getattr(document, 'company_id', None),
    }

# def _resolve_template để nhận vào template hoặc id và trả về object DocumentTemplate (kể cả bản ẩn qua all_objects).
# vd: truyền 5 -> trả DocumentTemplate pk=5; truyền sẵn object -> trả luôn.
def _resolve_template(template_or_id):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_resolve_template` la helper noi bo trong file `ai_engine/rag_index.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi mau van ban trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly du lieu hoac thao tac lien quan toi mau van ban roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `purge_template_index`, `purge_document_index`, `sync_template_index` goi lai.
    Tac dung: Don buoc xu ly du lieu hoac thao tac lien quan toi mau van ban xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if isinstance(template_or_id, DocumentTemplate):
        return template_or_id
    if not template_or_id:
        return None
    return (
        DocumentTemplate.all_objects.select_related('category', 'department', 'group')
        .filter(pk=template_or_id)
        .first()
    )

# def _resolve_document để nhận vào document hoặc id và trả về object Document (kể cả bản ẩn qua all_objects).
# vd: truyền 9 -> trả Document pk=9.
def _resolve_document(document_or_id):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_resolve_document` la helper noi bo trong file `ai_engine/rag_index.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi van ban trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly du lieu hoac thao tac lien quan toi van ban roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `purge_template_index`, `purge_document_index`, `sync_template_index` goi lai.
    Tac dung: Don buoc xu ly du lieu hoac thao tac lien quan toi van ban xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if isinstance(document_or_id, Document):
        return document_or_id
    if not document_or_id:
        return None
    return (
        Document.all_objects.select_related('category', 'department', 'template')
        .filter(pk=document_or_id)
        .first()
    )

# def _write_chunks để chia text thành chunk rồi ghi vào collection kèm metadata; trả số chunk đã ghi.
# vd: text 2000 ký tự -> chia ~3 chunk, ghi vào collection, trả 3.
def _write_chunks(collection_name, text, metadata):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_write_chunks` la helper noi bo trong file `ai_engine/rag_index.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `purge_template_index`, `purge_document_index`, `sync_template_index` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    chunks = [chunk.strip() for chunk in _splitter.split_text(text or '') if chunk.strip()]
    if not chunks:
        return 0
    _vectorstore(collection_name).add_texts(chunks, _chunk_metadatas(metadata, len(chunks)))
    return len(chunks)

# def purge_template_index để xóa toàn bộ vector của một mẫu khỏi collection công ty (và cả collection legacy nếu khác).
# vd: mẫu #5 bị xóa -> purge_template_index(5) gỡ vector khỏi index.
def purge_template_index(template_or_id):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `purge_template_index` la ham nghiep vu chinh trong file `ai_engine/rag_index.py`, chiu trach nhiem xoa hoac don du lieu khong con hieu luc trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xoa hoac don du lieu khong con hieu luc roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_get_embeddings`, `_strip_html_text`, `_vectorstore` trong module nay.
    Tac dung: Don buoc xoa hoac don du lieu khong con hieu luc xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    template = _resolve_template(template_or_id)
    object_id = getattr(template_or_id, 'pk', template_or_id)
    collection_name = _template_collection_name(getattr(template, 'company_id', None))
    deleted_rows = _delete_embeddings_by_object_id(collection_name, object_id)
    if collection_name != TEMPLATE_RAG_COLLECTION:
        deleted_rows += _delete_embeddings_by_object_id(TEMPLATE_RAG_COLLECTION, object_id)
    return deleted_rows

# def purge_document_index để xóa toàn bộ vector của một tài liệu khỏi collection công ty (và collection legacy nếu khác).
# vd: văn bản #9 bị xóa -> purge_document_index(9).
def purge_document_index(document_or_id):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `purge_document_index` la ham nghiep vu chinh trong file `ai_engine/rag_index.py`, chiu trach nhiem xoa hoac don du lieu khong con hieu luc trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xoa hoac don du lieu khong con hieu luc roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_get_embeddings`, `_strip_html_text`, `_vectorstore` trong module nay.
    Tac dung: Don buoc xoa hoac don du lieu khong con hieu luc xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    document = _resolve_document(document_or_id)
    object_id = getattr(document_or_id, 'pk', document_or_id)
    collection_name = _document_collection_name(getattr(document, 'company_id', None))
    deleted_rows = _delete_embeddings_by_object_id(collection_name, object_id)
    if collection_name != DOCUMENT_RAG_COLLECTION:
        deleted_rows += _delete_embeddings_by_object_id(DOCUMENT_RAG_COLLECTION, object_id)
    return deleted_rows

# def sync_template_index để đồng bộ chỉ mục một mẫu: xóa vector cũ rồi ghi lại theo nội dung hiện tại (chỉ purge nếu mẫu bị từ chối hoặc rỗng).
# vd: sửa nội dung mẫu #5 -> sync để vector khớp nội dung mới.
def sync_template_index(template_or_id, *, raise_on_error=False):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `sync_template_index` la ham nghiep vu chinh trong file `ai_engine/rag_index.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi mau van ban trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly du lieu hoac thao tac lien quan toi mau van ban roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_get_embeddings`, `_strip_html_text`, `_vectorstore` trong module nay.
    Tac dung: Don buoc xu ly du lieu hoac thao tac lien quan toi mau van ban xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    template = _resolve_template(template_or_id)
    object_id = getattr(template_or_id, 'pk', template_or_id)
    try:
        purge_template_index(object_id)
        if template is None or template.is_deleted or template.status == STATUS_REJECTED:
            return 0
        text = _template_index_text(template)
        if not text:
            return 0
        return _write_chunks(
            _template_collection_name(getattr(template, 'company_id', None)),
            text,
            _template_metadata(template),
        )
    except Exception as exc:
        _logger.exception('template index sync failed | template_id=%s', object_id)
        if raise_on_error:
            raise
        return 0

# def sync_document_index để đồng bộ chỉ mục một tài liệu: xóa vector cũ rồi ghi lại theo nội dung hiện tại.
# vd: cập nhật văn bản #9 -> sync lại vector.
def sync_document_index(document_or_id, *, raise_on_error=False):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `sync_document_index` la ham nghiep vu chinh trong file `ai_engine/rag_index.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi van ban trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly du lieu hoac thao tac lien quan toi van ban roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_get_embeddings`, `_strip_html_text`, `_vectorstore` trong module nay.
    Tac dung: Don buoc xu ly du lieu hoac thao tac lien quan toi van ban xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    document = _resolve_document(document_or_id)
    object_id = getattr(document_or_id, 'pk', document_or_id)
    try:
        purge_document_index(object_id)
        if document is None or document.is_deleted:
            return 0
        text = _document_index_text(document)
        if not text:
            return 0
        return _write_chunks(
            _document_collection_name(getattr(document, 'company_id', None)),
            text,
            _document_metadata(document),
        )
    except Exception as exc:
        _logger.exception('document index sync failed | document_id=%s', object_id)
        if raise_on_error:
            raise
        return 0

# def rebuild_template_index để dựng lại toàn bộ chỉ mục mẫu (có thể giới hạn theo công ty): xóa sạch rồi đánh chỉ mục lại; trả thống kê đã xóa/đã đánh.
# vd: rebuild_template_index(company_id=1) -> đánh lại toàn bộ mẫu của công ty 1.
def rebuild_template_index(*, raise_on_error=False, company_id=None):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `rebuild_template_index` la ham nghiep vu chinh trong file `ai_engine/rag_index.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi mau van ban trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly du lieu hoac thao tac lien quan toi mau van ban roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_get_embeddings`, `_strip_html_text`, `_vectorstore` trong module nay.
    Tac dung: Don buoc xu ly du lieu hoac thao tac lien quan toi mau van ban xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    queryset = (
        DocumentTemplate.objects.exclude(status=STATUS_REJECTED)
        .select_related('category', 'department', 'group', 'company')
        .order_by('pk')
    )
    if company_id is not None:
        queryset = queryset.filter(company_id=company_id)
    company_ids = list(queryset.values_list('company_id', flat=True).distinct())
    deleted_rows = 0
    for company_id in company_ids:
        deleted_rows += _delete_collection_embeddings(_template_collection_name(company_id))
    indexed_chunks = 0
    for template in queryset:
        indexed_chunks += sync_template_index(template, raise_on_error=raise_on_error)
    return {
        'collection': _template_collection_name(company_id) if company_id is not None else 'company_*_template_rag_kb',
        'deleted_rows': deleted_rows,
        'indexed_objects': queryset.count(),
        'indexed_chunks': indexed_chunks,
    }

# def rebuild_document_index để dựng lại toàn bộ chỉ mục tài liệu (có thể giới hạn theo công ty): xóa sạch rồi đánh chỉ mục lại; trả thống kê.
# vd: rebuild_document_index() -> đánh lại toàn bộ văn bản.
def rebuild_document_index(*, raise_on_error=False, company_id=None):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `rebuild_document_index` la ham nghiep vu chinh trong file `ai_engine/rag_index.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi van ban trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly du lieu hoac thao tac lien quan toi van ban roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_get_embeddings`, `_strip_html_text`, `_vectorstore` trong module nay.
    Tac dung: Don buoc xu ly du lieu hoac thao tac lien quan toi van ban xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    queryset = (
        Document.objects.select_related('category', 'department', 'template', 'company')
        .order_by('pk')
    )
    if company_id is not None:
        queryset = queryset.filter(company_id=company_id)
    company_ids = list(queryset.values_list('company_id', flat=True).distinct())
    deleted_rows = 0
    for company_id in company_ids:
        deleted_rows += _delete_collection_embeddings(_document_collection_name(company_id))
    indexed_chunks = 0
    for document in queryset:
        indexed_chunks += sync_document_index(document, raise_on_error=raise_on_error)
    return {
        'collection': _document_collection_name(company_id) if company_id is not None else 'company_*_document_rag_kb',
        'deleted_rows': deleted_rows,
        'indexed_objects': queryset.count(),
        'indexed_chunks': indexed_chunks,
    }

# def _stats để tính thống kê một collection so với DB: số dòng, số object đã index, object còn sống / đã cũ (stale) / đã mất (missing).
# vd: -> {'total_rows':1200,'indexed_objects':50,'stale_objects':3,'missing_objects':2,...}.
def _stats(collection_name, live_ids):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_stats` la helper noi bo trong file `ai_engine/rag_index.py`, chiu trach nhiem tong hop so lieu thong ke trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tong hop so lieu thong ke roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `purge_template_index`, `purge_document_index`, `sync_template_index` goi lai.
    Tac dung: Don buoc tong hop so lieu thong ke xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    indexed_ids = _collection_object_ids(collection_name)
    live_ids = set(int(value) for value in live_ids)
    live_indexed_ids = indexed_ids & live_ids
    return {
        'collection': collection_name,
        'total_rows': _collection_row_count(collection_name),
        'indexed_objects': len(indexed_ids),
        'live_objects': len(live_indexed_ids),
        'stale_objects': len(indexed_ids - live_ids),
        'missing_objects': len(live_ids - indexed_ids),
        'missing_ids': sorted(live_ids - indexed_ids),
        'stale_ids': sorted(indexed_ids - live_ids),
    }


# def _multi_collection_stats để gộp thống kê từ nhiều collection (nhiều công ty + legacy) thành một báo cáo chung.
# vd: gộp số liệu của company_1 + legacy thành 1 báo cáo.
def _multi_collection_stats(collection_names, live_ids):
    all_indexed_ids = set()
    total_rows = 0
    names = []
    for collection_name in collection_names:
        if not collection_name:
            continue
        names.append(collection_name)
        total_rows += _collection_row_count(collection_name)
        all_indexed_ids |= _collection_object_ids(collection_name)
    live_ids = set(int(value) for value in live_ids)
    live_indexed_ids = all_indexed_ids & live_ids
    return {
        'collection': names,
        'total_rows': total_rows,
        'indexed_objects': len(all_indexed_ids),
        'live_objects': len(live_indexed_ids),
        'stale_objects': len(all_indexed_ids - live_ids),
        'missing_objects': len(live_ids - all_indexed_ids),
        'missing_ids': sorted(live_ids - all_indexed_ids),
        'stale_ids': sorted(all_indexed_ids - live_ids),
    }

# def template_index_stats để trả thống kê chỉ mục mẫu (toàn hệ thống hoặc theo một công ty).
# vd: template_index_stats(company_id=1) -> thống kê chỉ mục mẫu công ty 1.
def template_index_stats(company_id=None):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `template_index_stats` la ham nghiep vu chinh trong file `ai_engine/rag_index.py`, chiu trach nhiem tong hop so lieu thong ke trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tong hop so lieu thong ke roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_get_embeddings`, `_strip_html_text`, `_vectorstore` trong module nay.
    Tac dung: Don buoc tong hop so lieu thong ke xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    queryset = DocumentTemplate.objects.exclude(status=STATUS_REJECTED)
    if company_id is not None:
        queryset = queryset.filter(company_id=company_id)
    company_ids = list(queryset.values_list('company_id', flat=True).distinct())
    collection_names = [_template_collection_name(company_id) for company_id in company_ids]
    return _multi_collection_stats(collection_names, queryset.values_list('pk', flat=True))

# def document_index_stats để trả thống kê chỉ mục tài liệu (toàn hệ thống hoặc theo một công ty).
# vd: document_index_stats() -> thống kê chỉ mục văn bản toàn hệ thống.
def document_index_stats(company_id=None):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `document_index_stats` la ham nghiep vu chinh trong file `ai_engine/rag_index.py`, chiu trach nhiem tong hop so lieu thong ke trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tong hop so lieu thong ke roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_get_embeddings`, `_strip_html_text`, `_vectorstore` trong module nay.
    Tac dung: Don buoc tong hop so lieu thong ke xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    queryset = Document.objects.all()
    if company_id is not None:
        queryset = queryset.filter(company_id=company_id)
    company_ids = list(queryset.values_list('company_id', flat=True).distinct())
    collection_names = [_document_collection_name(company_id) for company_id in company_ids]
    return _multi_collection_stats(collection_names, queryset.values_list('pk', flat=True))

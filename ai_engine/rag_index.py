"""
Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
Vai tro backend: File `ai_engine/rag_index.py` giu hoac ho tro luong backend cho chat, RAG, OCR, prefill ho so, sinh van ban, luu session va quan ly tri thuc AI.
Vai tro cua no trong frontend: Cac man `/chat`, `/rag`, `/ai-doc`, `/guest` va cac dialog AI phu tro phu thuoc vao ket qua ma file nay sinh ra.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`.
Tac dung: Bao dam prompt, ket qua AI, session hoi thoai, du lieu trich xuat va chi muc RAG phuc vu dung ngu canh cua nguoi dung hien tai.
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


def _template_collection_name(company_id=None):
    if company_id:
        return f'company_{company_id}_template_rag_kb'
    return TEMPLATE_RAG_COLLECTION


def _document_collection_name(company_id=None):
    if company_id:
        return f'company_{company_id}_document_rag_kb'
    return DOCUMENT_RAG_COLLECTION

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

def _document_index_text(document):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_document_index_text` la helper noi bo trong file `ai_engine/rag_index.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi van ban trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly du lieu hoac thao tac lien quan toi van ban roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `purge_template_index`, `purge_document_index`, `sync_template_index` goi lai.
    Tac dung: Don buoc xu ly du lieu hoac thao tac lien quan toi van ban xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return _strip_html_text(document.content or '')

def _chunk_metadatas(metadata, chunk_count):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_chunk_metadatas` la helper noi bo trong file `ai_engine/rag_index.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `purge_template_index`, `purge_document_index`, `sync_template_index` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return [{**metadata, 'chunk_index': index} for index in range(chunk_count)]

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
    return _delete_embeddings_by_object_id(collection_name, object_id)

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
    return _delete_embeddings_by_object_id(collection_name, object_id)

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

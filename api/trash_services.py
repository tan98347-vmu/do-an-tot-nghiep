"""
Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
Vai tro backend: File `api/trash_services.py` giu hoac ho tro luong backend cho danh sach van ban, chi tiet van ban, version, chia se, luu tru, preview PDF, hom thu va xoa mem.
Vai tro cua no trong frontend: Cac man `/documents`, `/mailbox`, `/trash` va badge phe duyet doc ket qua do file nay cung cap hoac gian tiep lam thay doi.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`.
Tac dung: Bao dam vong doi van ban tu luc tao, chia se, xu ly hom thu toi luc phuc hoi hoac xoa vinh vien khong bi lech trang thai.
"""

import re
from datetime import timedelta
from datetime import datetime, timezone as dt_timezone

from django.db.models import Count, Q
from django.utils import timezone

from accounts.tenancy import filter_queryset_by_current_company
from ai_engine.models import ChatSession
from document_templates.models import DocumentTemplate
from documents.models import Document

TRASH_RETENTION_DAYS = 30
TRASH_RETENTION = timedelta(days=TRASH_RETENTION_DAYS)

CATEGORY_ALL = 'all'
CATEGORY_TEMPLATE = 'template'
CATEGORY_DOCUMENT = 'document'
CATEGORY_CHAT_AI_TEXT = 'chat_ai_text'
CATEGORY_CHAT_AI_VOICE = 'chat_ai_voice'
CATEGORY_RAG_TEMPLATE = 'rag_template'
CATEGORY_RAG_DOCUMENT = 'rag_document'

TRASH_CATEGORY_CHOICES = {
    CATEGORY_TEMPLATE,
    CATEGORY_DOCUMENT,
    CATEGORY_CHAT_AI_TEXT,
    CATEGORY_CHAT_AI_VOICE,
    CATEGORY_RAG_TEMPLATE,
    CATEGORY_RAG_DOCUMENT,
}

def normalize_id_list(raw_ids):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `normalize_id_list` la ham nghiep vu chinh trong file `api/trash_services.py`, chiu trach nhiem chuan hoa du lieu dau vao hoac du lieu trung gian trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can chuan hoa du lieu dau vao hoac du lieu trung gian roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_strip_html`, `_preview_text`, `_session_trash_category` trong module nay.
    Tac dung: Don buoc chuan hoa du lieu dau vao hoac du lieu trung gian xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if raw_ids is None:
        return []
    if isinstance(raw_ids, str):
        raw_ids = [part.strip() for part in raw_ids.split(',') if part.strip()]
    values = []
    for raw in raw_ids:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            continue
        if value > 0:
            values.append(value)
    deduped = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped

def _strip_html(value):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_strip_html` la helper noi bo trong file `api/trash_services.py`, chiu trach nhiem loai bo dinh dang hoac ky tu du khoi du lieu trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can loai bo dinh dang hoac ky tu du khoi du lieu roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Thuong duoc cac ham public nhu `normalize_id_list`, `mark_deleted`, `restore_deleted` goi lai.
    Tac dung: Don buoc loai bo dinh dang hoac ky tu du khoi du lieu xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return re.sub(r'<[^>]+>', ' ', str(value or ''))

def _preview_text(value, limit=180):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_preview_text` la helper noi bo trong file `api/trash_services.py`, chiu trach nhiem chuan bi noi dung xem truoc trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can chuan bi noi dung xem truoc roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Thuong duoc cac ham public nhu `normalize_id_list`, `mark_deleted`, `restore_deleted` goi lai.
    Tac dung: Don buoc chuan bi noi dung xem truoc xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    text = re.sub(r'\s+', ' ', _strip_html(value)).strip()
    if len(text) <= limit:
        return text
    return text[: max(limit - 3, 0)].rstrip() + '...'

def _session_trash_category(session):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_session_trash_category` la helper noi bo trong file `api/trash_services.py`, chiu trach nhiem quan ly vong doi phien lam viec trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can quan ly vong doi phien lam viec roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Thuong duoc cac ham public nhu `normalize_id_list`, `mark_deleted`, `restore_deleted` goi lai.
    Tac dung: Don buoc quan ly vong doi phien lam viec xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if session.session_type == ChatSession.SESSION_VOICE:
        return CATEGORY_CHAT_AI_VOICE
    if session.session_type == ChatSession.SESSION_RAG:
        return CATEGORY_RAG_DOCUMENT if session.rag_mode == 'document' else CATEGORY_RAG_TEMPLATE
    return CATEGORY_CHAT_AI_TEXT

def _expires_at(deleted_at):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_expires_at` la helper noi bo trong file `api/trash_services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Thuong duoc cac ham public nhu `normalize_id_list`, `mark_deleted`, `restore_deleted` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if not deleted_at:
        return None
    return deleted_at + TRASH_RETENTION

def mark_deleted(instance, actor):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `mark_deleted` la ham nghiep vu chinh trong file `api/trash_services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `normalize_id_list`, `_strip_html`, `_preview_text` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if getattr(instance, 'is_deleted', False):
        return False
    instance.is_deleted = True
    instance.deleted_at = timezone.now()
    instance.deleted_by = actor
    update_fields = ['is_deleted', 'deleted_at', 'deleted_by']
    if hasattr(instance, 'updated_at'):
        update_fields.append('updated_at')
    instance.save(update_fields=update_fields)
    return True

def restore_deleted(instance):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `restore_deleted` la ham nghiep vu chinh trong file `api/trash_services.py`, chiu trach nhiem khoi phuc du lieu hoac trang thai cu trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can khoi phuc du lieu hoac trang thai cu roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `normalize_id_list`, `_strip_html`, `_preview_text` trong module nay.
    Tac dung: Don buoc khoi phuc du lieu hoac trang thai cu xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if not getattr(instance, 'is_deleted', False):
        return False
    instance.is_deleted = False
    instance.deleted_at = None
    instance.deleted_by = None
    update_fields = ['is_deleted', 'deleted_at', 'deleted_by']
    if hasattr(instance, 'updated_at'):
        update_fields.append('updated_at')
    instance.save(update_fields=update_fields)
    return True

def purge_expired_trash(now=None):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `purge_expired_trash` la ham nghiep vu chinh trong file `api/trash_services.py`, chiu trach nhiem xoa hoac don du lieu khong con hieu luc trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xoa hoac don du lieu khong con hieu luc roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `normalize_id_list`, `_strip_html`, `_preview_text` trong module nay.
    Tac dung: Don buoc xoa hoac don du lieu khong con hieu luc xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    now = now or timezone.now()
    cutoff = now - TRASH_RETENTION
    payload = {
        CATEGORY_TEMPLATE: 0,
        CATEGORY_DOCUMENT: 0,
        CATEGORY_CHAT_AI_TEXT: 0,
        CATEGORY_CHAT_AI_VOICE: 0,
        CATEGORY_RAG_TEMPLATE: 0,
        CATEGORY_RAG_DOCUMENT: 0,
    }

    expired_templates = list(
        DocumentTemplate.all_objects.filter(is_deleted=True, deleted_at__lte=cutoff)
    )
    for item in expired_templates:
        item.delete()
    payload[CATEGORY_TEMPLATE] = len(expired_templates)

    expired_documents = list(
        Document.all_objects.filter(is_deleted=True, deleted_at__lte=cutoff)
    )
    for item in expired_documents:
        item.delete()
    payload[CATEGORY_DOCUMENT] = len(expired_documents)

    expired_sessions = list(
        ChatSession.all_objects.filter(is_deleted=True, deleted_at__lte=cutoff)
    )
    for item in expired_sessions:
        payload[_session_trash_category(item)] += 1
        item.delete()
    return payload

def _trash_template_queryset(user):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_trash_template_queryset` la helper noi bo trong file `api/trash_services.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi mau van ban trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly du lieu hoac thao tac lien quan toi mau van ban roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Thuong duoc cac ham public nhu `normalize_id_list`, `mark_deleted`, `restore_deleted` goi lai.
    Tac dung: Don buoc xu ly du lieu hoac thao tac lien quan toi mau van ban xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    queryset = DocumentTemplate.all_objects.filter(owner=user, is_deleted=True)
    return filter_queryset_by_current_company(queryset, user)

def _trash_document_queryset(user):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_trash_document_queryset` la helper noi bo trong file `api/trash_services.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi van ban trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly du lieu hoac thao tac lien quan toi van ban roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Thuong duoc cac ham public nhu `normalize_id_list`, `mark_deleted`, `restore_deleted` goi lai.
    Tac dung: Don buoc xu ly du lieu hoac thao tac lien quan toi van ban xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    queryset = Document.all_objects.filter(owner=user, is_deleted=True)
    return filter_queryset_by_current_company(queryset, user)

def _trash_chat_queryset(user):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_trash_chat_queryset` la helper noi bo trong file `api/trash_services.py`, chiu trach nhiem xu ly ban ghi trong thung rac trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly ban ghi trong thung rac roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Thuong duoc cac ham public nhu `normalize_id_list`, `mark_deleted`, `restore_deleted` goi lai.
    Tac dung: Don buoc xu ly ban ghi trong thung rac xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    queryset = ChatSession.all_objects.filter(user=user, is_deleted=True)
    return filter_queryset_by_current_company(queryset, user)


def _trash_template_item_queryset(user):
    return _trash_template_queryset(user)


def _trash_document_item_queryset(user):
    return _trash_document_queryset(user)


def _trash_chat_item_queryset(user):
    return _trash_chat_queryset(user)

def trash_counts(user):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `trash_counts` la ham nghiep vu chinh trong file `api/trash_services.py`, chiu trach nhiem xu ly ban ghi trong thung rac trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly ban ghi trong thung rac roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `normalize_id_list`, `_strip_html`, `_preview_text` trong module nay.
    Tac dung: Don buoc xu ly ban ghi trong thung rac xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    chat_qs = _trash_chat_queryset(user)
    counts = {
        CATEGORY_TEMPLATE: _trash_template_queryset(user).count(),
        CATEGORY_DOCUMENT: _trash_document_queryset(user).count(),
        CATEGORY_CHAT_AI_TEXT: chat_qs.filter(
            session_type__in=[ChatSession.SESSION_ASSISTANT, ChatSession.SESSION_CHAT]
        ).count(),
        CATEGORY_CHAT_AI_VOICE: chat_qs.filter(
            session_type=ChatSession.SESSION_VOICE
        ).count(),
        CATEGORY_RAG_TEMPLATE: chat_qs.filter(session_type=ChatSession.SESSION_RAG).exclude(
            rag_mode='document'
        ).count(),
        CATEGORY_RAG_DOCUMENT: chat_qs.filter(
            session_type=ChatSession.SESSION_RAG,
            rag_mode='document',
        ).count(),
    }
    counts[CATEGORY_ALL] = sum(counts.values())
    return counts

def list_trash_entries(user, *, category=CATEGORY_ALL, query=''):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `list_trash_entries` la ham nghiep vu chinh trong file `api/trash_services.py`, chiu trach nhiem tra danh sach du lieu theo bo loc hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tra danh sach du lieu theo bo loc hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `normalize_id_list`, `_strip_html`, `_preview_text` trong module nay.
    Tac dung: Don buoc tra danh sach du lieu theo bo loc hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    query = str(query or '').strip()
    counts = trash_counts(user)
    results = []

    if category not in TRASH_CATEGORY_CHOICES and category != CATEGORY_ALL:
        category = CATEGORY_ALL

    if category in {CATEGORY_ALL, CATEGORY_TEMPLATE}:
        qs = _trash_template_queryset(user)
        if query:
            qs = qs.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(content__icontains=query)
                | Q(notes__icontains=query)
            )
        for item in qs.order_by('-deleted_at'):
            results.append({
                'category': CATEGORY_TEMPLATE,
                'id': item.id,
                'trash_key': f'{CATEGORY_TEMPLATE}:{item.id}',
                'title': item.title,
                'subtitle': 'Mau van ban',
                'preview': _preview_text(item.description or item.content),
                'deleted_at': item.deleted_at,
                'expires_at': _expires_at(item.deleted_at),
                'message_count': 0,
                'audio_count': 0,
            })

    if category in {CATEGORY_ALL, CATEGORY_DOCUMENT}:
        qs = _trash_document_queryset(user)
        if query:
            qs = qs.filter(
                Q(title__icontains=query)
                | Q(content__icontains=query)
                | Q(notes__icontains=query)
                | Q(doc_number__icontains=query)
            )
        for item in qs.order_by('-deleted_at'):
            results.append({
                'category': CATEGORY_DOCUMENT,
                'id': item.id,
                'trash_key': f'{CATEGORY_DOCUMENT}:{item.id}',
                'title': item.title,
                'subtitle': 'Van ban',
                'preview': _preview_text(item.notes or item.content),
                'deleted_at': item.deleted_at,
                'expires_at': _expires_at(item.deleted_at),
                'message_count': 0,
                'audio_count': 0,
            })

    chat_categories = {
        CATEGORY_CHAT_AI_TEXT,
        CATEGORY_CHAT_AI_VOICE,
        CATEGORY_RAG_TEMPLATE,
        CATEGORY_RAG_DOCUMENT,
    }
    if category in chat_categories or category == CATEGORY_ALL:
        qs = _trash_chat_queryset(user).prefetch_related('messages').annotate(
            message_count_value=Count('messages', distinct=True),
            audio_count_value=Count('audio_attachments', distinct=True),
        )
        if query:
            qs = qs.filter(
                Q(title__icontains=query) | Q(messages__content__icontains=query)
            ).distinct()

        if category == CATEGORY_CHAT_AI_TEXT:
            qs = qs.filter(session_type__in=[ChatSession.SESSION_ASSISTANT, ChatSession.SESSION_CHAT])
        elif category == CATEGORY_CHAT_AI_VOICE:
            qs = qs.filter(session_type=ChatSession.SESSION_VOICE)
        elif category == CATEGORY_RAG_TEMPLATE:
            qs = qs.filter(session_type=ChatSession.SESSION_RAG).exclude(rag_mode='document')
        elif category == CATEGORY_RAG_DOCUMENT:
            qs = qs.filter(session_type=ChatSession.SESSION_RAG, rag_mode='document')

        for item in qs.order_by('-deleted_at'):
            first_message = ''
            for message in item.messages.all():
                if str(message.content or '').strip():
                    first_message = message.content
                    break
            entry_category = _session_trash_category(item)
            results.append({
                'category': entry_category,
                'id': item.id,
                'trash_key': f'{entry_category}:{item.id}',
                'title': item.title,
                'subtitle': 'Lich su tro chuyen',
                'preview': _preview_text(first_message),
                'deleted_at': item.deleted_at,
                'expires_at': _expires_at(item.deleted_at),
                'message_count': getattr(item, 'message_count_value', 0),
                'audio_count': getattr(item, 'audio_count_value', 0),
            })

    results.sort(
        key=lambda item: item.get('deleted_at')
        or datetime.min.replace(tzinfo=dt_timezone.utc),
        reverse=True,
    )
    return {
        'counts': counts,
        'results': results,
    }

def restore_trash_items(user, items):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `restore_trash_items` la ham nghiep vu chinh trong file `api/trash_services.py`, chiu trach nhiem khoi phuc du lieu hoac trang thai cu trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can khoi phuc du lieu hoac trang thai cu roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `normalize_id_list`, `_strip_html`, `_preview_text` trong module nay.
    Tac dung: Don buoc khoi phuc du lieu hoac trang thai cu xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    restored_count = 0
    skipped_count = 0

    for raw_item in items or []:
        category = str((raw_item or {}).get('category') or '').strip()
        try:
            item_id = int((raw_item or {}).get('id'))
        except (TypeError, ValueError):
            skipped_count += 1
            continue

        obj = None
        if category == CATEGORY_TEMPLATE:
            obj = _trash_template_item_queryset(user).filter(pk=item_id).first()
        elif category == CATEGORY_DOCUMENT:
            obj = _trash_document_item_queryset(user).filter(pk=item_id).first()
        elif category == CATEGORY_CHAT_AI_TEXT:
            obj = _trash_chat_item_queryset(user).filter(
                pk=item_id,
                session_type__in=[ChatSession.SESSION_ASSISTANT, ChatSession.SESSION_CHAT],
            ).first()
        elif category == CATEGORY_CHAT_AI_VOICE:
            obj = _trash_chat_item_queryset(user).filter(
                pk=item_id,
                session_type=ChatSession.SESSION_VOICE,
            ).first()
        elif category == CATEGORY_RAG_TEMPLATE:
            obj = _trash_chat_item_queryset(user).filter(
                pk=item_id,
                session_type=ChatSession.SESSION_RAG,
            ).exclude(rag_mode='document').first()
        elif category == CATEGORY_RAG_DOCUMENT:
            obj = _trash_chat_item_queryset(user).filter(
                pk=item_id,
                session_type=ChatSession.SESSION_RAG,
                rag_mode='document',
            ).first()

        if obj is None or not restore_deleted(obj):
            skipped_count += 1
            continue
        restored_count += 1

    return {
        'restored_count': restored_count,
        'skipped_count': skipped_count,
    }

def permanently_delete_trash_items(user, items):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `permanently_delete_trash_items` la ham nghiep vu chinh trong file `api/trash_services.py`, chiu trach nhiem xoa hoac don du lieu khong con hieu luc trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xoa hoac don du lieu khong con hieu luc roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `normalize_id_list`, `_strip_html`, `_preview_text` trong module nay.
    Tac dung: Don buoc xoa hoac don du lieu khong con hieu luc xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    deleted_count = 0
    skipped_count = 0

    for raw_item in items or []:
        category = str((raw_item or {}).get('category') or '').strip()
        try:
            item_id = int((raw_item or {}).get('id'))
        except (TypeError, ValueError):
            skipped_count += 1
            continue

        obj = None
        if category == CATEGORY_TEMPLATE:
            obj = _trash_template_item_queryset(user).filter(pk=item_id).first()
        elif category == CATEGORY_DOCUMENT:
            obj = _trash_document_item_queryset(user).filter(pk=item_id).first()
        elif category == CATEGORY_CHAT_AI_TEXT:
            obj = _trash_chat_item_queryset(user).filter(
                pk=item_id,
                session_type__in=[ChatSession.SESSION_ASSISTANT, ChatSession.SESSION_CHAT],
            ).first()
        elif category == CATEGORY_CHAT_AI_VOICE:
            obj = _trash_chat_item_queryset(user).filter(
                pk=item_id,
                session_type=ChatSession.SESSION_VOICE,
            ).first()
        elif category == CATEGORY_RAG_TEMPLATE:
            obj = _trash_chat_item_queryset(user).filter(
                pk=item_id,
                session_type=ChatSession.SESSION_RAG,
            ).exclude(rag_mode='document').first()
        elif category == CATEGORY_RAG_DOCUMENT:
            obj = _trash_chat_item_queryset(user).filter(
                pk=item_id,
                session_type=ChatSession.SESSION_RAG,
                rag_mode='document',
            ).first()

        if obj is None:
            skipped_count += 1
            continue

        obj.delete()
        deleted_count += 1

    return {
        'deleted_count': deleted_count,
        'skipped_count': skipped_count,
    }

def soft_delete_chat_sessions(user, session_ids, *, actor, session_types=None, rag_mode=None):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `soft_delete_chat_sessions` la ham nghiep vu chinh trong file `api/trash_services.py`, chiu trach nhiem xoa hoac don du lieu khong con hieu luc trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xoa hoac don du lieu khong con hieu luc roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `normalize_id_list`, `_strip_html`, `_preview_text` trong module nay.
    Tac dung: Don buoc xoa hoac don du lieu khong con hieu luc xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    normalized_ids = normalize_id_list(session_ids)
    if not normalized_ids:
        return {'deleted_count': 0, 'skipped_count': 0}

    qs = ChatSession.all_objects.filter(
        user=user,
        is_deleted=False,
        pk__in=normalized_ids,
    )
    qs = filter_queryset_by_current_company(qs, user)
    if session_types:
        qs = qs.filter(session_type__in=session_types)
    if rag_mode == 'document':
        qs = qs.filter(session_type=ChatSession.SESSION_RAG, rag_mode='document')
    elif rag_mode == 'template':
        qs = qs.filter(session_type=ChatSession.SESSION_RAG).exclude(rag_mode='document')

    deleted_count = 0
    for session in qs:
        if mark_deleted(session, actor):
            deleted_count += 1
    skipped_count = len(normalized_ids) - deleted_count
    return {
        'deleted_count': deleted_count,
        'skipped_count': skipped_count,
    }

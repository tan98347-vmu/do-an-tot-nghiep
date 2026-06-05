"""
Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
Vai tro backend: File `documents/signals.py` giu hoac ho tro luong backend cho danh sach van ban, chi tiet van ban, version, chia se, luu tru, preview PDF, hom thu va xoa mem.
Vai tro cua no trong frontend: Cac man `/documents`, `/mailbox`, `/trash` va badge phe duyet doc ket qua do file nay cung cap hoac gian tiep lam thay doi.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`.
Tac dung: Bao dam vong doi van ban tu luc tao, chia se, xu ly hom thu toi luc phuc hoi hoac xoa vinh vien khong bi lech trang thai.
"""

import logging

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from ai_engine.rag_index import purge_document_index, sync_document_index

from .models import Document, DocumentVersion

_logger = logging.getLogger('ai_engine')
_DOCUMENT_INDEX_FIELDS = {
    'title',
    'content',
    'notes',
    'template',
    'template_id',
    'category',
    'category_id',
    'department',
    'department_id',
    'doc_number',
    'is_deleted',
}

def _delete_field_file(instance, field_name):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_delete_field_file` la signal handler hoac helper signal trong file `documents/signals.py`, chiu trach nhiem xoa hoac don du lieu khong con hieu luc sau khi model doi trang thai.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep signal; giao dien chi nhin thay tac dong nen cua buoc xoa hoac don du lieu khong con hieu luc sau khi du lieu duoc luu hoac xoa.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_delete_document_output_file`, `_should_sync_document_index`, `_safe_sync_document` trong module nay.
    Tac dung: Tu dong hoa buoc xoa hoac don du lieu khong con hieu luc de nguoi dung khong phai kich hoat dong bo thu cong.
    """
    file_field = getattr(instance, field_name, None)
    if not file_field:
        return
    try:
        storage = file_field.storage
        name = file_field.name
        if name and storage.exists(name):
            storage.delete(name)
    except Exception:
        pass

@receiver(post_delete, sender=Document)
def _delete_document_output_file(sender, instance, **kwargs):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_delete_document_output_file` la signal handler hoac helper signal trong file `documents/signals.py`, chiu trach nhiem xoa hoac don du lieu khong con hieu luc sau khi model doi trang thai.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep signal; giao dien chi nhin thay tac dong nen cua buoc xoa hoac don du lieu khong con hieu luc sau khi du lieu duoc luu hoac xoa.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_delete_field_file`, `_should_sync_document_index`, `_safe_sync_document` trong module nay.
    Tac dung: Tu dong hoa buoc xoa hoac don du lieu khong con hieu luc de nguoi dung khong phai kich hoat dong bo thu cong.
    """
    _delete_field_file(instance, 'output_file')

def _should_sync_document_index(update_fields):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_should_sync_document_index` la signal handler hoac helper signal trong file `documents/signals.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi van ban sau khi model doi trang thai.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep signal; giao dien chi nhin thay tac dong nen cua buoc xu ly du lieu hoac thao tac lien quan toi van ban sau khi du lieu duoc luu hoac xoa.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_delete_field_file`, `_delete_document_output_file`, `_safe_sync_document` trong module nay.
    Tac dung: Tu dong hoa buoc xu ly du lieu hoac thao tac lien quan toi van ban de nguoi dung khong phai kich hoat dong bo thu cong.
    """
    if update_fields is None:
        return True
    return bool(set(update_fields) & _DOCUMENT_INDEX_FIELDS)

def _safe_sync_document(document_id):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_safe_sync_document` la signal handler hoac helper signal trong file `documents/signals.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi van ban sau khi model doi trang thai.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep signal; giao dien chi nhin thay tac dong nen cua buoc xu ly du lieu hoac thao tac lien quan toi van ban sau khi du lieu duoc luu hoac xoa.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_delete_field_file`, `_delete_document_output_file`, `_should_sync_document_index` trong module nay.
    Tac dung: Tu dong hoa buoc xu ly du lieu hoac thao tac lien quan toi van ban de nguoi dung khong phai kich hoat dong bo thu cong.
    """
    try:
        sync_document_index(document_id)
    except Exception:
        _logger.exception('document auto reindex failed | document_id=%s', document_id)

def _safe_purge_document(document_id):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_safe_purge_document` la signal handler hoac helper signal trong file `documents/signals.py`, chiu trach nhiem xoa hoac don du lieu khong con hieu luc sau khi model doi trang thai.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep signal; giao dien chi nhin thay tac dong nen cua buoc xoa hoac don du lieu khong con hieu luc sau khi du lieu duoc luu hoac xoa.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_delete_field_file`, `_delete_document_output_file`, `_should_sync_document_index` trong module nay.
    Tac dung: Tu dong hoa buoc xoa hoac don du lieu khong con hieu luc de nguoi dung khong phai kich hoat dong bo thu cong.
    """
    try:
        purge_document_index(document_id)
    except Exception:
        _logger.exception('document auto purge failed | document_id=%s', document_id)

@receiver(post_save, sender=Document)
def _sync_document_search_index(sender, instance, created, update_fields=None, **kwargs):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_sync_document_search_index` la signal handler hoac helper signal trong file `documents/signals.py`, chiu trach nhiem tim kiem hoac loc du lieu theo cau hoi dau vao sau khi model doi trang thai.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep signal; giao dien chi nhin thay tac dong nen cua buoc tim kiem hoac loc du lieu theo cau hoi dau vao sau khi du lieu duoc luu hoac xoa.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_delete_field_file`, `_delete_document_output_file`, `_should_sync_document_index` trong module nay.
    Tac dung: Tu dong hoa buoc tim kiem hoac loc du lieu theo cau hoi dau vao de nguoi dung khong phai kich hoat dong bo thu cong.
    """
    if not _should_sync_document_index(update_fields):
        return
    callback = _safe_purge_document if instance.is_deleted else _safe_sync_document
    transaction.on_commit(lambda document_id=instance.pk: callback(document_id))

@receiver(post_delete, sender=Document)
def _purge_document_search_index(sender, instance, **kwargs):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_purge_document_search_index` la signal handler hoac helper signal trong file `documents/signals.py`, chiu trach nhiem xoa hoac don du lieu khong con hieu luc sau khi model doi trang thai.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep signal; giao dien chi nhin thay tac dong nen cua buoc xoa hoac don du lieu khong con hieu luc sau khi du lieu duoc luu hoac xoa.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_delete_field_file`, `_delete_document_output_file`, `_should_sync_document_index` trong module nay.
    Tac dung: Tu dong hoa buoc xoa hoac don du lieu khong con hieu luc de nguoi dung khong phai kich hoat dong bo thu cong.
    """
    transaction.on_commit(lambda document_id=instance.pk: _safe_purge_document(document_id))

@receiver(post_delete, sender=DocumentVersion)
def _delete_document_version_output_file(sender, instance, **kwargs):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_delete_document_version_output_file` la signal handler hoac helper signal trong file `documents/signals.py`, chiu trach nhiem xoa hoac don du lieu khong con hieu luc sau khi model doi trang thai.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep signal; giao dien chi nhin thay tac dong nen cua buoc xoa hoac don du lieu khong con hieu luc sau khi du lieu duoc luu hoac xoa.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_delete_field_file`, `_delete_document_output_file`, `_should_sync_document_index` trong module nay.
    Tac dung: Tu dong hoa buoc xoa hoac don du lieu khong con hieu luc de nguoi dung khong phai kich hoat dong bo thu cong.
    """
    _delete_field_file(instance, 'output_file')

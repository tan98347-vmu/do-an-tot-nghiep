"""
Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
Vai tro backend: File `document_templates/signals.py` giu hoac ho tro luong backend cho CRUD mau, duyet mau, version mau, import DOCX/URL, bulk upload va preview noi dung mau.
Vai tro cua no trong frontend: Cac man `/templates`, `/templates/create`, man chi tiet mau va man bulk upload lay du lieu hoac chiu tac dong gian tiep tu file nay.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`.
Tac dung: Giu cho du lieu mau, quyen thao tac va preview cua nhom man Mau van ban luon dong nhat giua API, storage va chi so tim kiem.
"""

import logging

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from ai_engine.rag_index import purge_template_index, sync_template_index

from .models import DocumentTemplate, TemplateVersion, STATUS_REJECTED

_logger = logging.getLogger('ai_engine')
_TEMPLATE_INDEX_FIELDS = {
    'title',
    'description',
    'content',
    'notes',
    'tags',
    'category',
    'category_id',
    'department',
    'department_id',
    'group',
    'group_id',
    'source_type',
    'status',
    'is_deleted',
}

def _delete_field_file(instance, field_name):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Ham `_delete_field_file` la signal handler hoac helper signal trong file `document_templates/signals.py`, chiu trach nhiem xoa hoac don du lieu khong con hieu luc sau khi model doi trang thai.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep signal; giao dien chi nhin thay tac dong nen cua buoc xoa hoac don du lieu khong con hieu luc sau khi du lieu duoc luu hoac xoa.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Dung cung cap voi cac ham `_delete_template_docx_file`, `_should_sync_template_index`, `_safe_sync_template` trong module nay.
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

@receiver(post_delete, sender=DocumentTemplate)
def _delete_template_docx_file(sender, instance, **kwargs):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Ham `_delete_template_docx_file` la signal handler hoac helper signal trong file `document_templates/signals.py`, chiu trach nhiem xoa hoac don du lieu khong con hieu luc sau khi model doi trang thai.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep signal; giao dien chi nhin thay tac dong nen cua buoc xoa hoac don du lieu khong con hieu luc sau khi du lieu duoc luu hoac xoa.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Dung cung cap voi cac ham `_delete_field_file`, `_should_sync_template_index`, `_safe_sync_template` trong module nay.
    Tac dung: Tu dong hoa buoc xoa hoac don du lieu khong con hieu luc de nguoi dung khong phai kich hoat dong bo thu cong.
    """
    _delete_field_file(instance, 'docx_file')

def _should_sync_template_index(update_fields):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Ham `_should_sync_template_index` la signal handler hoac helper signal trong file `document_templates/signals.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi mau van ban sau khi model doi trang thai.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep signal; giao dien chi nhin thay tac dong nen cua buoc xu ly du lieu hoac thao tac lien quan toi mau van ban sau khi du lieu duoc luu hoac xoa.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Dung cung cap voi cac ham `_delete_field_file`, `_delete_template_docx_file`, `_safe_sync_template` trong module nay.
    Tac dung: Tu dong hoa buoc xu ly du lieu hoac thao tac lien quan toi mau van ban de nguoi dung khong phai kich hoat dong bo thu cong.
    """
    if update_fields is None:
        return True
    return bool(set(update_fields) & _TEMPLATE_INDEX_FIELDS)

def _safe_sync_template(template_id):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Ham `_safe_sync_template` la signal handler hoac helper signal trong file `document_templates/signals.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi mau van ban sau khi model doi trang thai.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep signal; giao dien chi nhin thay tac dong nen cua buoc xu ly du lieu hoac thao tac lien quan toi mau van ban sau khi du lieu duoc luu hoac xoa.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Dung cung cap voi cac ham `_delete_field_file`, `_delete_template_docx_file`, `_should_sync_template_index` trong module nay.
    Tac dung: Tu dong hoa buoc xu ly du lieu hoac thao tac lien quan toi mau van ban de nguoi dung khong phai kich hoat dong bo thu cong.
    """
    try:
        sync_template_index(template_id)
    except Exception:
        _logger.exception('template auto reindex failed | template_id=%s', template_id)

def _safe_purge_template(template_id):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Ham `_safe_purge_template` la signal handler hoac helper signal trong file `document_templates/signals.py`, chiu trach nhiem xoa hoac don du lieu khong con hieu luc sau khi model doi trang thai.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep signal; giao dien chi nhin thay tac dong nen cua buoc xoa hoac don du lieu khong con hieu luc sau khi du lieu duoc luu hoac xoa.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Dung cung cap voi cac ham `_delete_field_file`, `_delete_template_docx_file`, `_should_sync_template_index` trong module nay.
    Tac dung: Tu dong hoa buoc xoa hoac don du lieu khong con hieu luc de nguoi dung khong phai kich hoat dong bo thu cong.
    """
    try:
        purge_template_index(template_id)
    except Exception:
        _logger.exception('template auto purge failed | template_id=%s', template_id)

@receiver(post_save, sender=DocumentTemplate)
def _sync_template_search_index(sender, instance, created, update_fields=None, **kwargs):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Ham `_sync_template_search_index` la signal handler hoac helper signal trong file `document_templates/signals.py`, chiu trach nhiem tim kiem hoac loc du lieu theo cau hoi dau vao sau khi model doi trang thai.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep signal; giao dien chi nhin thay tac dong nen cua buoc tim kiem hoac loc du lieu theo cau hoi dau vao sau khi du lieu duoc luu hoac xoa.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Dung cung cap voi cac ham `_delete_field_file`, `_delete_template_docx_file`, `_should_sync_template_index` trong module nay.
    Tac dung: Tu dong hoa buoc tim kiem hoac loc du lieu theo cau hoi dau vao de nguoi dung khong phai kich hoat dong bo thu cong.
    """
    if not _should_sync_template_index(update_fields):
        return
    callback = _safe_purge_template if instance.is_deleted or instance.status == STATUS_REJECTED else _safe_sync_template
    transaction.on_commit(lambda template_id=instance.pk: callback(template_id))

@receiver(post_delete, sender=DocumentTemplate)
def _purge_template_search_index(sender, instance, **kwargs):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Ham `_purge_template_search_index` la signal handler hoac helper signal trong file `document_templates/signals.py`, chiu trach nhiem xoa hoac don du lieu khong con hieu luc sau khi model doi trang thai.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep signal; giao dien chi nhin thay tac dong nen cua buoc xoa hoac don du lieu khong con hieu luc sau khi du lieu duoc luu hoac xoa.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Dung cung cap voi cac ham `_delete_field_file`, `_delete_template_docx_file`, `_should_sync_template_index` trong module nay.
    Tac dung: Tu dong hoa buoc xoa hoac don du lieu khong con hieu luc de nguoi dung khong phai kich hoat dong bo thu cong.
    """
    transaction.on_commit(lambda template_id=instance.pk: _safe_purge_template(template_id))

@receiver(post_delete, sender=TemplateVersion)
def _delete_template_version_docx_file(sender, instance, **kwargs):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Ham `_delete_template_version_docx_file` la signal handler hoac helper signal trong file `document_templates/signals.py`, chiu trach nhiem xoa hoac don du lieu khong con hieu luc sau khi model doi trang thai.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep signal; giao dien chi nhin thay tac dong nen cua buoc xoa hoac don du lieu khong con hieu luc sau khi du lieu duoc luu hoac xoa.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Dung cung cap voi cac ham `_delete_field_file`, `_delete_template_docx_file`, `_should_sync_template_index` trong module nay.
    Tac dung: Tu dong hoa buoc xoa hoac don du lieu khong con hieu luc de nguoi dung khong phai kich hoat dong bo thu cong.
    """
    _delete_field_file(instance, 'docx_file')

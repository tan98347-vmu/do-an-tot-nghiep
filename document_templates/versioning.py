"""
Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
Vai tro backend: File `document_templates/versioning.py` giu hoac ho tro luong backend cho CRUD mau, duyet mau, version mau, import DOCX/URL, bulk upload va preview noi dung mau.
Vai tro cua no trong frontend: Cac man `/templates`, `/templates/create`, man chi tiet mau va man bulk upload lay du lieu hoac chiu tac dong gian tiep tu file nay.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`.
Tac dung: Giu cho du lieu mau, quyen thao tac va preview cua nhom man Mau van ban luon dong nhat giua API, storage va chi so tim kiem.
"""

import os

from django.core.files.base import ContentFile

from .models import TemplateVersion

def _template_version_docx_name(template, version_number):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Ham `_template_version_docx_name` la mot don vi xu ly backend cua file `document_templates/versioning.py`, chu yeu de quan ly du lieu phien ban.
    Vai tro cua no trong frontend: Frontend chu yeu quan sat ket qua gian tiep cua buoc quan ly du lieu phien ban nay thong qua API, du lieu luu tru hoac trang thai do lop goi phia tren tra ve.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Thuong duoc cac ham public nhu `create_template_version_snapshot` goi lai.
    Tac dung: Tach rieng trach nhiem quan ly du lieu phien ban de pham vi tac dong cua `_template_version_docx_name` ro rang hon.
    """
    original_name = os.path.basename(getattr(template.docx_file, 'name', '') or '').strip()
    if original_name:
        stem, ext = os.path.splitext(original_name)
        ext = ext or '.docx'
        return f'{stem}_v{version_number}{ext}'
    return f'template_{template.pk}_v{version_number}.docx'

def create_template_version_snapshot(template, *, created_by=None, change_note=''):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Ham `create_template_version_snapshot` la mot don vi xu ly backend cua file `document_templates/versioning.py`, chu yeu de tao moi ban ghi hoac khoi tao mot luong xu ly.
    Vai tro cua no trong frontend: Frontend chu yeu quan sat ket qua gian tiep cua buoc tao moi ban ghi hoac khoi tao mot luong xu ly nay thong qua API, du lieu luu tru hoac trang thai do lop goi phia tren tra ve.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Dung cung cap voi cac ham `_template_version_docx_name` trong module nay.
    Tac dung: Tach rieng trach nhiem tao moi ban ghi hoac khoi tao mot luong xu ly de pham vi tac dong cua `create_template_version_snapshot` ro rang hon.
    """
    version = TemplateVersion.objects.create(
        template=template,
        version_number=template.version,
        content=template.content,
        created_by=created_by,
        change_note=change_note,
    )
    if not getattr(template, 'docx_file', None):
        return version

    try:
        with template.docx_file.open('rb') as docx_handle:
            docx_bytes = docx_handle.read()
        if docx_bytes:
            version.docx_file.save(
                _template_version_docx_name(template, template.version),
                ContentFile(docx_bytes),
                save=False,
            )
            version.save(update_fields=['docx_file'])
    except Exception:
        pass
    return version

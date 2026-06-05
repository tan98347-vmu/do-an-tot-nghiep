"""
Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
Vai tro backend: File `document_templates/runtime_app.py` giu hoac ho tro luong backend cho CRUD mau, duyet mau, version mau, import DOCX/URL, bulk upload va preview noi dung mau.
Vai tro cua no trong frontend: Cac man `/templates`, `/templates/create`, man chi tiet mau va man bulk upload lay du lieu hoac chiu tac dong gian tiep tu file nay.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`.
Tac dung: Giu cho du lieu mau, quyen thao tac va preview cua nhom man Mau van ban luon dong nhat giua API, storage va chi so tim kiem.
"""

from django.apps import AppConfig

class DocumentTemplatesRuntimeConfig(AppConfig):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Lop `DocumentTemplatesRuntimeConfig` dang ky cau hinh khoi dong va hook `ready()` cua app trong file `document_templates/runtime_app.py`.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; no tac dong gian tiep bang cach bao dam signal, runtime override hoac side effect nen da san sang truoc khi API phuc vu man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong pham vi module hien tai.
    Tac dung: Kich hoat dung wiring cua app khi Django khoi dong de cac man nav khong gap trang thai thieu hook nen.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'document_templates'
    verbose_name = 'Mau Van Ban'

    

    def ready(self):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `ready` xu ly phan ha tang hoac wiring cua file `document_templates/runtime_app.py` trong lop `DocumentTemplatesRuntimeConfig`, cu the la nap signal, runtime hook hoac wiring khoi dong cua app.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep ham nay; no huong tac dong gian tiep vi route, cau hinh hoac hook nen can buoc nap signal, runtime hook hoac wiring khoi dong cua app truoc khi phuc vu request.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong lop `DocumentTemplatesRuntimeConfig` va phuc vu luong xu ly cua lop nay.
        Tac dung: Giu cho lop ha tang van hanh on dinh bang cach chot rieng buoc nap signal, runtime hook hoac wiring khoi dong cua app.
        """
        from . import signals  
        from .runtime_overrides import apply_runtime_overrides

        apply_runtime_overrides()

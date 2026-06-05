"""
Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
Vai tro backend: File `signing/apps.py` giu hoac ho tro luong backend cho de xuat ky, packet ky, nhiem vu ky, xac minh PDF, PKI noi bo va quyen uy quyen.
Vai tro cua no trong frontend: Cac man `/signing/tasks`, `/signed-pdfs`, `/signing/access` va mot phan thao tac o `/mailbox` phu thuoc truc tiep hoac gian tiep vao file nay.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`.
Tac dung: Giu cho quy trinh ky nhieu buoc, trang thai chu ky va kiem tra toan ven PDF nhat quan giua nguoi de xuat, nguoi ky va man tra cuu.
"""

from django.apps import AppConfig

class SigningConfig(AppConfig):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `SigningConfig` dang ky cau hinh khoi dong va hook `ready()` cua app trong file `signing/apps.py`.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; no tac dong gian tiep bang cach bao dam signal, runtime override hoac side effect nen da san sang truoc khi API phuc vu man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi module hien tai.
    Tac dung: Kich hoat dung wiring cua app khi Django khoi dong de cac man nav khong gap trang thai thieu hook nen.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'signing'
    verbose_name = 'Ky so noi bo'

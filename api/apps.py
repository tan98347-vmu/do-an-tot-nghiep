"""
Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
Vai tro backend: File `api/apps.py` giu hoac ho tro luong backend cho cau hinh du an, anh xa route, thong ke dashboard, quan tri du lieu nen va API chung toan he thong.
Vai tro cua no trong frontend: Cac man `/dashboard`, `/admin`, `/admin/ai-config`, `/admin/backup`, badge thong bao va shell dieu huong doc hoac chiu tac dong tu file nay.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`.
Tac dung: Giu cho cac man dieu phoi cap he thong co cung nguon cau hinh, cung route va cung so lieu nen khi frontend khoi chay.
"""

from django.apps import AppConfig

# class ApiConfig là cấu hình khởi động của app.
# vd: gom các thuộc tính/method liên quan vào một nơi.
class ApiConfig(AppConfig):
    """
    Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
    Vai tro backend: Lop `ApiConfig` dang ky cau hinh khoi dong va hook `ready()` cua app trong file `api/apps.py`.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; no tac dong gian tiep bang cach bao dam signal, runtime override hoac side effect nen da san sang truoc khi API phuc vu man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Nam trong pham vi module hien tai.
    Tac dung: Kich hoat dung wiring cua app khi Django khoi dong de cac man nav khong gap trang thai thieu hook nen.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    verbose_name = 'REST API'

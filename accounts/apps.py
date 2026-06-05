"""
Thuoc chuc nang nao: Khoi dong app tai khoan, ho so nguoi dung va nen phan quyen dung chung.
Vai tro backend: File nay dang ky cau hinh app `accounts` de Django biet thoi diem nap signal va cac side effect can thiet cho user profile, ma nhan vien va credential ky so noi bo.
Vai tro cua no trong frontend: Frontend thay doi gian tiep qua viec API dang nhap, ho so va cac badge quyen chi hoat dong dung khi app `accounts` da nap day du signal ngay tu luc backend start.
Moi lien he voi nhung ham / source khac: Ket noi truc tiep voi `accounts.signals`, `accounts.models`, `accounts.permissions`, `api/serializers/auth.py` va luong tao credential trong `signing.internal_pki`.
Tac dung: Bao dam app tai khoan khong chi co model ma con kich hoat dung cac hook can chay ngay khi Django khoi dong.
"""

from django.apps import AppConfig

class AccountsConfig(AppConfig):
    """
    Thuoc chuc nang nao: Cau hinh khoi dong cho app tai khoan va ho so nguoi dung.
    Vai tro backend: Lop nay khai bao metadata cua app `accounts` va cung cap diem moc `ready()` de nap signal phat sinh profile/credential cho user.
    Vai tro cua no trong frontend: Frontend khong tuong tac truc tiep, nhung cac man login, profile va phan quyen nhan dung hanh vi dung nhanho backend khoi tao app nay chinh xac.
    Moi lien he voi nhung ham / source khac: Duoc Django nap tu `INSTALLED_APPS`; `ready()` ben trong tiep tuc import `accounts.signals`, noi voi `UserProfile` va `signing.internal_pki`.
    Tac dung: Gom phan metadata va wiring khoi dong cua app vao mot diem ro rang.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    

    def ready(self):
        """
        Thuoc chuc nang nao: Khoi dong signal cua app tai khoan.
        Vai tro backend: Ham nay import module `accounts.signals` tai dung thoi diem Django da nap xong app registry, de receiver tao/sync profile duoc dang ky.
        Vai tro cua no trong frontend: Frontend huong loi gian tiep vi user moi tao ra qua admin, social login hoac register se co profile va credential ky so nen ngay lap tuc, khong can mot buoc dong bo rieng.
        Moi lien he voi nhung ham / source khac: Goi module `accounts.signals`; cac receiver trong do tiep tuc lam viec voi `UserProfile` va `signing.internal_pki.ensure_user_signing_credential`.
        Tac dung: Dam bao signal cua app tai khoan thuc su duoc moc vao vong doi save cua model `User`.
        """
        import accounts.signals

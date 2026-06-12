"""
cấu hình một app Django cho quản lý tài khoản và hồ sơ người dùng, bao gồm metadata và logic khởi động để đảm bảo rằng các tín hiệu liên quan đến việc tạo hồ sơ người dùng và chứng chỉ ký số được đăng ký đúng cách khi ứng dụng được tải.
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

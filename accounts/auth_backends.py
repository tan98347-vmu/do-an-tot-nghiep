"""
Thuoc chuc nang nao: Xac thuc dang nhap da kenh cho tai khoan noi bo.
Vai tro backend: File nay mo rong backend xac thuc mac dinh cua Django de mot tai khoan co the dang nhap bang username, email hoac ma nhan vien luu trong `UserProfile`.
Vai tro cua no trong frontend: Form dang nhap tren frontend co the nhan mot truong dinh danh duy nhat thay vi ep nguoi dung biet chinh xac backend dang tim theo cot nao.
Moi lien he voi nhung ham / source khac: Duoc dua vao `AUTHENTICATION_BACKENDS` trong `my_tennis_club.settings`; doc `User` qua `get_user_model()` va join sang `profile__ma_nhan_vien`.
Tac dung: Tang kha nang dang nhap cho nhan su noi bo ma khong can nhan ban view hay serializer dang nhap.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

class EmployeeCodeOrUsernameBackend(ModelBackend):
    """
    Thuoc chuc nang nao: Backend xac thuc cho login bang nhieu loai dinh danh.
    Vai tro backend: Lop nay ke thua `ModelBackend` va dong goi toan bo quy trinh tim user theo username, email hoac ma nhan vien truoc khi kiem tra mat khau.
    Vai tro cua no trong frontend: Frontend dang nhap khong can biet nguoi dung nhap username hay ma nhan vien; backend nay se tu suy ra cach tim tai khoan.
    Moi lien he voi nhung ham / source khac: Duoc Django auth goi thong qua `authenticate`; phoi hop voi `_authenticate_user`, `UserProfile` va `user_can_authenticate` tu lop cha.
    Tac dung: Dat logic dang nhap linh hoat vao dung lop xac thuc thay vi trai sang view.
    """

    

    def _authenticate_user(self, user, password):
        """
        Thuoc chuc nang nao: Kiem tra mat khau va trang thai cho mot user da tim thay.
        Vai tro backend: Helper nay chi xu ly phan xac minh cuoi cung: neu co user, mat khau dung va user van duoc phep dang nhap thi tra ve doi tuong user, nguoc lai tra `None`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep, nhung ket qua cua no quyet dinh form dang nhap nhan token thanh cong hay bi tu choi.
        Moi lien he voi nhung ham / source khac: Duoc `authenticate` goi lai nhieu lan sau moi chien luoc tim user; dung `check_password` cua model user va `user_can_authenticate` tu `ModelBackend`.
        Tac dung: Tach rieng buoc "xac nhan user da hop le" khoi buoc "tim user theo dinh danh" de luong dang nhap de doc va de mo rong.
        """
        if user is None:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Thuoc chuc nang nao: Dang nhap bang username, email hoac ma nhan vien.
        Vai tro backend: Ham nay nhan gia tri dang nhap, lan luot thu tim user theo truong username mac dinh, email va `profile__ma_nhan_vien`, sau moi lan tim deu dung `_authenticate_user` de kiem tra mat khau.
        Vai tro cua no trong frontend: Day la diem backend ma form login, JWT obtain flow hoac cac API dang nhap duoc huong loi; nguoi dung co trai nghiem dang nhap thong nhat du chon loai dinh danh nao.
        Moi lien he voi nhung ham / source khac: Duoc Django auth framework goi; doc `USERNAME_FIELD`, `EMAIL_FIELD`, join sang `profile`; phoi hop voi `_authenticate_user` de tranh lap logic kiem tra password.
        Tac dung: Hop nhat nhieu cach tim tai khoan vao mot backend xac thuc duy nhat.
        """
        login_value = str(username or kwargs.get("email") or kwargs.get("identifier") or "").strip()
        if not login_value or not password:
            return None

        UserModel = get_user_model()
        username_field = getattr(UserModel, "USERNAME_FIELD", "username")

        user = UserModel._default_manager.filter(**{username_field: login_value}).first()
        authed = self._authenticate_user(user, password)
        if authed is not None:
            return authed

        email_field = getattr(UserModel, "EMAIL_FIELD", None)
        if email_field:
            email_matches = UserModel._default_manager.filter(**{f"{email_field}__iexact": login_value})
            if email_matches.count() == 1:
                authed = self._authenticate_user(email_matches.first(), password)
                if authed is not None:
                    return authed

        employee_matches = UserModel._default_manager.filter(
            profile__ma_nhan_vien__iexact=login_value,
        ).distinct()
        if employee_matches.count() != 1:
            return None
        return self._authenticate_user(employee_matches.first(), password)

"""
auth_backends.py chịu trách nhiệm xác thực tài khoản bằng nhiều loại định danh thay vì chỉ bằng username mặc định của Django.

  File: accounts/auth_backends.py:1.

  ## Vai Trò

  Backend này cho phép nhập một giá trị đăng nhập có thể là:

  Username kỹ thuật
  Email
  Mã nhân viên

  Sau đó kiểm tra mật khẩu và trạng thái tài khoản.

  Thông tin đăng nhập
  → tìm User
  → kiểm tra password
  → kiểm tra User có active không
  → trả User hoặc None
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
# class EmployeeCodeOrUsernameBackend kế thừa từ ModelBackend của Django, cho phép xác thực người dùng bằng nhiều loại định danh khác nhau như username, email hoặc mã nhân viên. Nó định nghĩa hai phương thức chính: authenticate để xử lý quá trình xác thực và _authenticate_user để kiểm tra mật khẩu và trạng thái của người dùng đã tìm thấy. Phương thức authenticate sẽ lần lượt thử tìm người dùng dựa trên các trường định danh khác nhau và sử dụng _authenticate_user để xác minh thông tin đăng nhập, trả về đối tượng người dùng nếu thành công hoặc None nếu thất bại.
class EmployeeCodeOrUsernameBackend(ModelBackend):


    
# def _authenticate_user để kiểm tra mật khẩu và trạng thái của người dùng đã tìm thấy. Nếu người dùng không tồn tại, nó sẽ trả về None. Nếu người dùng tồn tại và mật khẩu đúng, đồng thời người dùng có quyền đăng nhập (active), nó sẽ trả về đối tượng người dùng đó. Ngược lại, nếu mật khẩu sai hoặc người dùng không có quyền đăng nhập, nó sẽ trả về None.
    def _authenticate_user(self, user, password):
       
        if user is None:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    
# def authenticate để xử lý quá trình xác thực người dùng bằng cách nhận vào một giá trị đăng nhập (có thể là username, email hoặc mã nhân viên) và mật khẩu. Nó sẽ lần lượt thử tìm người dùng dựa trên các trường định danh khác nhau (username, email, mã nhân viên) và sử dụng phương thức _authenticate_user để kiểm tra mật khẩu và trạng thái của người dùng đã tìm thấy. Nếu tìm thấy một người dùng hợp lệ, nó sẽ trả về đối tượng người dùng đó; nếu không tìm thấy hoặc thông tin đăng nhập không hợp lệ, nó sẽ trả về None.
    def authenticate(self, request, username=None, password=None, **kwargs):
  
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

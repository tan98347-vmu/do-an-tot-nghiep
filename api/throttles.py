"""Chong brute-force / credential stuffing cho endpoint dang nhap.

Mac dinh DRF khong bat throttling (xem REST_FRAMEWORK trong settings). File nay
cung cap 2 lop throttle danh rieng cho `login_view`:

- `LoginIpRateThrottle`: gioi han so lan thu dang nhap theo dia chi IP (chong 1 IP
  do mat khau hang loat tren nhieu tai khoan = credential stuffing).
- `LoginIdentifierRateThrottle`: gioi han theo dinh danh dang nhap duoc gui len
  (chong brute-force mat khau cua DUNG 1 tai khoan tu nhieu IP).

Ca hai dung cache mac dinh cua Django. Voi trien khai nhieu worker/process nen
cau hinh CACHES dung Redis de dem chia se giua cac process (xem ghi chu trong
settings). Rate cau hinh qua DEFAULT_THROTTLE_RATES['login_ip'] / ['login_id'].
"""
from rest_framework.throttling import SimpleRateThrottle


# class LoginIpRateThrottle là lớp giới hạn tần suất gọi (rate limit).
# vd: gom các thuộc tính/method liên quan vào một nơi.
class LoginIpRateThrottle(SimpleRateThrottle):
    scope = 'login_ip'

    # def get_cache_key để lấy cache key.
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }


# class LoginIdentifierRateThrottle là lớp giới hạn tần suất gọi (rate limit).
# vd: gom các thuộc tính/method liên quan vào một nơi.
class LoginIdentifierRateThrottle(SimpleRateThrottle):
    scope = 'login_id'

    # def get_cache_key để lấy cache key.
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_cache_key(self, request, view):
        identifier = (
            request.data.get('identifier')
            or request.data.get('username')
            or request.data.get('email')
            or ''
        )
        identifier = str(identifier).strip().lower()
        if not identifier:
            # Khong co dinh danh -> khong throttle theo lop nay (de lop IP lo).
            return None
        # Ghep them IP-prefix de tranh dung chung key toan cuc khi nhieu cong ty
        # vo tinh trung local_username; van du de chan brute-force 1 tai khoan.
        return self.cache_format % {
            'scope': self.scope,
            'ident': identifier,
        }

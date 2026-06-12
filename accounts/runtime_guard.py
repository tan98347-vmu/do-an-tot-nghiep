'''
accounts/runtime_guard.py là lớp bảo vệ chống truy cập chéo dữ liệu và file giữa các công ty trong lúc hệ thống đang chạy.

  File: accounts/runtime_guard.py:1

  ## Vì Sao Cần File Này?

  Hệ thống là multi-company:

  Company A → documents/files/cache riêng
  Company B → documents/files/cache riêng

  Chỉ lọc queryset chưa đủ. Một lỗi lập trình vẫn có thể truyền:

  - Document công ty A.
  - File thuộc công ty B.
  - Preview cache của công ty B.

  vào cùng một quy trình.

  CompanyRuntimeGuard kiểm tra lại tại thời điểm xử lý:

  User, object, file và preview có cùng thuộc một công ty không?

  Nếu sai, nó ném:

  PermissionDenied

  thường được DRF chuyển thành HTTP 403 Forbidden.
'''

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from rest_framework.exceptions import PermissionDenied

from .storage_paths import company_storage_slug
from .tenancy import get_target_company, get_user_company, is_platform_admin, targets_share_company

#class CompanyRuntimeGuard để cung cấp các phương thức tĩnh và lớp để kiểm tra quyền truy cập và đảm bảo rằng các tài nguyên như media, cache và các đối tượng liên quan đến công ty được truy cập một cách an toàn trong môi trường đa công ty. Lớp này bao gồm các phương thức để tạo tiền tố cho media và cache, chuẩn hóa tên lưu trữ, và xác thực rằng người dùng hoặc tài nguyên đang được truy cập thuộc về cùng một công ty, nếu không sẽ ném ra lỗi PermissionDenied để ngăn chặn truy cập trái phép giữa các công ty.
class CompanyRuntimeGuard:
    @staticmethod
    def company_media_prefix(company) -> str:
        return f'companies/{company_storage_slug(company)}/'
#def preview_cache_prefix để tạo tiền tố cho đường dẫn cache trước nhìn (preview cache) dựa trên công ty và namespace. Tiền tố này được sử dụng để xác định vị trí lưu trữ của các file cache trước nhìn liên quan đến một công ty cụ thể trong hệ thống, giúp đảm bảo rằng các file cache được tổ chức và truy cập một cách an toàn theo công ty.
#vd : preview_cache_prefix(company=CompanyA, namespace='documents') có thể trả về 'preview_cache/documents/cong-ty-a/' để chỉ ra rằng các file cache trước nhìn liên quan đến công ty A và namespace 'documents' sẽ được lưu trữ dưới đường dẫn này trong hệ thống lưu trữ.
    @staticmethod
    def preview_cache_prefix(*, company, namespace: str) -> str:
        return f'preview_cache/{namespace}/{company_storage_slug(company)}/'
# def _normalize_storage_name để chuẩn hóa tên lưu trữ bằng cách thay thế các ký tự gạch chéo ngược (\) bằng gạch chéo (/) và loại bỏ các ký tự gạch chéo ở đầu chuỗi. Điều này giúp đảm bảo rằng tên lưu trữ được định dạng một cách nhất quán và tuân thủ định dạng đường dẫn chuẩn, đặc biệt là trong môi trường đa công ty nơi các tài nguyên được tổ chức theo cấu trúc thư mục liên quan đến công ty.
# vd: nếu đầu vào là '\companies\cong-ty-a\file.txt', kết quả trả về sẽ là 'companies/cong-ty-a/file.txt' sau khi chuẩn hóa, giúp đảm bảo rằng tên lưu trữ tuân thủ định dạng đường dẫn chuẩn và có thể được xử lý một cách nhất quán trong hệ thống.
    @staticmethod
    def _normalize_storage_name(name) -> str:
        return str(name or '').replace('\\', '/').lstrip('/')
#def assert_same_company để kiểm tra rằng tất cả các mục tiêu (targets) được cung cấp đều thuộc về cùng một công ty. Nó lọc ra các mục tiêu không phải là None, sau đó sử dụng hàm targets_share_company để xác định xem tất cả các mục tiêu có cùng công ty hay không. Nếu không, nó sẽ ném ra lỗi PermissionDenied với thông điệp chi tiết được cung cấp. Kết quả của hàm này là nếu tất cả các mục tiêu thuộc về cùng một công ty, nó sẽ hoàn thành mà không có lỗi; nếu có bất kỳ mục tiêu nào không thuộc về cùng một công ty, nó sẽ ném ra lỗi PermissionDenied.
# vd: nếu có ba mục tiêu A, B và C, trong đó A và B thuộc về công ty X, nhưng C thuộc về công ty Y, thì khi gọi assert_same_company(A, B, C) sẽ ném ra lỗi PermissionDenied vì không phải tất cả các mục tiêu đều thuộc về cùng một công ty.
    @classmethod
    def assert_same_company(cls, *targets, detail='Tai nguyen runtime dang tro sang cong ty khac.'):
        scoped_targets = [target for target in targets if target is not None]
        if scoped_targets and not targets_share_company(*scoped_targets):
            raise PermissionDenied(detail)
# def assert_user_target_access để kiểm tra rằng một người dùng có quyền truy cập vào một mục tiêu cụ thể dựa trên công ty của người dùng và mục tiêu. Nó lấy công ty của mục tiêu và công ty của người dùng, sau đó so sánh chúng. Nếu người dùng không thuộc về bất kỳ công ty nào nhưng được phép là quản trị viên nền tảng, nó sẽ cho phép truy cập. Nếu người dùng thuộc về một công ty khác với mục tiêu, nó sẽ ném ra lỗi PermissionDenied với thông điệp chi tiết được cung cấp. Kết quả của hàm này là nếu người dùng có quyền truy cập vào mục tiêu, nó sẽ trả về công ty của mục tiêu; nếu không, nó sẽ ném ra lỗi PermissionDenied.
# vd: nếu người dùng thuộc về công ty A và mục tiêu thuộc về công ty B, thì khi gọi assert_user_target_access(user, target) sẽ ném ra lỗi PermissionDenied vì người dùng không có quyền truy cập vào mục tiêu do thuộc về công ty khác. Ngược lại, nếu người dùng thuộc về công ty A và mục tiêu cũng thuộc về công ty A, thì hàm sẽ trả về công ty của mục tiêu mà không có lỗi nào xảy ra, cho phép người dùng truy cập vào mục tiêu đó.
    @classmethod
    def assert_user_target_access(
        cls,
        user,
        target,
        *,
        allow_platform_admin: bool = False,
        detail='Ban khong duoc truy cap tai nguyen runtime cua cong ty khac.',
    ):
        target_company = get_target_company(target)
        if target_company is None or user is None:
            return target_company

        user_company = get_user_company(user)
        if user_company is None:
            if allow_platform_admin and is_platform_admin(user):
                return target_company
            raise PermissionDenied(detail)

        if user_company.pk != target_company.pk:
            raise PermissionDenied(detail)
        return target_company
# def assert_storage_name để kiểm tra rằng một tên lưu trữ (storage name) thuộc về cùng một công ty với mục tiêu (target) hoặc công ty được chỉ định (company). Nó chuẩn hóa tên lưu trữ bằng cách sử dụng phương thức _normalize_storage_name, sau đó kiểm tra xem tên lưu trữ có bắt đầu với tiền tố liên quan đến công ty hay không. Nếu tên lưu trữ không hợp lệ hoặc không thuộc về cùng một công ty, nó sẽ ném ra lỗi PermissionDenied với thông điệp chi tiết được cung cấp. Kết quả trả về là tên lưu trữ đã được xác thực nếu hợp lệ, hoặc một chuỗi rỗng nếu tên lưu trữ không có giá trị.
    @classmethod
    def assert_storage_name(
        cls,
        name,
        *,
        company=None,
        target=None,
        detail='File dang tro sang storage cua cong ty khac.',
    ) -> str:
        normalized = cls._normalize_storage_name(name)
        if not normalized:
            return normalized
        if not normalized.startswith('companies/'):
            return normalized

        target_company = company or get_target_company(target)
        if target_company is None:
            return normalized

        if not normalized.startswith(cls.company_media_prefix(target_company)):
            raise PermissionDenied(detail)
        return normalized
# def assert_file_field để kiểm tra rằng một trường file (file_field) thuộc về cùng một công ty với mục tiêu (target) hoặc công ty được chỉ định (company). Nó sử dụng phương thức assert_storage_name để xác thực rằng tên lưu trữ của file_field tuân thủ định dạng và tiền tố liên quan đến công ty. Nếu tên lưu trữ không hợp lệ hoặc không thuộc về cùng một công ty, nó sẽ ném ra lỗi PermissionDenied với thông điệp chi tiết được cung cấp. Kết quả trả về là tên lưu trữ đã được xác thực nếu hợp lệ, hoặc một chuỗi rỗng nếu file_field không có giá trị.
    @classmethod
    def assert_file_field(
        cls,
        file_field,
        *,
        company=None,
        target=None,
        detail='File dang tro sang storage cua cong ty khac.',
    ) -> str:
        if not file_field:
            return ''
        return cls.assert_storage_name(
            getattr(file_field, 'name', ''),
            company=company,
            target=target,
            detail=detail,
        )
# def assert_preview_path để kiểm tra rằng một đường dẫn trước nhìn (preview_path) thuộc về cùng một công ty với mục tiêu (target) hoặc công ty được chỉ định (company). Nó sử dụng phương thức assert_storage_name để xác thực rằng tên lưu trữ của preview_path tuân thủ định dạng và tiền tố liên quan đến công ty. Nếu tên lưu trữ không hợp lệ hoặc không thuộc về cùng một công ty, nó sẽ ném ra lỗi PermissionDenied với thông điệp chi tiết được cung cấp. Kết quả trả về là đường dẫn trước nhìn đã được xác thực nếu hợp lệ, hoặc một chuỗi rỗng nếu preview_path không có giá trị.
    @classmethod
    def assert_preview_path(
        cls,
        preview_path,
        *,
        company=None,
        target=None,
        namespace='documents',
        detail='Ban xem truoc dang tro sang cache cua cong ty khac.',
    ):
        if preview_path is None:
            return preview_path

        target_company = company or get_target_company(target)
        if target_company is None:
            return preview_path

        try:
            media_root = Path(settings.MEDIA_ROOT).resolve(strict=False)
            resolved_path = Path(preview_path).resolve(strict=False)
        except (TypeError, ValueError, OSError):
            return preview_path

        try:
            relative_path = resolved_path.relative_to(media_root)
        except ValueError:
            return preview_path

        normalized = relative_path.as_posix().lstrip('/')
        if not normalized.startswith('preview_cache/'):
            return preview_path

        expected_prefix = cls.preview_cache_prefix(company=target_company, namespace=namespace)
        if not normalized.startswith(expected_prefix):
            raise PermissionDenied(detail)
        return preview_path

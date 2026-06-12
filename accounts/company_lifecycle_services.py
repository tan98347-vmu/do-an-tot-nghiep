'''

• company_lifecycle_services.py quản lý vòng đời của một công ty sau khi công ty đã được tạo.

  Nếu company_services.py phụ trách:

  Tạo công ty → tạo admin → tạo nhân viên → import Excel

  thì company_lifecycle_services.py phụ trách:

  Công ty đang hoạt động
  → xóa mềm
  → đưa vào thùng rác
  → phục hồi
  → hoặc xóa vĩnh viễn
'''
from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q

from ai_engine.rag_index import _delete_collection_embeddings
from .models import Company, CompanyRole, CompanyStatus, CompanyUserMembership
from .storage_paths import company_storage_slug
from .tenancy import is_platform_admin


LOGGER = logging.getLogger(__name__)

# class CompanyHardDeleteError để định nghĩa một lỗi tùy chỉnh được sử dụng khi có lỗi liên quan đến việc xóa cứng một công ty. Lỗi này kế thừa từ ValueError và có thể được sử dụng để ném ra lỗi cụ thể khi có vấn đề xảy ra trong quá trình xóa cứng công ty, giúp người dùng hoặc nhà phát triển hiểu rõ hơn về nguyên nhân của lỗi.
class CompanyHardDeleteError(ValueError):
    pass

# dataclass CompanyTrashSummary để định nghĩa một cấu trúc dữ liệu chứa thông tin tóm tắt về một công ty đã bị xóa mềm (soft deleted). Nó bao gồm các trường như company (đối tượng Company), bootstrap_admin_username (tên người dùng của quản trị viên ban đầu), và bootstrap_admin_email (email của quản trị viên ban đầu). Cấu trúc này có thể được sử dụng để hiển thị thông tin về các công ty đã bị xóa mềm trong thùng rác hoặc để thực hiện các thao tác liên quan đến việc khôi phục hoặc xóa cứng công ty.
@dataclass(frozen=True)
class CompanyTrashSummary:
    company: Company
    bootstrap_admin_username: str
    bootstrap_admin_email: str

# class CompanyHardDeleteResult để định nghĩa một cấu trúc dữ liệu chứa thông tin về kết quả của quá trình xóa cứng một công ty. Nó bao gồm các trường như company_id (ID của công ty đã bị xóa), company_code (mã của công ty đã bị xóa), company_name (tên của công ty đã bị xóa), deleted_user_count (số lượng người dùng đã bị xóa), và deleted_membership_count (số lượng thành viên đã bị xóa). Cấu trúc này có thể được sử dụng để cung cấp thông tin chi tiết về kết quả của quá trình xóa cứng công ty, giúp người dùng hoặc nhà phát triển hiểu rõ hơn về những gì đã xảy ra trong quá trình này.
@dataclass(frozen=True)
class CompanyHardDeleteResult:
    company_id: int
    company_code: str
    company_name: str
    deleted_user_count: int
    deleted_membership_count: int

# def get_company_bootstrap_admin_membership để lấy thông tin về thành viên quản trị viên ban đầu của một công ty. Nó truy vấn các thành viên của công ty có vai trò là COMPANY_ADMIN và đang hoạt động, sau đó ưu tiên tìm kiếm thành viên có tên người dùng địa phương là 'admin'. Nếu tìm thấy, nó sẽ trả về thành viên đó. Nếu không tìm thấy, nó sẽ trả về thành viên đầu tiên trong danh sách các quản trị viên đang hoạt động. Kết quả trả về là một đối tượng CompanyUserMembership hoặc None nếu không tìm thấy quản trị viên nào phù hợp.
def get_company_bootstrap_admin_membership(company: Company) -> CompanyUserMembership | None:
    memberships = company.memberships.select_related('user').filter(
        role=CompanyRole.COMPANY_ADMIN,
        is_active=True,
    )
    membership = memberships.filter(local_username__iexact='admin').order_by('pk').first()
    if membership is not None:
        return membership
    return memberships.order_by('pk').first()

# def list_deleted_companies để liệt kê các công ty đã bị xóa mềm (soft deleted) dựa trên một truy vấn tìm kiếm tùy chọn. Nó truy vấn các công ty có trạng thái là DELETED và sắp xếp theo tên và mã. Nếu có truy vấn tìm kiếm, nó sẽ lọc các công ty dựa trên tên hoặc mã chứa chuỗi truy vấn đó. Sau đó, nó tạo một danh sách các đối tượng CompanyTrashSummary chứa thông tin về mỗi công ty đã bị xóa mềm, bao gồm thông tin về quản trị viên ban đầu của công ty đó. Kết quả trả về là một danh sách các CompanyTrashSummary phù hợp với truy vấn tìm kiếm nếu có.
def list_deleted_companies(*, query: str = '') -> list[CompanyTrashSummary]:
    companies = Company.objects.filter(status=CompanyStatus.DELETED).order_by('name', 'code')
    if query:
        companies = companies.filter(Q(name__icontains=query) | Q(code__icontains=query))
    items: list[CompanyTrashSummary] = []
    for company in companies:
        bootstrap = get_company_bootstrap_admin_membership(company)
        items.append(
            CompanyTrashSummary(
                company=company,
                bootstrap_admin_username=bootstrap.local_username if bootstrap else '',
                bootstrap_admin_email=bootstrap.user.email if bootstrap else '',
            )
        )
    return items

# def soft_delete_company để thực hiện xóa mềm một công ty bằng cách cập nhật trạng thái của công ty thành DELETED. Nếu công ty đã ở trạng thái DELETED, nó sẽ trả về công ty đó mà không thực hiện thay đổi nào. Nếu không, nó sẽ cập nhật trạng thái của công ty, ghi nhận người thực hiện hành động (actor) nếu có, và lưu lại các thay đổi vào cơ sở dữ liệu. Kết quả trả về là đối tượng Company đã được cập nhật với trạng thái mới.
def soft_delete_company(company: Company, *, actor: User | None = None) -> Company:
    if company.status == CompanyStatus.DELETED:
        return company
    company.status = CompanyStatus.DELETED
    company.updated_by = actor
    company.save(update_fields=['status', 'updated_by', 'updated_at'])
    return company

# restore_company_from_trash để khôi phục một công ty từ trạng thái DELETED trở lại trạng thái hoạt động (hoặc trạng thái mục tiêu được chỉ định). Nó kiểm tra nếu công ty đang ở trạng thái DELETED, nếu không sẽ ném ra lỗi. Nếu có, nó sẽ cập nhật trạng thái của công ty thành trạng thái mục tiêu (mặc định là ACTIVE), ghi nhận người thực hiện hành động (actor) nếu có, và lưu lại các thay đổi vào cơ sở dữ liệu. Kết quả trả về là đối tượng Company đã được cập nhật với trạng thái mới.
def restore_company_from_trash(
    company: Company,
    *,
    actor: User | None = None,
    target_status: str = CompanyStatus.ACTIVE,
) -> Company:
    if company.status != CompanyStatus.DELETED:
        raise CompanyHardDeleteError('Chi cong ty trong thung rac moi co the khoi phuc.')
    company.status = target_status
    company.updated_by = actor
    company.save(update_fields=['status', 'updated_by', 'updated_at'])
    return company

# def _company_media_cleanup_paths để tạo một danh sách các đường dẫn đến các thư mục liên quan đến công ty trong hệ thống lưu trữ. Nó sử dụng slug của công ty để xây dựng các đường dẫn đến thư mục chứa dữ liệu của công ty, thư mục cache xem trước cho tài liệu và mẫu. Kết quả trả về là một danh sách các đối tượng Path đại diện cho các đường dẫn này, có thể được sử dụng để thực hiện các thao tác như xóa hoặc dọn dẹp dữ liệu liên quan đến công ty.

def _company_media_cleanup_paths(company: Company) -> list[Path]:
    slug = company_storage_slug(company)
    media_root = Path(settings.MEDIA_ROOT)
    return [
        media_root / 'companies' / slug,
        media_root / 'preview_cache' / 'documents' / slug,
        media_root / 'preview_cache' / 'templates' / slug,
    ]

# def _purge_path để xóa một đường dẫn cụ thể khỏi hệ thống tệp. Nếu đường dẫn không tồn tại, nó sẽ trả về mà không thực hiện gì. Nếu đường dẫn là một tệp, nó sẽ xóa tệp đó. Nếu đường dẫn là một thư mục, nó sẽ xóa toàn bộ thư mục và nội dung bên trong nó. Kết quả của hàm này là đường dẫn đã được xóa khỏi hệ thống tệp nếu nó tồn tại.
def _purge_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_file():
        path.unlink()
        return
    shutil.rmtree(path)

# def _purge_company_media để xóa tất cả các đường dẫn liên quan đến công ty khỏi hệ thống tệp. Nó nhận vào một danh sách các đường dẫn và cố gắng xóa từng đường dẫn bằng cách sử dụng hàm _purge_path. Nếu có lỗi xảy ra trong quá trình xóa, nó sẽ ghi lại một cảnh báo vào log với thông tin về đường dẫn và lỗi đã xảy ra. Kết quả của hàm này là tất cả các đường dẫn liên quan đến công ty đã được xóa khỏi hệ thống tệp nếu chúng tồn tại, và các lỗi nếu có sẽ được ghi lại trong log.
def _purge_company_media(paths: list[Path]) -> None:
    for path in paths:
        try:
            _purge_path(path)
        except OSError as exc:
            LOGGER.warning('company hard delete media cleanup skipped | path=%s | error=%s', path, exc)

# def _company_rag_collection_names để tạo một danh sách các tên bộ sưu tập RAG (Retrieval-Augmented Generation) liên quan đến một công ty cụ thể. Nó nhận vào ID của công ty và danh sách ID của người dùng, sau đó xây dựng các tên bộ sưu tập dựa trên định dạng đã định nghĩa. Kết quả trả về là một danh sách các tên bộ sưu tập RAG có liên quan đến công ty và người dùng, có thể được sử dụng để thực hiện các thao tác như xóa hoặc dọn dẹp dữ liệu RAG liên quan đến công ty.
def _company_rag_collection_names(*, company_id: int, user_ids: list[int]) -> list[str]:
    names = [
        f'company_{company_id}_template_rag_kb',
        f'company_{company_id}_document_rag_kb',
        f'company_{company_id}_shared_kb',
    ]
    names.extend(f'company_{company_id}_user_{user_id}_kb' for user_id in user_ids)
    return names

# def _purge_company_rag_indexes để xóa tất cả các bộ sưu tập RAG liên quan đến một công ty cụ thể. Nó nhận vào ID của công ty và danh sách ID của người dùng, sau đó tạo danh sách các tên bộ sưu tập RAG liên quan đến công ty và người dùng bằng cách sử dụng hàm _company_rag_collection_names. Sau đó, nó cố gắng xóa từng bộ sưu tập RAG bằng cách sử dụng hàm _delete_collection_embeddings. Nếu có lỗi xảy ra trong quá trình xóa, nó sẽ ghi lại một cảnh báo vào log với thông tin về công ty, bộ sưu tập và lỗi đã xảy ra. Kết quả của hàm này là tất cả các bộ sưu tập RAG liên quan đến công ty đã được xóa nếu chúng tồn tại, và các lỗi nếu có sẽ được ghi lại trong log.
def _purge_company_rag_indexes(*, company_id: int, user_ids: list[int]) -> None:
    for collection_name in _company_rag_collection_names(company_id=company_id, user_ids=user_ids):
        try:
            _delete_collection_embeddings(collection_name)
        except Exception as exc:  # pragma: no cover - defensive cleanup only
            LOGGER.warning(
                'company hard delete rag cleanup skipped | company_id=%s | collection=%s | error=%s',
                company_id,
                collection_name,
                exc,
            )

# def hard_delete_company để thực hiện xóa cứng một công ty khỏi hệ thống. Nó kiểm tra các điều kiện cần thiết như trạng thái của công ty, quyền của người thực hiện hành động và mật khẩu của quản trị viên nền tảng trước khi tiến hành xóa. Nếu tất cả các điều kiện được đáp ứng, nó sẽ xóa tất cả người dùng liên quan đến công ty, xóa công ty khỏi cơ sở dữ liệu, và sau đó dọn dẹp các tài nguyên liên quan đến công ty như dữ liệu media và bộ sưu tập RAG. Kết quả trả về là một đối tượng CompanyHardDeleteResult chứa thông tin chi tiết về quá trình xóa cứng công ty.
def hard_delete_company(
    company: Company,
    *,
    platform_admin_user: User,
    platform_admin_password: str,
    company_admin_password: str = '',
) -> CompanyHardDeleteResult:
    # Chi can xac thuc mat khau cua admin quan tri nen tang. Khong con yeu cau
    # mat khau cua admin cong ty (tham so company_admin_password giu lai cho
    # tuong thich nguoc nhung khong duoc su dung).
    if company.status != CompanyStatus.DELETED:
        raise CompanyHardDeleteError('Chi cong ty da xoa mem moi duoc xoa cung.')
    if not is_platform_admin(platform_admin_user):
        raise CompanyHardDeleteError('Chi platform admin moi duoc xoa cung cong ty.')
    if not platform_admin_user.check_password(platform_admin_password or ''):
        raise CompanyHardDeleteError('Mat khau admin quan tri nen tang khong dung.')

    user_ids = list(
        CompanyUserMembership.objects.filter(company=company).values_list('user_id', flat=True)
    )
    deleted_membership_count = len(user_ids)
    media_paths = _company_media_cleanup_paths(company)
    company_id = company.pk
    company_code = company.code
    company_name = company.name

    with transaction.atomic():
        User.objects.filter(pk__in=user_ids).delete()
        company.delete()
        transaction.on_commit(lambda: _purge_company_media(media_paths))
        transaction.on_commit(
            lambda: _purge_company_rag_indexes(company_id=company_id, user_ids=user_ids)
        )

    return CompanyHardDeleteResult(
        company_id=company_id,
        company_code=company_code,
        company_name=company_name,
        deleted_user_count=len(user_ids),
        deleted_membership_count=deleted_membership_count,
    )

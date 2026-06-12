'''
Tên đúng là tenancy.py. File này chịu trách nhiệm xác định người dùng thuộc công ty nào và cô lập nghiệp vụ theo công ty đó.

  File: accounts/tenancy.py:1

  ## Tenant Là Gì?

  Trong hệ thống này:

  Một Company = một tenant

  Mỗi tenant có user, tài liệu, template, cấu hình AI và file riêng.

  tenancy.py trả lời:

  User thuộc công ty nào?
  User có phải admin không?
  Hai tài nguyên có cùng công ty không?
  Đăng nhập vào công ty nào?
  Nên sử dụng cấu hình và ngữ cảnh AI nào?

'''

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.contrib.auth.models import User
from django.db.utils import DatabaseError, OperationalError, ProgrammingError

from .models import (
    Company,
    CompanyAIConfig,
    CompanyRole,
    CompanyStatus,
    CompanyUserMembership,
    DepartmentMembership,
    GlobalAIConfig,
)


@dataclass(frozen=True)
class CompanyLoginMatch:
    user: User
    membership: CompanyUserMembership

# def _legacy_platform_admin_fallback để kiểm tra rằng một người dùng có phải là quản trị viên nền tảng hay không bằng cách kiểm tra xem họ có phải là superuser hay không và không có thành viên công ty nào liên kết với họ. Nếu có lỗi xảy ra khi truy vấn cơ sở dữ liệu, nó sẽ trả về giá trị của user.is_superuser. Kết quả của hàm này là nếu người dùng là superuser và không có thành viên công ty nào liên kết với họ, nó sẽ trả về True, cho phép họ được coi là quản trị viên nền tảng; nếu người dùng không phải là superuser hoặc có thành viên công ty liên kết, nó sẽ trả về False, không coi họ là quản trị viên nền tảng.
def _legacy_platform_admin_fallback(user: User) -> bool:
    if not getattr(user, 'is_superuser', False):
        return False
    try:
        return not CompanyUserMembership.objects.filter(user=user).exists()
    except (ProgrammingError, OperationalError, DatabaseError):
        return bool(user.is_superuser)

# def is_platform_admin để kiểm tra rằng một người dùng có phải là quản trị viên nền tảng hay không bằng cách kiểm tra một thuộc tính đặc biệt trong hồ sơ người dùng của họ. Nếu người dùng không xác thực, nó sẽ trả về False. Nếu có lỗi xảy ra khi truy vấn cơ sở dữ liệu hoặc nếu hồ sơ người dùng không có thuộc tính marker, nó sẽ sử dụng hàm _legacy_platform_admin_fallback để xác định xem người dùng có phải là quản trị viên nền tảng hay không. Kết quả của hàm này là nếu người dùng có thuộc tính is_platform_admin_account trong hồ sơ của họ và giá trị đó là True, nó sẽ trả về True, cho phép họ được coi là quản trị viên nền tảng; nếu không, nó sẽ dựa vào kết quả của hàm _legacy_platform_admin_fallback để đưa ra quyết định cuối cùng.
def is_platform_admin(user: Optional[User]) -> bool:
    if not user or not user.is_authenticated:
        return False
    try:
        profile = getattr(user, 'profile', None)
    except (ProgrammingError, OperationalError, DatabaseError):
        return _legacy_platform_admin_fallback(user)
    if profile is None:
        return _legacy_platform_admin_fallback(user)
    marker = getattr(profile, 'is_platform_admin_account', None)
    if marker is None:
        return _legacy_platform_admin_fallback(user)
    return bool(marker)

# def get_user_membership để lấy thông tin thành viên công ty của một người dùng cụ thể. Nó kiểm tra xem người dùng có xác thực hay không, sau đó cố gắng truy xuất thành viên công ty liên kết với người dùng đó. Nếu thành viên công ty tồn tại và đang hoạt động, và công ty của thành viên đó cũng đang hoạt động, nó sẽ trả về đối tượng CompanyUserMembership; nếu không, nó sẽ trả về None. Kết quả của hàm này là nếu người dùng có một thành viên công ty hợp lệ và đang hoạt động, nó sẽ trả về thông tin đó; nếu không, nó sẽ trả về None, cho biết rằng người dùng không có thành viên công ty hợp lệ hoặc không có quyền truy cập vào bất kỳ công ty nào.
def get_user_membership(user: Optional[User]) -> Optional[CompanyUserMembership]:
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    membership = getattr(user, 'company_membership', None)
    if membership is None:
        return None
    if not membership.is_active:
        return None
    if membership.company.status != CompanyStatus.ACTIVE:
        return None
    return membership

# def get_user_company để lấy công ty mà một người dùng cụ thể thuộc về. Nó sử dụng hàm get_user_membership để lấy thông tin thành viên công ty của người dùng, sau đó trả về công ty liên kết với thành viên đó nếu tồn tại; nếu không, nó sẽ trả về None. Kết quả của hàm này là nếu người dùng có một thành viên công ty hợp lệ, nó sẽ trả về công ty mà người dùng đó thuộc về; nếu không, nó sẽ trả về None, cho biết rằng người dùng không thuộc về bất kỳ công ty nào hoặc không có quyền truy cập vào bất kỳ công ty nào.
def get_user_company(user: Optional[User]) -> Optional[Company]:
    membership = get_user_membership(user)
    return membership.company if membership else None

# def get_target_company để xác định công ty liên quan đến một mục tiêu cụ thể, có thể là một đối tượng thuộc về công ty hoặc có liên kết đến công ty thông qua các trường như company, document, source_document, thread, packet hoặc proposal. Nó sử dụng một cơ chế đệ quy để kiểm tra các trường liên quan và tránh vòng lặp vô hạn bằng cách theo dõi các mục tiêu đã thấy. Kết quả của hàm này là nếu nó tìm thấy một công ty hợp lệ liên quan đến mục tiêu, nó sẽ trả về đối tượng Company đó; nếu không tìm thấy hoặc nếu có vòng lặp trong cấu trúc liên kết, nó sẽ trả về None.
def get_target_company(target, _seen=None) -> Optional[Company]:
    if target is None:
        return None
    if _seen is None:
        _seen = set()
    target_key = (type(target), getattr(target, 'pk', None), id(target))
    if target_key in _seen:
        return None
    _seen.add(target_key)
    if isinstance(target, Company):
        return target
    if isinstance(target, User):
        return get_user_company(target)

    direct_company = getattr(target, 'company', None)
    if direct_company is not None:
        return direct_company

    for attr_name in ('document', 'source_document', 'thread', 'packet', 'proposal'):
        related = getattr(target, attr_name, None)
        if related is None:
            continue
        company = get_target_company(related, _seen=_seen)
        if company is not None:
            return company
    return None

# def targets_share_company để kiểm tra xem tất cả các mục tiêu được cung cấp có thuộc về cùng một công ty hay không. Nó lấy công ty của mỗi mục tiêu bằng cách sử dụng hàm get_target_company, sau đó so sánh chúng. Nếu tất cả các mục tiêu có cùng một công ty hoặc nếu tất cả đều không có công ty, nó sẽ trả về True; nếu có bất kỳ mục tiêu nào thuộc về một công ty khác, nó sẽ trả về False. Kết quả của hàm này là nếu tất cả các mục tiêu thuộc về cùng một công ty hoặc không có công ty nào, nó sẽ trả về True; nếu có bất kỳ mục tiêu nào thuộc về một công ty khác, nó sẽ trả về False, cho biết rằng các mục tiêu không chia sẻ cùng một công ty.
def targets_share_company(*targets) -> bool:
    company_ids = []
    saw_missing_company = False

    for target in targets:
        if target is None:
            continue
        company = get_target_company(target)
        if company is None:
            saw_missing_company = True
            continue
        company_ids.append(company.pk)

    if not company_ids:
        return True
    if saw_missing_company:
        return False
    return len(set(company_ids)) == 1

# def filter_queryset_by_current_company để lọc một queryset dựa trên công ty của người dùng hiện tại. Nó lấy công ty của người dùng bằng cách sử dụng hàm get_user_company, sau đó lọc queryset dựa trên trường công ty được chỉ định (mặc định là 'company') nếu công ty tồn tại. Nếu người dùng không thuộc về bất kỳ công ty nào, nó sẽ trả về queryset gốc mà không áp dụng bộ lọc nào. Kết quả của hàm này là nếu người dùng thuộc về một công ty, nó sẽ trả về một queryset đã được lọc để chỉ bao gồm các mục liên quan đến công ty đó; nếu người dùng không thuộc về bất kỳ công ty nào, nó sẽ trả về queryset gốc, cho phép truy cập vào tất cả các mục mà không có sự cô lập theo công ty.
def filter_queryset_by_current_company(queryset, user: Optional[User], *, company_field: str = 'company'):
    company = get_user_company(user)
    if company is None:
        return queryset
    return queryset.filter(**{company_field: company})

# def is_company_admin để kiểm tra rằng một người dùng có phải là quản trị viên của công ty hay không bằng cách kiểm tra vai trò của người dùng trong thành viên công ty của họ. Nó lấy thông tin thành viên công ty của người dùng bằng cách sử dụng hàm get_user_membership, sau đó kiểm tra xem vai trò của thành viên đó có phải là CompanyRole.COMPANY_ADMIN hay không. Kết quả của hàm này là nếu người dùng có một thành viên công ty hợp lệ và vai trò của họ là COMPANY_ADMIN, nó sẽ trả về True, cho phép họ được coi là quản trị viên của công ty; nếu không, nó sẽ trả về False, không coi họ là quản trị viên của công ty.
def is_company_admin(user: Optional[User]) -> bool:
    membership = get_user_membership(user)
    return bool(membership and membership.role == CompanyRole.COMPANY_ADMIN)

# def is_tenant_admin để kiểm tra rằng một người dùng có phải là quản trị viên của tenant (công ty) hay không bằng cách kiểm tra xem họ có phải là quản trị viên nền tảng hoặc quản trị viên công ty hay không. Nó sử dụng hàm is_platform_admin để kiểm tra nếu người dùng là quản trị viên nền tảng, và hàm is_company_admin để kiểm tra nếu người dùng là quản trị viên công ty. Kết quả của hàm này là nếu người dùng là quản trị viên nền tảng hoặc quản trị viên công ty, nó sẽ trả về True, cho phép họ được coi là quản trị viên của tenant; nếu không, nó sẽ trả về False, không coi họ là quản trị viên của tenant.
def is_tenant_admin(user: Optional[User]) -> bool:
    return is_platform_admin(user) or is_company_admin(user)

# def resolve_company để lấy đối tượng Company dựa trên company_id được cung cấp. Nó kiểm tra xem company_id có tồn tại hay không, sau đó cố gắng truy vấn cơ sở dữ liệu để tìm kiếm công ty với khóa chính tương ứng. Nếu tìm thấy, nó sẽ trả về đối tượng Company; nếu không tìm thấy hoặc nếu có lỗi xảy ra do company_id không hợp lệ, nó sẽ trả về None. Kết quả của hàm này là nếu company_id hợp lệ và có một công ty tương ứng trong cơ sở dữ liệu, nó sẽ trả về đối tượng Company đó; nếu company_id không hợp lệ hoặc không có công ty nào tương ứng, nó sẽ trả về None, cho biết rằng không thể xác định công ty dựa trên company_id đã cho.
def resolve_company(company_id) -> Optional[Company]:
    if not company_id:
        return None
    try:
        return Company.objects.filter(pk=company_id).first()
    except (TypeError, ValueError):
        return None

# def resolve_company_login để xác định người dùng và thành viên công ty dựa trên thông tin đăng nhập được cung cấp, bao gồm identifier (có thể là tên đăng nhập, email hoặc mã nhân viên), mật khẩu và công ty mà người dùng đang cố gắng đăng nhập. Nó tìm kiếm các thành viên công ty trong công ty đó có thông tin đăng nhập phù hợp với identifier, sau đó kiểm tra mật khẩu và trạng thái hoạt động của người dùng. Nếu tìm thấy một kết quả phù hợp duy nhất, nó sẽ trả về một đối tượng CompanyLoginMatch chứa người dùng và thành viên công ty; nếu không tìm thấy hoặc nếu có nhiều kết quả phù hợp, nó sẽ trả về None. Kết quả của hàm này là nếu thông tin đăng nhập hợp lệ và chỉ khớp với một người dùng duy nhất trong công ty, nó sẽ trả về thông tin đó; nếu không, nó sẽ trả về None, cho biết rằng thông tin đăng nhập không hợp lệ hoặc không thể xác định người dùng một cách duy nhất.
def resolve_company_login(identifier: str, password: str, company: Company) -> Optional[CompanyLoginMatch]:
    if not identifier or not password:
        return None
    memberships = CompanyUserMembership.objects.select_related('user', 'company').filter(
        company=company,
        is_active=True,
    )

    direct = memberships.filter(local_username__iexact=identifier).first()
    if direct and direct.user.check_password(password) and direct.user.is_active:
        return CompanyLoginMatch(user=direct.user, membership=direct)

    username_matches = memberships.filter(user__username__iexact=identifier)
    if username_matches.count() == 1:
        membership = username_matches.first()
        if membership and membership.user.check_password(password) and membership.user.is_active:
            return CompanyLoginMatch(user=membership.user, membership=membership)

    email_matches = memberships.filter(user__email__iexact=identifier)
    if email_matches.count() == 1:
        membership = email_matches.first()
        if membership and membership.user.check_password(password) and membership.user.is_active:
            return CompanyLoginMatch(user=membership.user, membership=membership)

    employee_matches = memberships.filter(user__profile__ma_nhan_vien__iexact=identifier).distinct()
    if employee_matches.count() == 1:
        membership = employee_matches.first()
        if membership and membership.user.check_password(password) and membership.user.is_active:
            return CompanyLoginMatch(user=membership.user, membership=membership)
    return None

# def resolve_ai_config để xác định cấu hình AI hiệu quả dựa trên người dùng và công ty. Nó lấy công ty từ tham số hoặc từ người dùng, sau đó trả về cấu hình AI của công ty nếu có; nếu không có công ty nào được xác định, nó sẽ trả về cấu hình AI toàn cầu. Kết quả của hàm này là nếu một công ty được xác định và có cấu hình AI riêng, nó sẽ trả về cấu hình đó; nếu không, nó sẽ trả về cấu hình AI toàn cầu, đảm bảo rằng luôn có một cấu hình AI hợp lệ được sử dụng trong hệ thống.
def resolve_ai_config(*, user: Optional[User] = None, company: Optional[Company] = None):
    company = company or get_user_company(user)
    if not company:
        return GlobalAIConfig.get_config()
    return CompanyAIConfig.seed_defaults(company)

# def resolve_chat_ai_model để xác định mô hình AI hiệu quả dành riêng cho trợ lý Chat AI dựa trên người dùng và công ty. Nó sử dụng hàm resolve_ai_config để lấy cấu hình AI, sau đó trả về trường chat_ai_model nếu có; nếu không có trường đó, nó sẽ trả về trường ai_model; nếu cả hai trường đều không có giá trị, nó sẽ trả về một giá trị mặc định 'kimi-k2.6:cloud'. Kết quả của hàm này là nếu cấu hình AI có một mô hình Chat AI cụ thể được định nghĩa, nó sẽ trả về mô hình đó; nếu không, nó sẽ trả về mô hình AI chung hoặc một giá trị mặc định, đảm bảo rằng luôn có một mô hình AI hợp lệ được sử dụng cho trợ lý Chat AI trong hệ thống.
def resolve_chat_ai_model(*, user: Optional[User] = None, company: Optional[Company] = None) -> str:
    """Model rieng cho Tro ly Chat AI. Fall back ve ai_model neu de trong."""
    cfg = resolve_ai_config(user=user, company=company)
    return (getattr(cfg, 'chat_ai_model', '') or getattr(cfg, 'ai_model', '') or 'kimi-k2.6:cloud').strip()

# def build_effective_company_context để xây dựng ngữ cảnh công ty hiệu quả dựa trên người dùng và công ty. Nó sử dụng hàm resolve_ai_config để lấy cấu hình AI, sau đó trả về trường company_context nếu có; nếu không có trường đó, nó sẽ trả về một chuỗi rỗng. Kết quả của hàm này là nếu cấu hình AI có một ngữ cảnh công ty được định nghĩa, nó sẽ trả về ngữ cảnh đó; nếu không, nó sẽ trả về một chuỗi rỗng, đảm bảo rằng luôn có một giá trị hợp lệ được sử dụng làm ngữ cảnh công ty trong hệ thống.
def build_effective_company_context(*, user: Optional[User] = None, company: Optional[Company] = None) -> str:
    config = resolve_ai_config(user=user, company=company)
    return config.company_context or ''

# def build_employee_profile_context để xây dựng ngữ cảnh hồ sơ nhân viên dựa trên thông tin của người dùng. Nó kiểm tra xem người dùng có xác thực hay không, sau đó lấy thông tin hồ sơ và thành viên công ty của người dùng để tạo ra một chuỗi ngữ cảnh chi tiết về nhân viên, bao gồm tên đầy đủ, tên đăng nhập, email, tuổi, chức danh, mã nhân viên, phòng ban và số yếu lý lịch nếu có. Kết quả của hàm này là một chuỗi ngữ cảnh được định dạng tốt chứa thông tin chi tiết về nhân viên nếu người dùng có thông tin đó; nếu không, nó sẽ trả về một chuỗi rỗng, đảm bảo rằng luôn có một giá trị hợp lệ được sử dụng làm ngữ cảnh hồ sơ nhân viên trong hệ thống.
def build_employee_profile_context(user: Optional[User]) -> str:
    if not user or not getattr(user, 'is_authenticated', False):
        return ''
    profile = getattr(user, 'profile', None)
    if profile is None:
        return ''

    membership = get_user_membership(user)
    department_membership = (
        DepartmentMembership.objects.select_related('department')
        .filter(user=user, is_active=True, department__is_active=True)
        .order_by('department__name', 'pk')
        .first()
    )

    lines = []
    full_name = (user.get_full_name() or '').strip()
    if full_name:
        lines.append(f'Ho va ten: {full_name}')
    lines.append(f'Ten dang nhap: {membership.local_username if membership else user.username}')
    if user.email:
        lines.append(f'Email: {user.email}')
    if getattr(profile, 'age_years', None) is not None:
        lines.append(f'Tuoi: {profile.age_years}')
    if getattr(profile, 'chuc_danh', ''):
        lines.append(f'Chuc danh: {profile.chuc_danh}')
    if getattr(profile, 'ma_nhan_vien', ''):
        lines.append(f'Ma nhan vien: {profile.ma_nhan_vien}')
    department = department_membership.department if department_membership else None
    if department is not None and getattr(department, 'name', ''):
        lines.append(f'Phong ban: {department.name}')
    if getattr(profile, 'so_yeu_ly_lich', ''):
        lines.append(f'Ho so nhan su: {profile.so_yeu_ly_lich.strip()}')
    return '\n'.join(line for line in lines if line).strip()

# def build_effective_ai_context để xây dựng ngữ cảnh AI hiệu quả bằng cách kết hợp thông tin từ công ty và hồ sơ nhân viên của người dùng. Nó có thể bao gồm ngữ cảnh công ty và hồ sơ nhân viên dựa trên các flag include_company và include_profile. Nếu cả hai flag đều bị tắt, nó sẽ trả về một chuỗi rỗng, cho phép downstream prefill không gọi LLM. Kết quả của hàm này là một chuỗi ngữ cảnh tổng hợp chứa thông tin về công ty và nhân viên nếu được bao gồm; nếu không, nó sẽ trả về một chuỗi rỗng, đảm bảo rằng luôn có một giá trị hợp lệ được sử dụng làm ngữ cảnh AI trong hệ thống.
def build_effective_ai_context(
    *,
    user: Optional[User] = None,
    company: Optional[Company] = None,
    include_profile: bool = True,
    include_company: bool = True,
) -> str:
    """Ghep ngu canh AI tu hai nguon: cong ty + ho so nhan vien.

    Co the tat tung nguon doc lap qua flag `include_company`, `include_profile`.
    Khi user tat ca hai flag o frontend (toggle prefill VoiceAI/ChatAI) thi
    ham nay tra ve chuoi rong, downstream prefill se khong goi LLM.
    """
    parts = []
    if include_company:
        company_context = build_effective_company_context(user=user, company=company).strip()
        if company_context:
            parts.append(f'NGU CANH CONG TY:\n{company_context}')
    if include_profile:
        employee_context = build_employee_profile_context(user).strip()
        if employee_context:
            parts.append(f'HO SO NHAN VIEN:\n{employee_context}')
    return '\n\n'.join(parts).strip()

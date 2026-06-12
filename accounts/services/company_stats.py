"""Aggregate stats cho 1 company — dashboard platform admin (r5/M9).
• accounts/services/company_stats.py dùng để tổng hợp số liệu chi tiết của một công ty cho màn hình quản trị Platform Admin.

  File: accounts/services/company_stats.py:1

  ## Luồng Hoạt Động

  Flutter Platform Admin
  → API chi tiết công ty
  → compute_company_stats(company)
  → truy vấn nhiều app và quét media
  → cache kết quả 5 phút
  → trả dictionary/JSON
"""

from datetime import timedelta
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


CACHE_TTL_SECONDS = 300
CACHE_KEY_PREFIX = 'r5_company_stats'

# def _safe_count để thực hiện đếm số lượng bản ghi trong một queryset một cách an toàn, tránh các lỗi có thể xảy ra khi truy vấn cơ sở dữ liệu. Nó cố gắng gọi phương thức count() trên queryset và trả về kết quả dưới dạng số nguyên. Nếu có bất kỳ lỗi nào xảy ra trong quá trình này (ví dụ: lỗi kết nối cơ sở dữ liệu, lỗi truy vấn không hợp lệ), nó sẽ bắt ngoại lệ và trả về 0 thay vì gây ra lỗi, giúp đảm bảo rằng hệ thống vẫn hoạt động ổn định ngay cả khi có sự cố với truy vấn cơ sở dữ liệu.
def _safe_count(qs) -> int:
    try:
        return int(qs.count())
    except Exception:
        return 0

# def _media_company_dir để trả về đường dẫn đến thư mục media của công ty nếu tồn tại. Nó sử dụng hàm company_storage_slug để xác định slug của công ty, sau đó xây dựng đường dẫn đến thư mục media dựa trên MEDIA_ROOT và cấu trúc lưu trữ đã định nghĩa. Nếu thư mục công ty tồn tại, nó sẽ trả về đối tượng Path tương ứng; nếu không tồn tại hoặc nếu có lỗi xảy ra, nó sẽ trả về None, cho biết rằng không thể xác định thư mục media cho công ty đó.
def _media_company_dir(company) -> Optional[Path]:
    """Tra ve thu muc media/companies/<slug> neu ton tai."""
    try:
        from accounts.storage_paths import company_storage_slug
        slug = company_storage_slug(company)
    except Exception:
        return None
    media_root = Path(getattr(settings, 'MEDIA_ROOT', '') or '.')
    company_dir = media_root / 'companies' / slug
    return company_dir if company_dir.exists() else None

# def _compute_storage_total_bytes để tính tổng dung lượng lưu trữ của một công ty bằng cách quét qua tất cả các file trong thư mục media của công ty và cộng dồn kích thước của chúng. Nó sử dụng hàm _media_company_dir để lấy đường dẫn đến thư mục media của công ty, sau đó sử dụng phương thức rglob để tìm tất cả các file trong thư mục đó và cộng dồn kích thước của chúng bằng cách gọi stat().st_size. Nếu thư mục công ty không tồn tại hoặc nếu có lỗi xảy ra trong quá trình quét và tính toán, nó sẽ trả về 0, cho biết rằng không có dung lượng lưu trữ nào được sử dụng hoặc không thể xác định được dung lượng lưu trữ cho công ty đó.
def _compute_storage_total_bytes(company_dir: Optional[Path]) -> int:
    if company_dir is None or not company_dir.exists():
        return 0
    total = 0
    try:
        for p in company_dir.rglob('*'):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total

# def _compute_storage_by_subdir để phân loại dung lượng lưu trữ theo cấp-1 subdir trong cấu trúc lưu trữ của công ty. Nó lấy đường dẫn đến thư mục media của công ty, sau đó quét qua tất cả các thư mục con cấp 1 và tính tổng dung lượng của các file trong mỗi thư mục con đó. Kết quả là một dictionary với tên thư mục con làm khóa và tổng dung lượng lưu trữ của các file trong thư mục đó làm giá trị. Nếu thư mục công ty không tồn tại hoặc nếu có lỗi xảy ra trong quá trình quét và tính toán, nó sẽ trả về một dictionary rỗng, cho biết rằng không thể xác định được phân loại dung lượng lưu trữ cho công ty đó.
def _compute_storage_by_subdir(company_dir: Optional[Path]) -> dict:
    """Phan loai dung luong theo cap-1 subdir trong companies/<slug>/."""
    if company_dir is None or not company_dir.exists():
        return {}
    result: dict[str, int] = {}
    try:
        for entry in company_dir.iterdir():
            if not entry.is_dir():
                continue
            subtotal = 0
            try:
                for p in entry.rglob('*'):
                    if p.is_file():
                        try:
                            subtotal += p.stat().st_size
                        except OSError:
                            pass
            except OSError:
                pass
            result[entry.name] = subtotal
    except OSError:
        pass
    return result

# def _serialize_company để chuyển đổi đối tượng Company thành một dictionary có cấu trúc dữ liệu đơn giản, bao gồm các trường thông tin cơ bản của công ty như id, code, slug, name, status, description, industry, address, email, phone, website, company_context, created_at và updated_at. Nó sử dụng getattr để lấy giá trị của các trường có thể không tồn tại và đảm bảo rằng chúng luôn có giá trị hợp lệ (ví dụ: chuỗi rỗng hoặc None). Kết quả của hàm này là một dictionary chứa thông tin chi tiết về công ty được chuẩn hóa và dễ dàng sử dụng trong các phần khác của hệ thống.
def _serialize_company(company) -> dict:
    """Field thuc te ton tai trong Company model (xem accounts/models.py:27)."""
    return {
        'id': company.id,
        'code': company.code,
        'slug': getattr(company, 'slug', ''),
        'name': company.name,
        'status': company.status,
        'description': getattr(company, 'description', '') or '',
        'industry': getattr(company, 'industry', '') or '',
        'address': getattr(company, 'address', '') or '',
        'email': getattr(company, 'email', '') or '',
        'phone': getattr(company, 'phone', '') or '',
        'website': getattr(company, 'website', '') or '',
        'company_context': getattr(company, 'company_context', '') or '',
        'created_at': company.created_at.isoformat() if getattr(company, 'created_at', None) else None,
        'updated_at': company.updated_at.isoformat() if getattr(company, 'updated_at', None) else None,
    }

# def _compute_counts để tính toán các số liệu thống kê cơ bản cho một công ty, bao gồm số lượng người dùng, phòng ban, vị trí, mẫu tài liệu, tài liệu, prompts và bản sao lưu liên quan đến công ty đó. Nó thực hiện các truy vấn cơ sở dữ liệu để đếm số lượng bản ghi tương ứng với công ty và trả về một dictionary chứa các số liệu thống kê này. Nếu có lỗi xảy ra trong quá trình truy vấn cơ sở dữ liệu, nó sẽ trả về 0 cho các số liệu thống kê tương ứng, đảm bảo rằng hệ thống vẫn hoạt động ổn định ngay cả khi có sự cố với truy vấn cơ sở dữ liệu.
def _compute_counts(company) -> dict:
    from documents.models import Document
    from document_templates.models import DocumentTemplate
    from accounts.models import Department, CompanyUserMembership, CompanyPosition

    # Prompt: filter qua owner_membership/company neu co
    try:
        from prompts.models import Prompt
        prompt_count = _safe_count(
            Prompt.objects.filter(owner__memberships__company=company).distinct()
        )
    except Exception:
        prompt_count = 0

    try:
        backup_count = _safe_count(
            company.backups.all()  # related_name='backups' on CompanyBackup.company
        )
    except Exception:
        backup_count = 0

    return {
        'users': _safe_count(CompanyUserMembership.objects.filter(company=company)),
        'departments': _safe_count(Department.objects.filter(company=company)),
        'positions': _safe_count(CompanyPosition.objects.filter(company=company)),
        'templates': _safe_count(DocumentTemplate.objects.filter(company=company)),
        'documents': _safe_count(Document.objects.filter(company=company)),
        'prompts': prompt_count,
        'backups': backup_count,
    }

# def _compute_last_backup để lấy thông tin về bản sao lưu (backup) gần nhất của một công ty. Nó truy vấn cơ sở dữ liệu để tìm bản sao lưu mới nhất dựa trên trường created_at, sau đó trả về một dictionary chứa các thông tin chi tiết về bản sao lưu đó, bao gồm id, name, status, kind, size_bytes, created_at, completed_at, is_encrypted, signature_status và has_signature. Nếu không tìm thấy bản sao lưu nào hoặc nếu có lỗi xảy ra trong quá trình truy vấn cơ sở dữ liệu, nó sẽ trả về None, cho biết rằng không có thông tin về bản sao lưu nào có sẵn cho công ty đó.
def _compute_last_backup(company) -> Optional[dict]:
    try:
        from company_backups.models import CompanyBackup
        last = (
            CompanyBackup.objects.filter(company=company)
            .order_by('-created_at')
            .first()
        )
    except Exception:
        return None
    if last is None:
        return None
    return {
        'id': last.id,
        'name': last.name,
        'status': last.status,
        'kind': last.kind,
        'size_bytes': last.size_bytes,
        'created_at': last.created_at.isoformat() if last.created_at else None,
        'completed_at': last.completed_at.isoformat() if last.completed_at else None,
        'is_encrypted': bool(getattr(last, 'encryption_meta', None)),
        'signature_status': getattr(last, 'signature_status', 'unsigned'),
        'has_signature': bool(getattr(last, 'signature_path', '')),
    }

# def _compute_extended_counts để tính toán các số liệu thống kê mở rộng cho một công ty, bao gồm số lượng người dùng hoạt động trong 30 ngày qua, số lượng tài liệu và mẫu tài liệu mới được tạo trong 30 ngày qua, số lượng cuộc gọi AI trong 30 ngày qua và tổng số cuộc gọi AI, cũng như phân loại số lượng tài liệu và mẫu tài liệu theo trạng thái. Nó thực hiện các truy vấn cơ sở dữ liệu để đếm số lượng bản ghi tương ứng với các tiêu chí này và trả về một dictionary chứa các số liệu thống kê mở rộng này. Nếu có lỗi xảy ra trong quá trình truy vấn cơ sở dữ liệu, nó sẽ trả về 0 hoặc một dictionary rỗng cho các số liệu thống kê tương ứng, đảm bảo rằng hệ thống vẫn hoạt động ổn định ngay cả khi có sự cố với truy vấn cơ sở dữ liệu.
def _compute_extended_counts(company) -> dict:
    """Stats them: active users 30d, doc/template moi 30d, AI usage, status breakdown."""
    from documents.models import Document
    from document_templates.models import DocumentTemplate
    from accounts.models import CompanyUserMembership, DepartmentMembership

    now = timezone.now()
    cutoff_30d = now - timedelta(days=30)

    def _by_status(qs, field='status'):
        out: dict[str, int] = {}
        try:
            for row in qs.values(field).annotate_n_count() if False else []:
                pass
        except Exception:
            pass
        try:
            from django.db.models import Count
            for row in qs.values(field).annotate(n=Count('id')):
                key = str(row.get(field) or 'unknown')
                out[key] = int(row.get('n') or 0)
        except Exception:
            pass
        return out

    docs_qs = Document.objects.filter(company=company)
    tmpl_qs = DocumentTemplate.objects.filter(company=company)

    documents_30d = _safe_count(docs_qs.filter(created_at__gte=cutoff_30d))
    templates_30d = _safe_count(tmpl_qs.filter(created_at__gte=cutoff_30d))

    members_qs = CompanyUserMembership.objects.filter(company=company)
    users_active_30d = _safe_count(
        members_qs.filter(user__last_login__gte=cutoff_30d)
    )
    members_with_dept = _safe_count(
        DepartmentMembership.objects.filter(
            department__company=company, is_active=True
        ).values('user_id').distinct()
    )
    members_total = _safe_count(members_qs)

    try:
        from ai_engine.models import AIUsageLog
        ai_calls_30d = _safe_count(
            AIUsageLog.objects.filter(
                user__memberships__company=company,
                created_at__gte=cutoff_30d,
            ).distinct()
        )
        ai_calls_total = _safe_count(
            AIUsageLog.objects.filter(
                user__memberships__company=company,
            ).distinct()
        )
    except Exception:
        ai_calls_30d = 0
        ai_calls_total = 0

    try:
        from documents.models import DocumentShare
        pending_doc_shares = _safe_count(
            DocumentShare.objects.filter(
                document__company=company,
                status='pending',
            )
        )
    except Exception:
        pending_doc_shares = 0

    try:
        from document_templates.models import DocumentTemplateShare
        pending_tmpl_shares = _safe_count(
            DocumentTemplateShare.objects.filter(
                template__company=company,
                status='pending',
            )
        )
    except Exception:
        pending_tmpl_shares = 0

    return {
        'documents_30d': documents_30d,
        'templates_30d': templates_30d,
        'users_active_30d': users_active_30d,
        'members_with_department': members_with_dept,
        'members_without_department': max(0, members_total - members_with_dept),
        'ai_calls_30d': ai_calls_30d,
        'ai_calls_total': ai_calls_total,
        'pending_doc_shares': pending_doc_shares,
        'pending_template_shares': pending_tmpl_shares,
        'templates_by_status': _by_status(tmpl_qs, 'status'),
        'documents_by_status': _by_status(docs_qs, 'status'),
    }

# def _compute_org_tree để xây dựng cây tổ chức 3 tầng cho một công ty, bao gồm công ty, phòng ban (và vị trí) và thành viên. Cấu trúc cây được xây dựng dựa trên các mô hình Department, DepartmentMembership và CompanyUserMembership, cũng như thông tin về vị trí của người dùng nếu có. Kết quả là một dictionary chứa cấu trúc cây tổ chức, với mỗi node đại diện cho một công ty, phòng ban hoặc thành viên, cùng với các thông tin chi tiết như id, name, subtitle và role. Nếu có lỗi xảy ra trong quá trình truy vấn cơ sở dữ liệu hoặc xây dựng cây tổ chức, nó sẽ trả về một cấu trúc cây rỗng hoặc không đầy đủ, đảm bảo rằng hệ thống vẫn hoạt động ổn định ngay cả khi có sự cố với dữ liệu tổ chức của công ty đó.
def _compute_org_tree(company) -> dict:
    """Cay to chuc 3 tang: Company -> Department (+ Position) -> Member.

    Cau truc:
        root = {
          type: 'company', id, name, subtitle, children: [
            { type: 'department', id, name, subtitle, manager?, children: [
                { type: 'member', id, name, role, position? }, ...
            ]},
            ...
          ]
        }
    Them 1 nut "Khong phan phong" gom user thuoc company nhung chua co Department.
    """
    from accounts.models import (
        Department, DepartmentMembership, CompanyUserMembership,
    )

    departments = list(
        Department.objects.filter(company=company, is_active=True)
        .select_related('manager')
        .order_by('name')
    )
    company_memberships = list(
        CompanyUserMembership.objects.filter(company=company)
        .select_related('user')
    )
    user_position_map: dict[int, str] = {}
    try:
        from accounts.models import CompanyUserPosition
        for cup in CompanyUserPosition.objects.filter(
            user__memberships__company=company,
            position__company=company,
        ).select_related('position', 'user'):
            user_position_map.setdefault(cup.user_id, cup.position.name)
    except Exception:
        pass

    dept_member_map: dict[int, list[dict]] = {d.id: [] for d in departments}
    user_to_dept_ids: dict[int, set[int]] = {}

    for m in DepartmentMembership.objects.filter(
        department__company=company,
        is_active=True,
    ).select_related('user', 'department'):
        node = {
            'type': 'member',
            'id': m.user_id,
            'name': (m.user.get_full_name() or m.user.username),
            'subtitle': user_position_map.get(m.user_id, 'Thanh vien'),
            'role': 'leader' if getattr(m, 'role', '') == 'leader' else 'member',
        }
        dept_member_map.setdefault(m.department_id, []).append(node)
        user_to_dept_ids.setdefault(m.user_id, set()).add(m.department_id)

    dept_children = []
    for d in departments:
        member_nodes = dept_member_map.get(d.id, [])
        manager_node = None
        if d.manager_id:
            manager_node = {
                'id': d.manager_id,
                'name': (d.manager.get_full_name() or d.manager.username)
                        if d.manager else '',
            }
        dept_children.append({
            'type': 'department',
            'id': d.id,
            'name': d.name,
            'code': d.code,
            'subtitle': f'{len(member_nodes)} thanh vien',
            'manager': manager_node,
            'children': member_nodes,
        })

    unassigned = []
    for cm in company_memberships:
        if cm.user_id in user_to_dept_ids:
            continue
        unassigned.append({
            'type': 'member',
            'id': cm.user_id,
            'name': (cm.user.get_full_name() or cm.user.username),
            'subtitle': user_position_map.get(cm.user_id, 'Chua phan phong'),
            'role': 'member',
        })
    if unassigned:
        dept_children.append({
            'type': 'department',
            'id': None,
            'name': 'Chua phan phong',
            'code': '',
            'subtitle': f'{len(unassigned)} thanh vien',
            'manager': None,
            'children': unassigned,
        })

    return {
        'root': {
            'type': 'company',
            'id': company.id,
            'name': company.name,
            'code': company.code,
            'subtitle': f'{len(company_memberships)} thanh vien · '
                        f'{len(departments)} phong ban',
            'children': dept_children,
        },
        'totals': {
            'departments': len(departments),
            'members': len(company_memberships),
            'unassigned': len(unassigned),
        },
    }

# def compute_company_stats để tính toán các số liệu thống kê tổng hợp cho một công ty, bao gồm thông tin chi tiết về công ty, số lượng người dùng, phòng ban, vị trí, mẫu tài liệu, tài liệu, prompts và bản sao lưu, cũng như phân loại dung lượng lưu trữ và cây tổ chức. Kết quả được lưu vào cache trong 5 phút để tối ưu hiệu suất khi truy cập lại trong khoảng thời gian đó. Nếu bypass_cache được đặt thành True, nó sẽ bỏ qua cache và tính toán lại số liệu thống kê mới nhất từ cơ sở dữ liệu và hệ thống file.
def compute_company_stats(company, *, bypass_cache: bool = False) -> dict:
    """Tinh aggregate stats cho 1 company. Cache 5 phut.

    Schema tra ve:
        {
            'company': {...},
            'counts': {...},
            'storage': {'total_bytes': int, 'by_subdir': dict},
            'last_backup': {...} | None,
        }
    """
    cache_key = f'{CACHE_KEY_PREFIX}:{company.pk}'
    if not bypass_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    company_dir = _media_company_dir(company)
    result = {
        'company': _serialize_company(company),
        'counts': _compute_counts(company),
        'extended': _compute_extended_counts(company),
        'storage': {
            'total_bytes': _compute_storage_total_bytes(company_dir),
            'by_subdir': _compute_storage_by_subdir(company_dir),
        },
        'last_backup': _compute_last_backup(company),
        'org_tree': _compute_org_tree(company),
    }
    cache.set(cache_key, result, CACHE_TTL_SECONDS)
    return result

# def invalidate_company_stats để xóa cache của số liệu thống kê công ty khi có sự thay đổi dữ liệu liên quan đến công ty đó, đảm bảo rằng lần truy cập tiếp theo sẽ tính toán lại số liệu thống kê mới nhất từ cơ sở dữ liệu và hệ thống file. Nó sử dụng cache.delete với khóa cache được xây dựng dựa trên tiền tố CACHE_KEY_PREFIX và primary key của công ty để xóa cache tương ứng.
def invalidate_company_stats(company_pk: int) -> None:
    cache.delete(f'{CACHE_KEY_PREFIX}:{company_pk}')

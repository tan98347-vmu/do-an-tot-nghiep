"""Aggregate stats cho 1 company — dashboard platform admin (r5/M9).

API duy nhat: `compute_company_stats(company) -> dict`.
Co cache 5 phut bang `django.core.cache`. Khi can luc nao bypass cache
(vi du goi tu management command), truyen `bypass_cache=True`.
"""

from datetime import timedelta
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


CACHE_TTL_SECONDS = 300
CACHE_KEY_PREFIX = 'r5_company_stats'


def _safe_count(qs) -> int:
    try:
        return int(qs.count())
    except Exception:
        return 0


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


def invalidate_company_stats(company_pk: int) -> None:
    cache.delete(f'{CACHE_KEY_PREFIX}:{company_pk}')

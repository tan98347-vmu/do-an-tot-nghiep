# file từ code cũ fallback, chưa được chỉnh sửa trong quá trình tối ưu. File này chứa các hàm liên quan đến quyền truy cập và quản lý tài nguyên như template, document và prompt. Nó định nghĩa các hàm để kiểm tra quyền sử dụng, chỉnh sửa, xóa và xem xét các tài nguyên này dựa trên người dùng và các nhóm người dùng mà họ thuộc về. Các hàm này thường gọi đến các dịch vụ chia sẻ (sharing.services) để xác định quyền truy cập dựa trên các quy tắc đã được định nghĩa trước đó.

"""
Helper quyen dung chung cho template/document/prompt - **WRAPPER LAYER**.

Tu phase 2 cua co che chia se thong nhat, toan bo logic quyen dat trong
`sharing.services`. File nay duoc giu lai voi cung chu ky ham de:
  - Khong vo cac caller cu (vd: api/views/templates.py, api/views/documents.py,
    api/views/prompts.py, signing/, word_ai/, ai_engine/...).
  - Cho phep cap nhat dan dan tung caller sang goi truc tiep `sharing.services`.

Quy tac chung cua sharing.services:
  - Owner (owner_id/created_by_id) luon co full quyen.
  - Platform admin / superuser luon co full quyen.
  - User khac duoc quyen qua ShareGrant active (scope=group/colleagues/everyone).
  - Ladder: delete > edit > view.
  - Reviewer: leader cua nhom (cho scope=group/colleagues) hoac admin (cho scope=everyone).
"""

from __future__ import annotations

from django.db.models import Q

from .models import UserGroup, UserGroupMembership
from .tenancy import get_user_company, is_platform_admin


def get_user_groups(user):
    """Tra ve queryset cac UserGroup ma user dang la thanh vien (cung company)."""
    groups = UserGroup.objects.filter(memberships__user=user)
    company = get_user_company(user)
    if company is not None:
        groups = groups.filter(company=company)
    return groups


def is_leader_of(user, group=None):
    """User co la leader cua mot nhom cu the (hoac bat ki nhom nao) khong."""
    qs = UserGroupMembership.objects.filter(user=user, role=UserGroupMembership.ROLE_LEADER)
    if group is not None:
        return qs.filter(group=group).exists()
    return qs.exists()


# ============================================================================
# Template
# ============================================================================

def get_accessible_templates(user):
    """Templates ma user co the xem (alias cua get_usable_templates)."""
    return get_usable_templates(user)


def get_usable_templates(user):
    """Templates ma user co the dung de tao tai lieu / mo / sua tuy quyen."""
    from sharing.services import get_accessible_qs
    from document_templates.models import DocumentTemplate

    return get_accessible_qs(user, DocumentTemplate)


def can_use_template(user, template):
    return get_usable_templates(user).filter(pk=template.pk).exists()


def can_edit_template(user, template):
    if not user:
        return False
    from sharing.services import can_edit

    return can_edit(user, template)


def can_delete_template(user, template):
    if not user:
        return False
    from sharing.services import can_delete

    return can_delete(user, template)


def get_reviewable_templates(user):
    from sharing.services import get_reviewable_qs
    from document_templates.models import DocumentTemplate

    return get_reviewable_qs(user, DocumentTemplate)


def can_review_template(user, template):
    return get_reviewable_templates(user).filter(pk=template.pk).exists()


def get_template_detail_queryset(user):
    from document_templates.models import DocumentTemplate

    company = get_user_company(user)
    if is_platform_admin(user) and company is None:
        return DocumentTemplate.objects.all()
    usable_ids = get_usable_templates(user).values_list('pk', flat=True)
    reviewable_ids = get_reviewable_templates(user).values_list('pk', flat=True)
    queryset = DocumentTemplate.objects.filter(
        Q(pk__in=usable_ids) | Q(pk__in=reviewable_ids)
    ).distinct()
    if company is not None:
        queryset = queryset.filter(company=company)
    return queryset


# ============================================================================
# Prompt
# ============================================================================

def get_accessible_prompts(user):
    from sharing.services import get_accessible_qs
    from prompts.models import Prompt

    return get_accessible_qs(user, Prompt)


def can_edit_prompt(user, prompt):
    if not user:
        return False
    from sharing.services import can_edit

    return can_edit(user, prompt)


def can_delete_prompt(user, prompt):
    if not user:
        return False
    from sharing.services import can_delete

    return can_delete(user, prompt)


# ============================================================================
# Document
# ============================================================================

def get_accessible_documents(user):
    """Documents user co the xem.

    Bao gom (ngoai grants thong thuong):
      - Mailbox forward (forward_to/forwarded_by) - giu nhu logic cu.
      - Signing tasks (signer_user) - giu nhu logic cu.
    """
    from sharing.services import get_accessible_qs
    from documents.models import Document
    from signing.models import PACKET_ACTIVE, PACKET_COMPLETED, PACKET_REJECTED
    from django.db.models import F

    # Bat dau bang queryset cua sharing layer
    base_qs = get_accessible_qs(user, Document)

    # Mo rong them: mailbox + signing - dung Q union ma khong loc lai company
    if user is None or not getattr(user, 'is_authenticated', False):
        return base_qs

    extra_qs = Document.objects.filter(
        Q(mailbox_threads__entries__forwarded_to=user)
        | Q(mailbox_threads__entries__forwarded_by=user)
        | Q(
            signing_packets__tasks__signer_user=user,
            signing_packets__status__in=[PACKET_ACTIVE, PACKET_COMPLETED, PACKET_REJECTED],
            signing_packets__source_version_number=F('version_number'),
        )
    ).filter(is_archived=False).distinct()

    company = get_user_company(user)
    if company is not None and not is_platform_admin(user):
        extra_qs = extra_qs.filter(company=company)

    # Union: tat ca document tu base_qs + extra_qs
    accessible_pks = list(base_qs.values_list('pk', flat=True)) + list(extra_qs.values_list('pk', flat=True))
    return Document.objects.filter(pk__in=accessible_pks).distinct()


def is_document_edit_locked(document):
    from documents.edit_lock_state import get_document_edit_lock_state

    return get_document_edit_lock_state(document).is_locked


def can_edit_document(user, document):
    if not user:
        return False
    if is_document_edit_locked(document):
        return False
    from sharing.services import can_edit

    return can_edit(user, document)


def can_delete_document(user, document):
    if not user:
        return False
    if is_document_edit_locked(document):
        return False
    from sharing.services import can_delete

    return can_delete(user, document)


def get_reviewable_documents(user):
    from sharing.services import get_reviewable_qs
    from documents.models import Document

    return get_reviewable_qs(user, Document)


def can_review_document(user, document):
    return get_reviewable_documents(user).filter(pk=document.pk).exists()


def get_document_detail_queryset(user):
    from documents.models import Document

    company = get_user_company(user)
    if user.is_superuser:
        queryset = Document.objects.all()
        if company is not None:
            queryset = queryset.filter(company=company)
        return queryset
    accessible_ids = get_accessible_documents(user).values_list('pk', flat=True)
    reviewable_ids = get_reviewable_documents(user).values_list('pk', flat=True)
    queryset = Document.objects.filter(
        Q(pk__in=accessible_ids) | Q(pk__in=reviewable_ids)
    ).distinct()
    if company is not None:
        queryset = queryset.filter(company=company)
    return queryset

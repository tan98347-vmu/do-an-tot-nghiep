"""
Hang so dung chung cho co che chia se thong nhat.

- SCOPE_*: 4 pham vi chia se (private/group/colleagues/everyone).
- PERMISSION_*: 3 muc quyen theo cap do (view < edit < delete).
- APPROVAL_*: trang thai duyet (draft/pending_leader/pending_admin/active/rejected).

Logic refactor: thay the cho cac hang so sau day (chuyen dung chung vao day):
- documents.models.VIS_PRIVATE/VIS_GROUP/VIS_PUBLIC + SHARE_*
- document_templates.models.STATUS_* + DocumentTemplate.VISIBILITY_*
- prompts.models.PROMPT_STATUS_*
- accounts.peer_permissions.PeerPermissionLevel
"""

from __future__ import annotations


SCOPE_PRIVATE = 'private'
SCOPE_GROUP = 'group'
SCOPE_COLLEAGUES = 'colleagues'
SCOPE_EVERYONE = 'everyone'

SCOPE_CHOICES = [
    (SCOPE_PRIVATE, 'Rieng tu'),
    (SCOPE_GROUP, 'Nhom'),
    (SCOPE_COLLEAGUES, 'Dong nghiep'),
    (SCOPE_EVERYONE, 'Moi nguoi'),
]


PERMISSION_VIEW = 'view'
PERMISSION_EDIT = 'edit'
PERMISSION_DELETE = 'delete'

PERMISSION_CHOICES = [
    (PERMISSION_VIEW, 'Chi xem'),
    (PERMISSION_EDIT, 'Xem & sua'),
    (PERMISSION_DELETE, 'Toan quyen (xem, sua, xoa)'),
]

# Ladder: cao hon bao gom thap hon
PERMISSION_ORDER = {
    PERMISSION_VIEW: 1,
    PERMISSION_EDIT: 2,
    PERMISSION_DELETE: 3,
}


APPROVAL_DRAFT = 'draft'
APPROVAL_PENDING_LEADER = 'pending_leader'
APPROVAL_PENDING_ADMIN = 'pending_admin'
APPROVAL_ACTIVE = 'active'
APPROVAL_REJECTED = 'rejected'

APPROVAL_CHOICES = [
    (APPROVAL_DRAFT, 'Nhap'),
    (APPROVAL_PENDING_LEADER, 'Cho truong nhom duyet'),
    (APPROVAL_PENDING_ADMIN, 'Cho admin duyet'),
    (APPROVAL_ACTIVE, 'Da kich hoat'),
    (APPROVAL_REJECTED, 'Bi tu choi'),
]


# Map ten entity_type tu URL/path sang model class string
ENTITY_TYPE_TO_MODEL = {
    'templates': ('document_templates', 'DocumentTemplate'),
    'documents': ('documents', 'Document'),
    'prompts': ('prompts', 'Prompt'),
}

# Reverse map: (app_label, model) -> entity_type string
MODEL_TO_ENTITY_TYPE = {value: key for key, value in ENTITY_TYPE_TO_MODEL.items()}


def normalize_permission(level: str | None) -> str | None:
    value = str(level or '').strip().lower()
    if value in PERMISSION_ORDER:
        return value
    return None


def normalize_scope(scope: str | None) -> str | None:
    value = str(scope or '').strip().lower()
    for key, _ in SCOPE_CHOICES:
        if value == key:
            return value
    return None


def required_approver_role(scope: str) -> str:
    """Tra ve 'leader' | 'admin' | 'none' tuy theo scope."""
    normalized = normalize_scope(scope)
    if normalized in (SCOPE_GROUP, SCOPE_COLLEAGUES):
        return 'leader'
    if normalized == SCOPE_EVERYONE:
        return 'admin'
    return 'none'

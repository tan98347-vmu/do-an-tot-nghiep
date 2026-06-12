from accounts.permissions import is_leader_of
from document_templates.models import (
    DocumentTemplate,
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_PENDING_LEADER,
)


# def _auto_status quyết định trạng thái duyệt khi tạo/sửa mẫu theo nguồn + phạm vi + vai trò: superuser hoặc private -> approved; group mà là trưởng nhóm -> approved, không phải -> pending_leader; public -> pending (chờ admin).
# vd: nhân viên thường tạo mẫu visibility='group' -> 'pending_leader'.
def _auto_status(source_type, visibility, user, target_group=None):
    if user and user.is_superuser:
        return STATUS_APPROVED
    if visibility == DocumentTemplate.VISIBILITY_PRIVATE:
        return STATUS_APPROVED
    if visibility == DocumentTemplate.VISIBILITY_GROUP:
        if target_group and is_leader_of(user, target_group):
            return STATUS_APPROVED
        return STATUS_PENDING_LEADER
    return STATUS_PENDING

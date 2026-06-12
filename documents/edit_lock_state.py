from dataclasses import dataclass

from django.utils import timezone

from signing.models import PACKET_ACTIVE, PACKET_COMPLETED

from .manual_edit_models import DocumentManualEditSession


# class DocumentEditLockState (dataclass) mô tả trạng thái khóa chỉnh sửa của 1 văn bản: có bị khóa không, lý do (đang ký / đang sửa thủ công), thông tin phiên sửa và ai đang giữ, có cho phép tiếp tục (resume) không.
# vd: đang có phiên Collabora mở -> is_locked=True, code='manual_edit_active'.
@dataclass(frozen=True)
class DocumentEditLockState:
    is_locked: bool
    code: str = ''
    detail: str = ''
    manual_edit_active: bool = False
    manual_edit_session_id: int | None = None
    manual_edit_session_status: str = ''
    manual_edit_locked_by_name: str = ''
    can_resume_manual_edit: bool = False


# def _manual_edit_lock_state kiểm tra văn bản có phiên sửa thủ công đang mở (còn hạn) không; nếu có -> khóa, kèm tên người giữ và cờ can_resume cho chủ phiên/superuser.
# vd: A đang mở phiên sửa -> B thấy 'đang được chỉnh sửa', A thấy 'bạn đang có phiên mở'.
def _manual_edit_lock_state(document, *, user=None):
    now = timezone.now()
    session = (
        DocumentManualEditSession.objects.select_related('created_by')
        .filter(
            document=document,
            status__in=DocumentManualEditSession.active_statuses(),
            expires_at__gt=now,
        )
        .order_by('-created_at')
        .first()
    )
    if session is None:
        return DocumentEditLockState(is_locked=False)
    locked_by_name = ''
    if session.created_by_id:
        locked_by_name = session.created_by.get_full_name() or session.created_by.username
    can_resume = bool(user and (user.is_superuser or session.created_by_id == user.id))
    detail = (
        'Van ban dang duoc chinh sua thu cong trong trinh sua web. '
        'Hoan tat hoac huy phien chinh sua truoc khi thuc hien thao tac nay.'
    )
    if can_resume:
        detail = 'Ban dang co phien chinh sua thu cong dang mo cho van ban nay.'
    return DocumentEditLockState(
        is_locked=True,
        code='manual_edit_active',
        detail=detail,
        manual_edit_active=True,
        manual_edit_session_id=session.id,
        manual_edit_session_status=session.status,
        manual_edit_locked_by_name=locked_by_name,
        can_resume_manual_edit=can_resume,
    )


# def get_document_edit_lock_state trả trạng thái khóa của văn bản: khóa nếu đang có quy trình ký (packet active/completed) hoặc đang có phiên sửa thủ công; không thì mở.
# vd: văn bản đang trong quy trình ký -> is_locked=True, code='signing_locked'.
def get_document_edit_lock_state(document, *, user=None):
    if not document or not getattr(document, 'pk', None):
        return DocumentEditLockState(is_locked=False)
    if document.signing_packets.filter(
        status__in=[PACKET_ACTIVE, PACKET_COMPLETED],
    ).exists():
        return DocumentEditLockState(
            is_locked=True,
            code='signing_locked',
            detail='Van ban da bi khoa chinh sua vi da co quy trinh ky dang hoat dong hoac da hoan tat.',
        )
    return _manual_edit_lock_state(document, user=user)

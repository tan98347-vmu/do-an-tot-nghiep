"""
Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
Vai tro backend: File `document_templates/notifications.py` giu hoac ho tro luong backend cho CRUD mau, duyet mau, version mau, import DOCX/URL, bulk upload va preview noi dung mau.
Vai tro cua no trong frontend: Cac man `/templates`, `/templates/create`, man chi tiet mau va man bulk upload lay du lieu hoac chiu tac dong gian tiep tu file nay.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`.
Tac dung: Giu cho du lieu mau, quyen thao tac va preview cua nhom man Mau van ban luon dong nhat giua API, storage va chi so tim kiem.
"""

from django.utils import timezone

from .models import TemplateReviewNotification

# def create_template_review_notification tạo thông báo duyệt mẫu gửi cho chủ mẫu (owner) khi có hành động (duyệt/từ chối/yêu cầu sửa...); bỏ qua nếu actor chính là owner.
# vd: trưởng nhóm từ chối mẫu -> tạo thông báo 'rejected' cho owner.
def create_template_review_notification(template, *, action, actor=None, comment=''):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Ham `create_template_review_notification` la mot don vi xu ly backend cua file `document_templates/notifications.py`, chu yeu de tao moi ban ghi hoac khoi tao mot luong xu ly.
    Vai tro cua no trong frontend: Frontend chu yeu quan sat ket qua gian tiep cua buoc tao moi ban ghi hoac khoi tao mot luong xu ly nay thong qua API, du lieu luu tru hoac trang thai do lop goi phia tren tra ve.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Dung cung cap voi cac ham `mark_template_notifications_read` trong module nay.
    Tac dung: Tach rieng trach nhiem tao moi ban ghi hoac khoi tao mot luong xu ly de pham vi tac dong cua `create_template_review_notification` ro rang hon.
    """
    recipient = getattr(template, 'owner', None)
    if recipient is None:
        return None
    if actor is not None and getattr(actor, 'pk', None) == getattr(recipient, 'pk', None):
        return None

    return TemplateReviewNotification.objects.create(
        recipient=recipient,
        template=template,
        action=action,
        actor=actor,
        comment=comment or '',
    )

# def mark_template_notifications_read đánh dấu đã đọc các thông báo duyệt của 1 mẫu cho 1 người nhận; trả số bản ghi đã cập nhật.
# vd: owner mở mẫu #5 -> các thông báo của mẫu #5 chuyển is_read=True.
def mark_template_notifications_read(*, recipient, template_id):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Ham `mark_template_notifications_read` la mot don vi xu ly backend cua file `document_templates/notifications.py`, chu yeu de xu ly du lieu hoac thao tac lien quan toi mau van ban.
    Vai tro cua no trong frontend: Frontend chu yeu quan sat ket qua gian tiep cua buoc xu ly du lieu hoac thao tac lien quan toi mau van ban nay thong qua API, du lieu luu tru hoac trang thai do lop goi phia tren tra ve.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Dung cung cap voi cac ham `create_template_review_notification` trong module nay.
    Tac dung: Tach rieng trach nhiem xu ly du lieu hoac thao tac lien quan toi mau van ban de pham vi tac dong cua `mark_template_notifications_read` ro rang hon.
    """
    if recipient is None or template_id is None:
        return 0
    updated = TemplateReviewNotification.objects.filter(
        recipient=recipient,
        template_id=template_id,
        is_read=False,
    ).update(
        is_read=True,
        read_at=timezone.now(),
    )
    return updated

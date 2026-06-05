"""
Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
Vai tro backend: File `api/views/notifications.py` giu hoac ho tro luong backend cho cau hinh du an, anh xa route, thong ke dashboard, quan tri du lieu nen va API chung toan he thong.
Vai tro cua no trong frontend: Cac man `/dashboard`, `/admin`, `/admin/ai-config`, `/admin/backup`, badge thong bao va shell dieu huong doc hoac chiu tac dong tu file nay.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `document_templates.models`.
Tac dung: Giu cho cac man dieu phoi cap he thong co cung nguon cau hinh, cung route va cung so lieu nen khi frontend khoi chay.
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ai_tasks.models import STATUS_QUEUED, STATUS_RUNNING
from api.services.aggregate_notifications import (
    build_aggregate_notifications,
    get_aggregate_unread_count,
    mark_aggregate_notification_read,
    mark_all_aggregate_notifications_read,
)
from document_templates.models import TemplateReviewNotification
from document_templates.notifications import mark_template_notifications_read
from ..serializers.notifications import (
    AggregateNotificationItemSerializer,
    AggregateNotificationReadSerializer,
    TemplateReviewNotificationSerializer,
)


def _serialize_task_notification(task):
    return {
        'kind': 'task',
        'task_id': str(task.task_id),
        'status': task.status,
        'title_summary': task.title_summary,
        'deeplink': task.deeplink,
        'updated_at': task.updated_at.isoformat(),
        'error_message': task.error_message,
        'progress_percent': task.progress_percent,
        'related_entity_type': task.related_entity_type,
        'related_entity_id': task.related_entity_id,
        'is_read': task.is_dismissed,
    }

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_list(request):
    """
    Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
    Vai tro backend: Ham `notification_list` la endpoint hoac diem vao REST cua file `api/views/notifications.py`, chiu trach nhiem tra danh sach du lieu theo bo loc hien tai theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can tra danh sach du lieu theo bo loc hien tai tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `document_templates.models`. Dung cung cap voi cac ham `notification_unread_count`, `notification_mark_read`, `notification_mark_template_read` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac tra danh sach du lieu theo bo loc hien tai tren giao dien.
    """
    tab = str(request.GET.get('tab') or '').strip().lower()
    if tab == 'tasks':
        from ai_tasks.models import AITaskProgress

        limit = min(max(int(request.GET.get('limit', 20) or 20), 1), 100)
        qs = AITaskProgress.objects.filter(user=request.user).exclude(
            status__in=[STATUS_QUEUED, STATUS_RUNNING],
        ).order_by('-created_at')
        items = [_serialize_task_notification(task) for task in qs[:limit] if not task.is_dismissed]
        return Response(items[:limit])

    unread_only = str(request.GET.get('unread', '') or '').lower() in {'1', 'true', 'yes'}
    template_id = request.GET.get('template_id')

    qs = TemplateReviewNotification.objects.filter(recipient=request.user).select_related(
        'template',
        'actor',
    )
    if unread_only:
        qs = qs.filter(is_read=False)
    if template_id:
        qs = qs.filter(template_id=template_id)

    limit = min(max(int(request.GET.get('limit', 20) or 20), 1), 100)
    serializer = TemplateReviewNotificationSerializer(qs[:limit], many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_unread_count(request):
    """
    Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
    Vai tro backend: Ham `notification_unread_count` la endpoint hoac diem vao REST cua file `api/views/notifications.py`, chiu trach nhiem dem so ban ghi hoac so muc theo dieu kien theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can dem so ban ghi hoac so muc theo dieu kien tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `document_templates.models`. Dung cung cap voi cac ham `notification_list`, `notification_mark_read`, `notification_mark_template_read` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac dem so ban ghi hoac so muc theo dieu kien tren giao dien.
    """
    count = TemplateReviewNotification.objects.filter(
        recipient=request.user,
        is_read=False,
    ).count()
    if str(request.GET.get('include_tasks', '') or '').lower() in {'1', 'true', 'yes'}:
        from ai_tasks.models import AITaskProgress

        for task in AITaskProgress.objects.filter(user=request.user).exclude(
            status__in=[STATUS_QUEUED, STATUS_RUNNING],
        ):
            if not task.is_dismissed:
                count += 1
    return Response({'count': count})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notification_mark_read(request, pk):
    """
    Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
    Vai tro backend: Ham `notification_mark_read` la endpoint hoac diem vao REST cua file `api/views/notifications.py`, chiu trach nhiem doc hoac cap nhat thong bao theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can doc hoac cap nhat thong bao tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `document_templates.models`. Dung cung cap voi cac ham `notification_list`, `notification_unread_count`, `notification_mark_template_read` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac doc hoac cap nhat thong bao tren giao dien.
    """
    notification = get_object_or_404(
        TemplateReviewNotification.objects.filter(recipient=request.user),
        pk=pk,
    )
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at'])
    return Response({'status': 'ok'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notification_mark_template_read(request):
    """
    Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
    Vai tro backend: Ham `notification_mark_template_read` la endpoint hoac diem vao REST cua file `api/views/notifications.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi mau van ban theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can xu ly du lieu hoac thao tac lien quan toi mau van ban tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `document_templates.models`. Dung cung cap voi cac ham `notification_list`, `notification_unread_count`, `notification_mark_read` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac xu ly du lieu hoac thao tac lien quan toi mau van ban tren giao dien.
    """
    template_id = request.data.get('template_id')
    if not template_id:
        return Response({'detail': 'Can template_id.'}, status=400)
    updated = mark_template_notifications_read(
        recipient=request.user,
        template_id=template_id,
    )
    return Response({'updated': updated})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def aggregate_notification_list(request):
    try:
        limit = int(request.GET.get('limit', 20) or 20)
    except (TypeError, ValueError):
        limit = 20
    limit = min(max(limit, 1), 100)
    actionable_only = str(request.GET.get('actionable_only', '') or '').lower() in {'1', 'true', 'yes'}
    items = build_aggregate_notifications(
        request.user,
        limit=limit,
        actionable_only=actionable_only,
    )
    serializer = AggregateNotificationItemSerializer(items, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def aggregate_notification_unread_count(request):
    actionable_only = str(request.GET.get('actionable_only', '') or '').lower() in {'1', 'true', 'yes'}
    return Response(
        {
            'count': get_aggregate_unread_count(
                request.user,
                actionable_only=actionable_only,
            )
        }
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def aggregate_notification_mark_read(request):
    serializer = AggregateNotificationReadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    updated = mark_aggregate_notification_read(
        request.user,
        serializer.validated_data['source_type'],
        serializer.validated_data['source_id'],
    )
    if not updated:
        return Response({'detail': 'Thong bao khong ton tai hoac khong ho tro danh dau da doc.'}, status=404)
    return Response({'updated': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def aggregate_notification_mark_all_read(request):
    """Danh dau da doc tat ca thong bao tong hop cua nguoi dung hien tai."""
    updated = mark_all_aggregate_notifications_read(request.user)
    return Response({'updated': updated})

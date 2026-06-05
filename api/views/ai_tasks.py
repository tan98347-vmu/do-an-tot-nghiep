from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ai_tasks.models import AITaskProgress, STATUS_COMPLETED, STATUS_FAILED, STATUS_QUEUED, STATUS_RUNNING
from ai_tasks.services.task_runner import request_cancel
from api.serializers.ai_tasks import AITaskProgressSerializer


def _user_task_qs(user):
    if user.is_superuser:
        return AITaskProgress.objects.all()
    return AITaskProgress.objects.filter(user=user)


def _serialize_task(task: AITaskProgress) -> dict:
    return AITaskProgressSerializer(task).data


def _is_dismissed(task: AITaskProgress) -> bool:
    return task.is_dismissed


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_state(request, task_id):
    qs = _user_task_qs(request.user)
    task = get_object_or_404(qs, task_id=task_id)
    data = _serialize_task(task)
    resp = Response(data)
    resp['Cache-Control'] = 'no-store'
    return resp


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def task_cancel(request, task_id):
    qs = _user_task_qs(request.user)
    task = qs.filter(task_id=task_id).first()
    if task is None:
        return Response({'detail': 'Khong tim thay task.'}, status=status.HTTP_404_NOT_FOUND)
    if task.status in {STATUS_COMPLETED, STATUS_FAILED, 'cancelled'}:
        return Response(
            {'detail': 'Task da o trang thai ket thuc, khong the cancel.'},
            status=status.HTTP_409_CONFLICT,
        )
    ok = request_cancel(task_id)
    if not ok:
        return Response({'detail': 'Khong cancel duoc task.'}, status=status.HTTP_400_BAD_REQUEST)
    task.refresh_from_db()
    return Response(_serialize_task(task))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_inbox(request):
    qs = _user_task_qs(request.user).order_by('-created_at')
    running = list(qs.filter(status__in=[STATUS_QUEUED, STATUS_RUNNING])[:20])
    recent_candidates = list(qs.exclude(status__in=[STATUS_QUEUED, STATUS_RUNNING])[:100])
    recent_completed = [
        task
        for task in recent_candidates
        if not _is_dismissed(task)
    ][:50]
    resp = Response({
        'running': [_serialize_task(task) for task in running],
        'recent_completed': [_serialize_task(task) for task in recent_completed],
    })
    resp['Cache-Control'] = 'no-store'
    return resp


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def task_dismiss(request, task_id):
    task = _user_task_qs(request.user).filter(task_id=task_id).first()
    if task is None:
        return Response({'detail': 'Khong tim thay task.'}, status=status.HTTP_404_NOT_FOUND)
    if task.status in {STATUS_QUEUED, STATUS_RUNNING}:
        return Response(
            {'detail': 'Khong the dismiss task dang chay.'},
            status=status.HTTP_409_CONFLICT,
        )
    result = task.result if isinstance(task.result, dict) else {}
    result = {**result, 'dismissed': True}
    task.result = result
    task.save(update_fields=['result', 'updated_at'])
    return Response(status=status.HTTP_204_NO_CONTENT)

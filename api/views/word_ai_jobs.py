import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import can_edit_document, get_accessible_documents
from api.serializers.word_ai import (
    WordEditJobCreateSerializer,
    WordEditJobDetailSerializer,
    WordEditJobSerializer,
)
from word_ai.models import WordEditJob
from word_ai.services.job_create_service import create_word_edit_job
from word_ai.services.job_transition_service import mark_cancelled

logger = logging.getLogger(__name__)


def _job_queryset_for_user(user):
    accessible_documents = get_accessible_documents(user)
    return WordEditJob.objects.select_related(
        'document',
        'requested_by',
        'current_worker',
    ).prefetch_related('events').filter(document__in=accessible_documents)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def word_ai_job_list_create(request):
    if request.method == 'GET':
        qs = _job_queryset_for_user(request.user)
        document_id = request.query_params.get('document_id')
        if document_id:
            qs = qs.filter(document_id=document_id)
        try:
            limit = int(request.query_params.get('limit', 20) or 20)
        except (TypeError, ValueError):
            limit = 20
        limit = min(max(limit, 1), 100)
        return Response(WordEditJobSerializer(qs[:limit], many=True).data)

    serializer = WordEditJobCreateSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(
            'word_ai job create rejected by serializer | user_id=%s | payload=%s | errors=%s',
            getattr(request.user, 'id', None),
            request.data,
            serializer.errors,
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    try:
        job = create_word_edit_job(user=request.user, **serializer.validated_data)
    except ValidationError as exc:
        logger.warning(
            'word_ai job create rejected by service validation | user_id=%s | payload=%s | detail=%s',
            getattr(request.user, 'id', None),
            serializer.validated_data,
            exc.detail,
        )
        raise
    except PermissionDenied as exc:
        logger.warning(
            'word_ai job create rejected by permission | user_id=%s | payload=%s | detail=%s',
            getattr(request.user, 'id', None),
            serializer.validated_data,
            exc.detail,
        )
        raise
    return Response(WordEditJobDetailSerializer(job).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def word_ai_job_detail(request, pk):
    job = get_object_or_404(_job_queryset_for_user(request.user), pk=pk)
    return Response(WordEditJobDetailSerializer(job).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def word_ai_job_cancel(request, pk):
    job = get_object_or_404(_job_queryset_for_user(request.user), pk=pk)
    if not can_edit_document(request.user, job.document):
        return Response({'detail': 'You do not have permission to cancel this job.'}, status=status.HTTP_403_FORBIDDEN)
    if job.is_terminal:
        return Response(WordEditJobDetailSerializer(job).data)
    mark_cancelled(job, user=request.user)
    return Response(WordEditJobDetailSerializer(job).data)

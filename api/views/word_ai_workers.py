import json

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.serializers.documents import DocumentDetailSerializer, DocumentVersionSerializer
from api.serializers.word_ai import (
    WordEditJobCompleteSerializer,
    WordEditJobDetailSerializer,
    WordEditJobMcpAdvanceSerializer,
    WordEditJobWorkerEventSerializer,
    WordEditJobFailSerializer,
    WordWorkerClaimSerializer,
    WordWorkerHeartbeatSerializer,
    WordWorkerSerializer,
)
from api.views.word_ai_common import worker_auth_error, worker_token_is_valid
from word_ai.models import WordEditJob, WordWorker, WordWorkerStatus
from word_ai.services.commit_result_service import commit_job_result
from word_ai.services.event_log_service import append_job_event
from word_ai.services.job_claim_service import claim_next_job
from word_ai.services.job_transition_service import mark_failed, mark_in_progress
from word_ai.services.word_tool_loop_service import advance_word_tool_loop
from word_ai.services.worker_payload_service import build_worker_job_context


advance_mcp_agent = advance_word_tool_loop


def _worker_from_key(worker_key):
    return WordWorker.objects.filter(worker_key=worker_key).first()


def _coerce_form_json(raw_value, *, default):
    if isinstance(default, list) and isinstance(raw_value, list):
        return raw_value
    if isinstance(default, dict) and isinstance(raw_value, dict):
        return raw_value
    raw_text = str(raw_value or '').strip()
    if not raw_text:
        return default
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        return default
    if isinstance(default, list) and isinstance(parsed, list):
        return parsed
    if isinstance(default, dict) and isinstance(parsed, dict):
        return parsed
    return default


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def word_ai_worker_claim(request):
    if not worker_token_is_valid(request):
        return worker_auth_error()
    serializer = WordWorkerClaimSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    job, worker = claim_next_job(**serializer.validated_data)
    payload = {
        'worker': WordWorkerSerializer(worker).data,
        'job': _serialize_worker_job(job) if job else None,
    }
    return Response(payload)


def _serialize_worker_job(job):
    data = WordEditJobDetailSerializer(job).data
    data['worker_context'] = build_worker_job_context(job)
    return data


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def word_ai_worker_heartbeat(request):
    if not worker_token_is_valid(request):
        return worker_auth_error()
    serializer = WordWorkerHeartbeatSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    worker, _ = WordWorker.objects.get_or_create(
        worker_key=serializer.validated_data['worker_key'],
        defaults={'slot_label': serializer.validated_data['slot_label']},
    )
    worker.slot_label = serializer.validated_data['slot_label']
    worker.last_seen_at = timezone.now()
    worker.metadata = serializer.validated_data.get('metadata') or worker.metadata
    worker.status = serializer.validated_data.get('status') or worker.status or WordWorkerStatus.IDLE
    worker.save(update_fields=['slot_label', 'last_seen_at', 'metadata', 'status', 'updated_at'])

    current_job_id = serializer.validated_data.get('current_job_id')
    if current_job_id:
        job = WordEditJob.objects.filter(pk=current_job_id).first()
        if job:
            job.heartbeat_payload = serializer.validated_data.get('metadata') or {}
            job.save(update_fields=['heartbeat_payload', 'updated_at'])
            append_job_event(
                job,
                worker=worker,
                step='heartbeat',
                status=job.status,
                message='Worker heartbeat received.',
            )
    return Response({'ok': True, 'worker': WordWorkerSerializer(worker).data})


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def word_ai_job_complete(request, pk):
    if not worker_token_is_valid(request):
        return worker_auth_error()
    serializer = WordEditJobCompleteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    job = get_object_or_404(WordEditJob.objects.select_related('document', 'requested_by', 'current_worker'), pk=pk)
    worker = _worker_from_key(serializer.validated_data['worker_key'])
    if worker is None:
        return Response({'detail': 'Unknown worker.'}, status=status.HTTP_404_NOT_FOUND)
    version = commit_job_result(
        job=job,
        worker=worker,
        uploaded_file=serializer.validated_data['output_file'],
        summary=serializer.validated_data.get('summary', ''),
        change_note=serializer.validated_data.get('change_note', ''),
        content_text=serializer.validated_data.get('content_text', ''),
        tool_transcript=_coerce_form_json(
            serializer.validated_data.get('tool_transcript', []) or request.data.get('tool_transcript', ''),
            default=[],
        ),
        verification_summary=_coerce_form_json(
            serializer.validated_data.get('verification_summary', {}) or request.data.get('verification_summary', ''),
            default={},
        ),
        artifact_manifest=_coerce_form_json(
            serializer.validated_data.get('artifact_manifest', {}) or request.data.get('artifact_manifest', ''),
            default={},
        ),
        document_checksums=_coerce_form_json(
            serializer.validated_data.get('document_checksums', {}) or request.data.get('document_checksums', ''),
            default={},
        ),
    )
    job.refresh_from_db()
    job.document.refresh_from_db()
    payload = {
        'job': WordEditJobDetailSerializer(job).data,
        'document': DocumentDetailSerializer(job.document).data,
        'version': DocumentVersionSerializer(version).data,
    }
    return Response(payload)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def word_ai_job_fail(request, pk):
    if not worker_token_is_valid(request):
        return worker_auth_error()
    serializer = WordEditJobFailSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    job = get_object_or_404(WordEditJob, pk=pk)
    worker = _worker_from_key(serializer.validated_data['worker_key'])
    if worker is None:
        return Response({'detail': 'Unknown worker.'}, status=status.HTTP_404_NOT_FOUND)
    mark_failed(
        job,
        worker=worker,
        error_code=serializer.validated_data['error_code'],
        error_detail=serializer.validated_data.get('error_detail', ''),
        tool_transcript=serializer.validated_data.get('tool_transcript') or [],
        verification_summary=serializer.validated_data.get('verification_summary') or {},
        payload=serializer.validated_data.get('failure_payload') or {},
        step='worker',
    )
    return Response(WordEditJobDetailSerializer(job).data, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def word_ai_job_event(request, pk):
    if not worker_token_is_valid(request):
        return worker_auth_error()
    serializer = WordEditJobWorkerEventSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    job = get_object_or_404(WordEditJob, pk=pk)
    worker = _worker_from_key(serializer.validated_data['worker_key'])
    if worker is None:
        return Response({'detail': 'Unknown worker.'}, status=status.HTTP_404_NOT_FOUND)

    requested_status = serializer.validated_data.get('status', '').strip()
    if requested_status in {'claimed', 'editing', 'uploading'} and not job.is_terminal:
        mark_in_progress(
            job,
            worker=worker,
            status=requested_status,
            step=serializer.validated_data['step'],
            message=serializer.validated_data.get('message', ''),
            payload=serializer.validated_data.get('payload') or {},
            level=serializer.validated_data.get('level', 'info'),
        )
    else:
        append_job_event(
            job,
            worker=worker,
            step=serializer.validated_data['step'],
            status=requested_status or job.status,
            message=serializer.validated_data.get('message', ''),
            payload=serializer.validated_data.get('payload') or {},
            level=serializer.validated_data.get('level', 'info'),
        )
    job.refresh_from_db()
    return Response(WordEditJobDetailSerializer(job).data)


def _handle_word_ai_job_tool_loop_advance(request, pk):
    if not worker_token_is_valid(request):
        return worker_auth_error()
    serializer = WordEditJobMcpAdvanceSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    job = get_object_or_404(WordEditJob.objects.select_related('requested_by', 'document'), pk=pk)
    worker = _worker_from_key(serializer.validated_data['worker_key'])
    if worker is None:
        return Response({'detail': 'Unknown worker.'}, status=status.HTTP_404_NOT_FOUND)
    if job.mcp_session_id and serializer.validated_data['session_id'] != job.mcp_session_id:
        return Response({'detail': 'Tool-loop session id does not match the claimed job.'}, status=status.HTTP_409_CONFLICT)
    decision = advance_mcp_agent(
        job=job,
        tool_transcript=serializer.validated_data.get('tool_transcript') or [],
        latest_command=serializer.validated_data.get('latest_command') or {},
        session_snapshot=serializer.validated_data.get('session_snapshot') or {},
    )
    return Response(decision)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def word_ai_job_tool_loop_advance(request, pk):
    return _handle_word_ai_job_tool_loop_advance(request, pk)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def word_ai_job_mcp_advance(request, pk):
    return _handle_word_ai_job_tool_loop_advance(request, pk)

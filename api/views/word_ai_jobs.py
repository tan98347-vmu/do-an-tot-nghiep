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


# Là gì: `_job_queryset_for_user` là helper nội bộ của module `word_ai_jobs.py`, phục vụ nhóm tạo và theo dõi công việc chỉnh sửa Word bằng AI.
# Chức năng backend: Hàm xử lý phần việc `job queryset for user` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ bảng tiến trình chỉnh sửa Word bằng AI.
# Mối liên hệ: Hàm phối hợp với `get_accessible_documents`, `WordEditJob.objects.select_related.prefetch_related.filter`, `WordEditJob.objects.select_related.prefetch_related` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _job_queryset_for_user(user):
    accessible_documents = get_accessible_documents(user)
    return WordEditJob.objects.select_related(
        'document',
        'requested_by',
        'current_worker',
    ).prefetch_related('events').filter(document__in=accessible_documents)


# Là gì: `word_ai_job_list_create` là endpoint REST của nhóm tạo và theo dõi công việc chỉnh sửa Word bằng AI; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm truy vấn và trả về danh sách dữ liệu phù hợp, đồng thời kiểm tra đầu vào và tạo dữ liệu mới; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được bảng tiến trình chỉnh sửa Word bằng AI sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_job_queryset_for_user`, `request.query_params.get`, `qs.filter` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
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


# Là gì: `word_ai_job_detail` là endpoint REST của nhóm tạo và theo dõi công việc chỉnh sửa Word bằng AI; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm đọc hoặc xử lý một bản ghi cụ thể; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được bảng tiến trình chỉnh sửa Word bằng AI sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `get_object_or_404`, `_job_queryset_for_user`, `WordEditJobDetailSerializer` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def word_ai_job_detail(request, pk):
    job = get_object_or_404(_job_queryset_for_user(request.user), pk=pk)
    return Response(WordEditJobDetailSerializer(job).data)


# Là gì: `word_ai_job_cancel` là endpoint REST của nhóm tạo và theo dõi công việc chỉnh sửa Word bằng AI; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm yêu cầu dừng một tiến trình đang chờ hoặc đang chạy; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được bảng tiến trình chỉnh sửa Word bằng AI sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `get_object_or_404`, `_job_queryset_for_user`, `can_edit_document` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
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

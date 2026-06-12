from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ai_tasks.models import AITaskProgress, STATUS_COMPLETED, STATUS_FAILED, STATUS_QUEUED, STATUS_RUNNING
from ai_tasks.services.task_runner import request_cancel
from api.serializers.ai_tasks import AITaskProgressSerializer


# Là gì: `_user_task_qs` là helper nội bộ của module `ai_tasks.py`, phục vụ nhóm theo dõi, hủy và nhận kết quả các tác vụ AI chạy nền.
# Chức năng backend: Hàm xử lý phần việc `user task qs` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ hộp tiến trình và danh sách tác vụ AI trên Flutter.
# Mối liên hệ: Hàm phối hợp với `AITaskProgress.objects.all`, `AITaskProgress.objects.filter` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
# cụ thể hàm này nhận vào một đối tượng người dùng và trả về một queryset của các tác vụ AI (AITaskProgress) liên quan đến người dùng đó. Nếu người dùng là superuser, nó sẽ trả về tất cả các tác vụ; nếu không, nó sẽ chỉ trả về các tác vụ mà người dùng đó sở hữu. Hàm này giúp chuẩn hóa cách truy vấn các tác vụ AI dựa trên quyền hạn của người dùng, đảm bảo rằng các endpoint khác trong module có thể dễ dàng lấy được dữ liệu phù hợp với ngữ cảnh của người dùng hiện tại.
# vd: khi một endpoint cần lấy danh sách các tác vụ AI của người dùng hiện tại, nó có thể gọi _user_task_qs(request.user) để nhận được queryset đã được lọc sẵn, từ đó có thể tiếp tục áp dụng các bộ lọc hoặc sắp xếp khác nếu cần.
def _user_task_qs(user):
    if user.is_superuser:
        return AITaskProgress.objects.all()
    return AITaskProgress.objects.filter(user=user)

# cụ thể hàm này giúp chuẩn hóa cách truy vấn các tác vụ AI dựa trên quyền hạn của người dùng, đảm bảo rằng các endpoint khác trong module có thể dễ dàng lấy được dữ liệu phù hợp với ngữ cảnh của người dùng hiện tại.
# vd: khi một endpoint cần lấy danh sách các tác vụ AI của người dùng hiện tại, nó có thể gọi _user_task_qs(request.user) để nhận được queryset đã được lọ
# Là gì: `_serialize_task` là helper nội bộ của module `ai_tasks.py`, phục vụ nhóm theo dõi, hủy và nhận kết quả các tác vụ AI chạy nền.
# Chức năng backend: Hàm chuyển đối tượng nội bộ thành dữ liệu có thể trả cho client; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ hộp tiến trình và danh sách tác vụ AI trên Flutter.
# Mối liên hệ: Hàm phối hợp với `AITaskProgressSerializer` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _serialize_task(task: AITaskProgress) -> dict:
    return AITaskProgressSerializer(task).data

# cụ thể hàm này nhận vào một đối tượng AITaskProgress và sử dụng AITaskProgressSerializer để chuyển đổi nó thành một dictionary có thể trả về cho client. Hàm này giúp chuẩn hóa cách dữ liệu của tác vụ AI được trình bày trong các endpoint, đảm bảo rằng tất cả các endpoint sử dụng cùng một định dạng dữ liệu khi trả về thông tin về tác vụ AI cho Flutter.
# vd: khi một endpoint cần trả về thông tin chi tiết của một tác vụ AI, nó có thể gọi _serialize_task(task) để nhận được một dictionary đã được chuẩn hóa, từ
# Là gì: `_is_dismissed` là helper nội bộ của module `ai_tasks.py`, phục vụ nhóm theo dõi, hủy và nhận kết quả các tác vụ AI chạy nền.
# Chức năng backend: Hàm đánh giá một điều kiện và trả về kết quả boolean; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ hộp tiến trình và danh sách tác vụ AI trên Flutter.
# Mối liên hệ: Hàm được các endpoint hoặc helper cùng module gọi khi cần cùng quy tắc xử lý.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _is_dismissed(task: AITaskProgress) -> bool:
    return task.is_dismissed


# Là gì: `task_state` là endpoint REST của nhóm theo dõi, hủy và nhận kết quả các tác vụ AI chạy nền; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xử lý phần việc `task state` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được hộp tiến trình và danh sách tác vụ AI trên Flutter sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_user_task_qs`, `get_object_or_404`, `_serialize_task` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_state(request, task_id):
    qs = _user_task_qs(request.user)
    task = get_object_or_404(qs, task_id=task_id)
    data = _serialize_task(task)
    resp = Response(data)
    resp['Cache-Control'] = 'no-store'
    return resp


# Là gì: `task_cancel` là endpoint REST của nhóm theo dõi, hủy và nhận kết quả các tác vụ AI chạy nền; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm yêu cầu dừng một tiến trình đang chờ hoặc đang chạy; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được hộp tiến trình và danh sách tác vụ AI trên Flutter sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_user_task_qs`, `qs.filter.first`, `qs.filter` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
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


# Là gì: `task_inbox` là endpoint REST của nhóm theo dõi, hủy và nhận kết quả các tác vụ AI chạy nền; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xử lý phần việc `task inbox` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được hộp tiến trình và danh sách tác vụ AI trên Flutter sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_user_task_qs.order_by`, `_user_task_qs`, `qs.filter` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
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


# Là gì: `task_dismiss` là endpoint REST của nhóm theo dõi, hủy và nhận kết quả các tác vụ AI chạy nền; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm ẩn hoặc đánh dấu đã xử lý một mục khỏi giao diện; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được hộp tiến trình và danh sách tác vụ AI trên Flutter sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_user_task_qs.filter.first`, `_user_task_qs.filter`, `_user_task_qs` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; có side effect ghi cơ sở dữ liệu; chuyển kết quả thành HTTP response.
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

from django.conf import settings
from rest_framework.response import Response
from rest_framework import status


# Là gì: `worker_token_is_valid` là hàm điều phối nghiệp vụ của module `word_ai_common.py`, thuộc nhóm xác thực và dữ liệu dùng chung cho tiến trình chỉnh sửa Word bằng AI.
# Chức năng backend: Hàm đánh giá một điều kiện và trả về kết quả boolean; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ luồng chỉnh sửa văn bản bằng AI.
# Mối liên hệ: Hàm phối hợp với `request.headers.get` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def worker_token_is_valid(request):
    expected = getattr(settings, 'WORD_AI_LOCAL_AGENT_TOKEN', '')
    provided = request.headers.get('X-Word-AI-Worker-Token', '')
    return bool(expected) and provided == expected


# Là gì: `worker_auth_error` là hàm điều phối nghiệp vụ của module `word_ai_common.py`, thuộc nhóm xác thực và dữ liệu dùng chung cho tiến trình chỉnh sửa Word bằng AI.
# Chức năng backend: Hàm xử lý phần việc `worker auth error` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ luồng chỉnh sửa văn bản bằng AI.
# Mối liên hệ: Hàm được các endpoint hoặc helper cùng module gọi khi cần cùng quy tắc xử lý.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
def worker_auth_error():
    return Response({'detail': 'Invalid worker token.'}, status=status.HTTP_403_FORBIDDEN)

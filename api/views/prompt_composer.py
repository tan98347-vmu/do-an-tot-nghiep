from __future__ import annotations

from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from prompts.models import Prompt
from prompts.services.composer import ALLOWED_COMPOSE_SCOPES, compose_prompt


# class ComposerThrottle là lớp giới hạn tần suất gọi (rate limit).
# vd: gom các thuộc tính/method liên quan vào một nơi.
class ComposerThrottle(UserRateThrottle):
    rate = '60/min'


# Là gì: `prompt_compose_preview` là endpoint REST của nhóm ghép và xem trước prompt từ nhiều lớp cấu hình; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm tạo dữ liệu xem trước mà chưa ghi nhận thay đổi cuối cùng; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được hộp thoại xem trước prompt sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `str.strip`, `request.data.get`, `compose_prompt` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ComposerThrottle])
def prompt_compose_preview(request):
    scope = str(request.data.get('scope') or '').strip()
    if scope not in ALLOWED_COMPOSE_SCOPES:
        return Response(
            {'detail': f'scope phải thuộc {list(ALLOWED_COMPOSE_SCOPES)}'},
            status=400,
        )

    raw_base_prompt_id = request.data.get('base_prompt_id')
    base_prompt_id = None
    if raw_base_prompt_id not in (None, ''):
        try:
            base_prompt_id = int(raw_base_prompt_id)
        except (TypeError, ValueError):
            return Response({'detail': 'base_prompt_id không hợp lệ.'}, status=400)

    try:
        result = compose_prompt(
            base_prompt_id=base_prompt_id,
            scope=scope,
            options=request.data.get('options') or {},
            extra_user_text=request.data.get('extra_user_text') or '',
            user=request.user,
        )
    except Prompt.DoesNotExist:
        return Response({'detail': 'base_prompt_id không tồn tại.'}, status=400)
    except PermissionError as exc:
        return Response({'detail': str(exc)}, status=403)
    return Response(result)

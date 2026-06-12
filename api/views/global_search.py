import time

from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from api.serializers.global_search import (
    GlobalSearchQuerySerializer,
    GlobalSearchResponseSerializer,
)
from document_templates.search_helpers import search_templates
from documents.search_helpers import search_documents
from prompts.search_helpers import search_prompts


# class SearchThrottle là lớp giới hạn tần suất gọi (rate limit).
# vd: gom các thuộc tính/method liên quan vào một nơi.
class SearchThrottle(UserRateThrottle):
    rate = '60/min'


# Là gì: `global_search` là endpoint REST của nhóm tìm kiếm hợp nhất trên các tài nguyên người dùng được phép truy cập; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm tìm kiếm và lọc các bản ghi phù hợp; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được ô tìm kiếm toàn cục sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `GlobalSearchQuerySerializer`, `serializer.is_valid`, `time.monotonic` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([SearchThrottle])
def global_search(request):
    serializer = GlobalSearchQuerySerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)

    query = serializer.validated_data['q']
    search_types = serializer.validated_data['types']
    started_at = time.monotonic()

    results = {}
    for search_type in search_types:
        if search_type == 'template':
            results['template'] = search_templates(request.user, query, limit=5)
        elif search_type == 'document':
            results['document'] = search_documents(request.user, query, limit=5)
        elif search_type == 'prompt':
            results['prompt'] = search_prompts(request.user, query, limit=5)
        elif search_type == 'summary':
            results['summary'] = []
        elif search_type == 'conversation':
            results['conversation'] = []

    payload = {
        'results': results,
        'took_ms': int((time.monotonic() - started_at) * 1000),
    }
    response_serializer = GlobalSearchResponseSerializer(payload)
    return Response(response_serializer.data)

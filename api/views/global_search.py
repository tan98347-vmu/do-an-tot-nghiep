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


class SearchThrottle(UserRateThrottle):
    rate = '60/min'


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

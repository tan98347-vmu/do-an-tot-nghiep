from __future__ import annotations

from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from prompts.models import Prompt
from prompts.services.composer import ALLOWED_COMPOSE_SCOPES, compose_prompt


class ComposerThrottle(UserRateThrottle):
    rate = '60/min'


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

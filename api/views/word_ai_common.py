from django.conf import settings
from rest_framework.response import Response
from rest_framework import status


def worker_token_is_valid(request):
    expected = getattr(settings, 'WORD_AI_LOCAL_AGENT_TOKEN', '')
    provided = request.headers.get('X-Word-AI-Worker-Token', '')
    return bool(expected) and provided == expected


def worker_auth_error():
    return Response({'detail': 'Invalid worker token.'}, status=status.HTTP_403_FORBIDDEN)

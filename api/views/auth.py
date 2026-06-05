from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import CompanyStatus, CompanyUserMembership
from accounts.tenancy import (
    build_effective_ai_context,
    get_user_membership,
    is_platform_admin,
    resolve_company,
    resolve_company_login,
)
from ..serializers.auth import UserMeUpdateSerializer, UserSerializer


def _ensure_signing_credential(user: User) -> None:
    try:
        from signing.internal_pki import ensure_user_signing_credential

        ensure_user_signing_credential(user)
    except Exception:
        pass


def _serialize_login(user: User, *, membership=None) -> Response:
    if membership is not None:
        membership.last_login_at = timezone.now()
        membership.save(update_fields=['last_login_at'])
    _ensure_signing_credential(user)
    refresh = RefreshToken.for_user(user)
    return Response(
        {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        }
    )


def _company_login_identifier_matches(identifier: str):
    if not identifier:
        return CompanyUserMembership.objects.none()
    return CompanyUserMembership.objects.select_related('user', 'company').filter(
        is_active=True,
        company__status=CompanyStatus.ACTIVE,
    ).filter(
        models.Q(local_username__iexact=identifier)
        | models.Q(user__username__iexact=identifier)
        | models.Q(user__email__iexact=identifier)
        | models.Q(user__profile__ma_nhan_vien__iexact=identifier)
    ).distinct()


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    return Response(
        {'detail': 'Dang ky tu do da bi tat trong phien ban multi-company.'},
        status=status.HTTP_403_FORBIDDEN,
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    identifier = str(
        request.data.get('identifier')
        or request.data.get('username')
        or request.data.get('email')
        or ''
    ).strip()
    password = str(request.data.get('password') or '')
    login_scope = str(request.data.get('login_scope') or '').strip().lower()
    company_id = request.data.get('company_id')

    if not identifier or not password:
        return Response(
            {'detail': 'Can nhap day du thong tin dang nhap.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if login_scope == 'platform':
        user = authenticate(username=identifier, password=password)
        if not user or not is_platform_admin(user):
            return Response(
                {'detail': 'Tai khoan quan tri nen tang hoac mat khau khong dung.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_active:
            return Response({'detail': 'Tai khoan da bi vo hieu hoa.'}, status=status.HTTP_401_UNAUTHORIZED)
        return _serialize_login(user)

    if login_scope == 'company' or company_id:
        company = resolve_company(company_id)
        if company is None:
            return Response({'detail': 'Can chon cong ty hop le.'}, status=status.HTTP_400_BAD_REQUEST)
        if company.status != CompanyStatus.ACTIVE:
            return Response({'detail': 'Cong ty hien khong cho phep dang nhap.'}, status=status.HTTP_403_FORBIDDEN)
        match = resolve_company_login(identifier, password, company)
        if match is None:
            return Response(
                {'detail': 'Thong tin dang nhap khong dung hoac ban dang chon sai cong ty.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return _serialize_login(match.user, membership=match.membership)

    platform_user = authenticate(username=identifier, password=password)
    if platform_user and is_platform_admin(platform_user) and platform_user.is_active:
        return _serialize_login(platform_user)

    matches = list(_company_login_identifier_matches(identifier))
    valid_matches = [
        membership
        for membership in matches
        if membership.user.is_active and membership.user.check_password(password)
    ]
    if len(valid_matches) == 1:
        return _serialize_login(valid_matches[0].user, membership=valid_matches[0])
    if len(valid_matches) > 1:
        return Response(
            {
                'detail': 'Tai khoan nay ton tai o nhieu cong ty. Hay chon cong ty truoc khi dang nhap.',
                'requires_company': True,
                'companies': [
                    {
                        'id': membership.company_id,
                        'code': membership.company.code,
                        'name': membership.company.name,
                        'slug': membership.company.slug,
                    }
                    for membership in valid_matches
                ],
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {'detail': 'Thong tin dang nhap khong dung.'},
        status=status.HTTP_401_UNAUTHORIZED,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            RefreshToken(refresh_token).blacklist()
    except TokenError:
        pass
    return Response({'detail': 'Da dang xuat.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def prefill_from_bio(request):
    from ai_engine.doc_creator import _extract_json_object, _repair_json
    from ai_engine.rag_engine import get_llm
    from langchain_core.messages import HumanMessage, SystemMessage
    import json as _json

    bio_text = str(request.data.get('biography_text') or '').strip()
    if not bio_text:
        return Response({'fields': {}})

    system_prompt = (
        'Ban la tro ly trich xuat thong tin ca nhan tu ho so nhan su.\n'
        'Chi tra ve JSON thuong, khong them giai thich.\n'
        "Neu khong co du lieu thi de chuoi rong ''."
    )
    effective_context = build_effective_ai_context(user=request.user).strip()
    human_prompt = (
        f'NGU CANH HE THONG:\n{effective_context[:3000]}\n\n'
        f'HO SO:\n{bio_text[:5000]}\n\n'
        'Trich xuat cac truong:\n'
        '- first_name\n'
        '- last_name\n'
        '- chuc_danh\n'
        '- ma_nhan_vien\n'
        '- cccd\n'
        '- ngay_sinh (YYYY-MM-DD)\n'
        '- email\n\n'
        '- so_dien_thoai\n'
        '- dia_chi\n\n'
        'Tra ve JSON: {"first_name":"","last_name":"","chuc_danh":"","ma_nhan_vien":"","cccd":"","ngay_sinh":"","email":"","so_dien_thoai":"","dia_chi":""}'
    )

    try:
        llm = get_llm(request.user)
        resp = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)])
        raw = resp.content.strip()
        extracted = _json.loads(_repair_json(_extract_json_object(raw)))
        fields = ['first_name', 'last_name', 'chuc_danh', 'ma_nhan_vien', 'cccd', 'ngay_sinh', 'email', 'so_dien_thoai', 'dia_chi']
        return Response({'fields': {field: str(extracted.get(field, '') or '') for field in fields}})
    except Exception as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def social_google(request):
    return Response(
        {'detail': 'Dang nhap Google da bi tat trong phien ban multi-company.'},
        status=status.HTTP_403_FORBIDDEN,
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def social_facebook(request):
    return Response(
        {'detail': 'Dang nhap Facebook da bi tat trong phien ban multi-company.'},
        status=status.HTTP_403_FORBIDDEN,
    )


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def me(request):
    if request.method == 'GET':
        _ensure_signing_credential(request.user)
        return Response(UserSerializer(request.user).data)

    serializer = UserMeUpdateSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    serializer.update(request.user, serializer.validated_data)
    membership = get_user_membership(request.user)
    if membership and membership.must_change_password and request.data.get('password'):
        membership.must_change_password = False
        membership.save(update_fields=['must_change_password'])
    return Response(UserSerializer(request.user).data)

"""
Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
Vai tro backend: File `api/views/signing.py` giu hoac ho tro luong backend cho de xuat ky, packet ky, nhiem vu ky, xac minh PDF, PKI noi bo va quyen uy quyen.
Vai tro cua no trong frontend: Cac man `/signing/tasks`, `/signed-pdfs`, `/signing/access` va mot phan thao tac o `/mailbox` phu thuoc truc tiep hoac gian tiep vao file nay.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`.
Tac dung: Giu cho quy trinh ky nhieu buoc, trang thai chu ky va kiem tra toan ven PDF nhat quan giua nguoi de xuat, nguoi ky va man tra cuu.
"""

import logging

from django.contrib.auth.models import User
from django.db import models
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import get_accessible_documents
from accounts.runtime_guard import CompanyRuntimeGuard
from accounts.tenancy import get_user_company
from accounts.user_resolution import get_company_recipient_by_id, search_recipient_candidates
from api.serializers.signing import (
    DepartmentDelegationCreateSerializer,
    DepartmentDelegationSerializer,
    SignedPdfDocumentSerializer,
    SigningCandidateSerializer,
    SigningProposalCreateSerializer,
    SigningProposalSerializer,
    SigningTaskSerializer,
)
from signing.assistant_quick_sign import (
    AssistantQuickSignError,
    build_quick_sign_plan_payload,
    cancel_quick_sign_plan,
    execute_quick_sign_and_forward,
    get_latest_quick_sign_plan,
    prepare_quick_sign_plan,
    refresh_quick_sign_plan,
    update_quick_sign_plan_recipient,
)
from signing.models import (
    DELEGATION_APPROVE_PROPOSAL,
    DELEGATION_VIEW_SIGNED_PDF,
    AssistantQuickSignPlan,
    DepartmentDelegation,
    is_internal_approval_status,
    normalize_signature_mode,
    normalize_verification_status,
)
from signing.permissions import (
    can_manage_accounting_delegations,
    can_manage_hr_delegations,
    can_review_signing_proposals,
    get_special_department_members_qs,
    can_view_signed_pdf,
    can_view_signing_packet,
    get_accessible_signed_pdfs,
    get_accessible_signing_tasks,
    get_accounting_department,
    get_accounting_group,
    get_hr_department,
    get_hr_group,
    get_hr_reviewer_users_qs,
    is_special_department_member,
    get_pending_hr_proposals,
    get_signing_summary,
)
from signing.services import (
    SigningFlowError,
    approve_signing_proposal,
    create_signing_proposal,
    ensure_signed_pdf_integrity,
    get_signature_context_for_task,
    get_signed_pdf_integrity_report,
    reject_signing_proposal,
    reject_task,
    sign_task,
    start_signing_flow,
)

logger = logging.getLogger('signing')

def _signing_flow_error_response(exc):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_signing_flow_error_response` la helper noi bo cua lop API trong file `api/views/signing.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai truoc khi endpoint chinh phan hoi.
    Vai tro cua no trong frontend: Frontend Flutter khong goi truc tiep helper nay; endpoint cung file dung no khi giao dien can thuc hien phan xu ly chuyen trach cua symbol hien tai nhung khong nen tu xu ly o client.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `signing_summary`, `signing_candidates`, `document_signing_start` goi lai.
    Tac dung: Co lap rieng buoc thuc hien phan xu ly chuyen trach cua symbol hien tai de cac endpoint cung file tai su dung dung mot quy tac.
    """
    detail = str(exc)
    if detail.startswith('May chu chua san sang cho ky PDF PKI'):
        return Response(
            {'detail': detail, 'code': 'pki_dependencies_missing'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    if detail.startswith('Cau hinh ky PDF PKI chua san sang') or detail.startswith('Remote HSM'):
        return Response(
            {'detail': detail, 'code': 'remote_hsm_unavailable'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)

def _resolve_signers(payload, *, request_user=None):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_resolve_signers` la helper noi bo cua lop API trong file `api/views/signing.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai truoc khi endpoint chinh phan hoi.
    Vai tro cua no trong frontend: Frontend Flutter khong goi truc tiep helper nay; endpoint cung file dung no khi giao dien can thuc hien phan xu ly chuyen trach cua symbol hien tai nhung khong nen tu xu ly o client.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `signing_summary`, `signing_candidates`, `document_signing_start` goi lai.
    Tac dung: Co lap rieng buoc thuc hien phan xu ly chuyen trach cua symbol hien tai de cac endpoint cung file tai su dung dung mot quy tac.
    """
    serializer = SigningProposalCreateSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    signers_payload = serializer.validated_data['signers']
    user_ids = sorted({item['user_id'] for item in signers_payload})
    user_qs = User.objects.filter(id__in=user_ids, is_active=True)
    company = get_user_company(request_user)
    if company is not None:
        user_qs = user_qs.filter(company_membership__company=company, company_membership__is_active=True)
    users = {user.id: user for user in user_qs.distinct()}
    signers = []
    for item in signers_payload:
        signer_user = users.get(item['user_id'])
        if signer_user is None:
            raise SigningFlowError('Danh sach nguoi ky co tai khoan khong ton tai hoac da bi khoa.')
        signers.append({
            'user': signer_user,
            'display_role': item['display_role'],
            'step_no': item.get('step_no', 1),
            'required': item.get('required', True),
            'group_context': item.get('group_context', ''),
        })
    return serializer.validated_data['proposal_note'], signers

def _multi_value_query_param(request, key):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_multi_value_query_param` la helper noi bo cua lop API trong file `api/views/signing.py`, chiu trach nhiem tim kiem hoac loc du lieu theo cau hoi dau vao truoc khi endpoint chinh phan hoi.
    Vai tro cua no trong frontend: Frontend Flutter khong goi truc tiep helper nay; endpoint cung file dung no khi giao dien can tim kiem hoac loc du lieu theo cau hoi dau vao nhung khong nen tu xu ly o client.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `signing_summary`, `signing_candidates`, `document_signing_start` goi lai.
    Tac dung: Co lap rieng buoc tim kiem hoac loc du lieu theo cau hoi dau vao de cac endpoint cung file tai su dung dung mot quy tac.
    """
    values = []
    for raw_value in request.GET.getlist(key):
        for item in str(raw_value or '').split(','):
            cleaned = item.strip()
            if cleaned:
                values.append(cleaned)
    return values


def _assistant_quick_sign_error_response(exc, *, plan=None):
    payload = {
        'detail': exc.message,
        'code': exc.code,
    }
    if plan is not None:
        payload['plan'] = build_quick_sign_plan_payload(plan)
        payload['partial_result'] = plan.status == AssistantQuickSignPlan.Status.PARTIAL
    return Response(payload, status=exc.http_status)


def _quick_sign_plan_or_404(token, user):
    company = get_user_company(user)
    queryset = AssistantQuickSignPlan.objects.select_related(
        'document',
        'created_by',
        'recipient_user',
        'signing_task',
        'signing_packet',
        'signed_pdf',
        'mailbox_thread',
    ).filter(created_by=user)
    if company is not None:
        queryset = queryset.filter(company=company)
    return get_object_or_404(queryset, token=token)


def _assistant_candidate_payloads(request):
    candidates = search_recipient_candidates(
        request.GET.get('q') or '',
        company=get_user_company(request.user),
        actor=request.user,
        limit=20,
        department_hint=request.GET.get('department_hint') or '',
        title_hint=request.GET.get('title_hint') or '',
        exclude_self=False,
    )
    return [
        {
            'id': item['user_id'],
            'username': item.get('username', ''),
            'full_name': item.get('display_name', ''),
            'title': item.get('title', ''),
            'groups': [],
            'managed_departments': [],
            'departments': (
                [{'id': None, 'name': item['department'], 'code': ''}]
                if item.get('department')
                else []
            ),
            'employee_code': item.get('employee_code', ''),
            'aliases': item.get('aliases', []),
            'department': item.get('department', ''),
            'match_reason': item.get('match_reason', ''),
            'confidence': item.get('confidence', 0),
        }
        for item in candidates
    ]

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def signing_summary(request):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `signing_summary` la endpoint hoac diem vao REST cua file `api/views/signing.py`, chiu trach nhiem tong hop so lieu tom tat theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can tong hop so lieu tom tat tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_flow_error_response`, `_resolve_signers`, `_multi_value_query_param` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac tong hop so lieu tom tat tren giao dien.
    """
    return Response(get_signing_summary(request.user))

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def signing_candidates(request):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `signing_candidates` la endpoint hoac diem vao REST cua file `api/views/signing.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can thuc hien phan xu ly chuyen trach cua symbol hien tai tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_flow_error_response`, `_resolve_signers`, `_multi_value_query_param` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac thuc hien phan xu ly chuyen trach cua symbol hien tai tren giao dien.
    """
    q = (request.GET.get('q') or '').strip().lower()
    permission_type = (request.GET.get('permission_type') or '').strip()
    if q and not permission_type:
        return Response(_assistant_candidate_payloads(request))
    company = get_user_company(request.user)
    users = User.objects.filter(is_active=True)
    if company is not None:
        users = users.filter(company_membership__company=company, company_membership__is_active=True)
    if permission_type == DELEGATION_APPROVE_PROPOSAL:
        if not can_manage_hr_delegations(request.user):
            return Response({'detail': 'Ban khong the xem danh sach uy quyen duyet de xuat ky.'}, status=status.HTTP_403_FORBIDDEN)
        users = get_special_department_members_qs(get_hr_department(request.user), get_hr_group(request.user))
    elif permission_type == DELEGATION_VIEW_SIGNED_PDF:
        if not can_manage_accounting_delegations(request.user):
            return Response({'detail': 'Ban khong the xem danh sach uy quyen PDF da ky.'}, status=status.HTTP_403_FORBIDDEN)
        users = get_special_department_members_qs(get_accounting_department(request.user), get_accounting_group(request.user))
    if q:
        users = users.filter(
            models.Q(username__icontains=q)
            | models.Q(first_name__icontains=q)
            | models.Q(last_name__icontains=q)
        )
    users = users.select_related('profile').prefetch_related('managed_departments', 'department_memberships__department')
    return Response(SigningCandidateSerializer(users.order_by('first_name', 'last_name', 'username')[:100], many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def signing_quick_sign_plan_update_recipient(request, plan_token):
    plan = _quick_sign_plan_or_404(plan_token, request.user)
    try:
        recipient_id = int(request.data.get('user_id') or 0)
    except (TypeError, ValueError):
        recipient_id = 0
    recipient = get_company_recipient_by_id(get_user_company(request.user), recipient_id)
    if recipient is None:
        return Response(
            {
                'detail': 'Khong tim thay nguoi nhan hop le trong cong ty hien tai.',
                'code': 'recipient_not_found',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        plan = update_quick_sign_plan_recipient(plan, request.user, recipient)
    except AssistantQuickSignError as exc:
        return _assistant_quick_sign_error_response(exc, plan=plan)
    return Response(
        {
            'plan': build_quick_sign_plan_payload(plan),
        }
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def signing_quick_sign_plan_execute(request, plan_token):
    plan = _quick_sign_plan_or_404(plan_token, request.user)
    try:
        plan = execute_quick_sign_and_forward(
            plan,
            request.user,
            reauth_password=str(request.data.get('reauth_password') or ''),
        )
    except AssistantQuickSignError as exc:
        plan.refresh_from_db()
        return _assistant_quick_sign_error_response(exc, plan=plan)
    return Response(
        {
            'status': plan.status,
            'message': build_quick_sign_plan_payload(plan)['message'],
            'document_id': plan.document_id,
            'signed_pdf_id': plan.signed_pdf_id,
            'mailbox_thread_id': plan.mailbox_thread_id,
            'recipient_user_id': plan.recipient_user_id,
            'partial_result': False,
            'plan': build_quick_sign_plan_payload(plan),
        }
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def signing_quick_sign_plan_dismiss(request, plan_token):
    plan = _quick_sign_plan_or_404(plan_token, request.user)
    try:
        plan = cancel_quick_sign_plan(plan, request.user)
    except AssistantQuickSignError as exc:
        return _assistant_quick_sign_error_response(exc, plan=plan)
    return Response({'status': plan.status})

def _start_signing_flow_response(request, pk):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_start_signing_flow_response` la helper noi bo cua lop API trong file `api/views/signing.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai truoc khi endpoint chinh phan hoi.
    Vai tro cua no trong frontend: Frontend Flutter khong goi truc tiep helper nay; endpoint cung file dung no khi giao dien can thuc hien phan xu ly chuyen trach cua symbol hien tai nhung khong nen tu xu ly o client.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `signing_summary`, `signing_candidates`, `document_signing_start` goi lai.
    Tac dung: Co lap rieng buoc thuc hien phan xu ly chuyen trach cua symbol hien tai de cac endpoint cung file tai su dung dung mot quy tac.
    """
    document = get_object_or_404(get_accessible_documents(request.user), pk=pk)
    try:
        proposal_note, signers = _resolve_signers(request.data, request_user=request.user)
        proposal, packet = start_signing_flow(document, request.user, signers, proposal_note=proposal_note)
    except SigningFlowError as exc:
        return _signing_flow_error_response(exc)
    except Exception as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    logger.info(
        'signing flow started directly | proposal_id=%s | packet_id=%s | document_id=%s | signers=%s',
        proposal.pk,
        packet.pk,
        document.pk,
        [
            {
                'user_id': signer['user'].id,
                'username': signer['user'].username,
                'display_role': signer['display_role'],
                'step_no': signer['step_no'],
            }
            for signer in signers
        ],
    )
    serializer = SigningProposalSerializer(proposal, context={'request': request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def document_signing_start(request, pk):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `document_signing_start` la endpoint hoac diem vao REST cua file `api/views/signing.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi van ban theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can xu ly du lieu hoac thao tac lien quan toi van ban tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_flow_error_response`, `_resolve_signers`, `_multi_value_query_param` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac xu ly du lieu hoac thao tac lien quan toi van ban tren giao dien.
    """
    return _start_signing_flow_response(request, pk)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def document_signing_proposal_create(request, pk):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `document_signing_proposal_create` la endpoint hoac diem vao REST cua file `api/views/signing.py`, chiu trach nhiem tao moi ban ghi hoac khoi tao mot luong xu ly theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can tao moi ban ghi hoac khoi tao mot luong xu ly tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_flow_error_response`, `_resolve_signers`, `_multi_value_query_param` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac tao moi ban ghi hoac khoi tao mot luong xu ly tren giao dien.
    """
    return _start_signing_flow_response(request, pk)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def signing_pending_hr_proposals(request):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `signing_pending_hr_proposals` la endpoint hoac diem vao REST cua file `api/views/signing.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can thuc hien phan xu ly chuyen trach cua symbol hien tai tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_flow_error_response`, `_resolve_signers`, `_multi_value_query_param` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac thuc hien phan xu ly chuyen trach cua symbol hien tai tren giao dien.
    """
    if not can_review_signing_proposals(request.user):
        logger.warning(
            'signing pending_hr denied | user_id=%s | hr_department=%s | hr_group=%s',
            request.user.id,
            getattr(get_hr_department(request.user), 'name', None),
            getattr(get_hr_group(request.user), 'name', None),
        )
        return Response({'detail': 'Ban khong co quyen duyet de xuat ky.'}, status=status.HTTP_403_FORBIDDEN)
    proposals = get_pending_hr_proposals(request.user)
    return Response(SigningProposalSerializer(proposals, many=True).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def signing_proposal_approve(request, proposal_id):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `signing_proposal_approve` la endpoint hoac diem vao REST cua file `api/views/signing.py`, chiu trach nhiem duyet mot yeu cau nghiep vu theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can duyet mot yeu cau nghiep vu tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_flow_error_response`, `_resolve_signers`, `_multi_value_query_param` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac duyet mot yeu cau nghiep vu tren giao dien.
    """
    if not can_review_signing_proposals(request.user):
        return Response({'detail': 'Ban khong co quyen duyet de xuat ky.'}, status=status.HTTP_403_FORBIDDEN)
    proposal = get_object_or_404(get_pending_hr_proposals(request.user), pk=proposal_id)
    note = str(request.data.get('review_note') or '').strip()
    try:
        approve_signing_proposal(proposal, request.user, note)
    except SigningFlowError as exc:
        return _signing_flow_error_response(exc)
    proposal.refresh_from_db()
    return Response(SigningProposalSerializer(proposal, context={'request': request}).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def signing_proposal_reject(request, proposal_id):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `signing_proposal_reject` la endpoint hoac diem vao REST cua file `api/views/signing.py`, chiu trach nhiem tu choi mot yeu cau nghiep vu theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can tu choi mot yeu cau nghiep vu tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_flow_error_response`, `_resolve_signers`, `_multi_value_query_param` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac tu choi mot yeu cau nghiep vu tren giao dien.
    """
    if not can_review_signing_proposals(request.user):
        return Response({'detail': 'Ban khong co quyen duyet de xuat ky.'}, status=status.HTTP_403_FORBIDDEN)
    proposal = get_object_or_404(get_pending_hr_proposals(request.user), pk=proposal_id)
    note = str(request.data.get('review_note') or '').strip()
    if not note:
        return Response({'detail': 'Phai co ly do tu choi de xuat ky.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        reject_signing_proposal(proposal, request.user, note)
    except SigningFlowError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(SigningProposalSerializer(proposal, context={'request': request}).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def signing_tasks(request):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `signing_tasks` la endpoint hoac diem vao REST cua file `api/views/signing.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can thuc hien phan xu ly chuyen trach cua symbol hien tai tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_flow_error_response`, `_resolve_signers`, `_multi_value_query_param` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac thuc hien phan xu ly chuyen trach cua symbol hien tai tren giao dien.
    """
    tasks = get_accessible_signing_tasks(request.user).order_by('status', 'step_no', 'sort_order', 'id')
    return Response(SigningTaskSerializer(tasks, many=True).data)

def _get_accessible_task_or_404(user, task_id):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_get_accessible_task_or_404` la helper noi bo cua lop API trong file `api/views/signing.py`, chiu trach nhiem danh gia pham vi quyen truy cap truoc khi endpoint chinh phan hoi.
    Vai tro cua no trong frontend: Frontend Flutter khong goi truc tiep helper nay; endpoint cung file dung no khi giao dien can danh gia pham vi quyen truy cap nhung khong nen tu xu ly o client.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `signing_summary`, `signing_candidates`, `document_signing_start` goi lai.
    Tac dung: Co lap rieng buoc danh gia pham vi quyen truy cap de cac endpoint cung file tai su dung dung mot quy tac.
    """
    return get_object_or_404(get_accessible_signing_tasks(user), pk=task_id)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def signing_task_detail(request, task_id):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `signing_task_detail` la endpoint hoac diem vao REST cua file `api/views/signing.py`, chiu trach nhiem tra du lieu chi tiet cho mot doi tuong cu the theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can tra du lieu chi tiet cho mot doi tuong cu the tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_flow_error_response`, `_resolve_signers`, `_multi_value_query_param` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac tra du lieu chi tiet cho mot doi tuong cu the tren giao dien.
    """
    task = _get_accessible_task_or_404(request.user, task_id)
    if task.opened_at is None:
        task.opened_at = timezone.now()
        task.save(update_fields=['opened_at'])
    return Response(SigningTaskSerializer(task).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def signing_task_signature_context(request, task_id):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `signing_task_signature_context` la endpoint hoac diem vao REST cua file `api/views/signing.py`, chiu trach nhiem chuan bi ngu canh cho buoc xu ly phia sau theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can chuan bi ngu canh cho buoc xu ly phia sau tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_flow_error_response`, `_resolve_signers`, `_multi_value_query_param` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac chuan bi ngu canh cho buoc xu ly phia sau tren giao dien.
    """
    task = _get_accessible_task_or_404(request.user, task_id)
    return Response(get_signature_context_for_task(task, request.user))

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def signing_task_preview_pdf(request, task_id):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `signing_task_preview_pdf` la endpoint hoac diem vao REST cua file `api/views/signing.py`, chiu trach nhiem chuan bi noi dung xem truoc theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can chuan bi noi dung xem truoc tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_flow_error_response`, `_resolve_signers`, `_multi_value_query_param` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac chuan bi noi dung xem truoc tren giao dien.
    """
    from urllib.parse import quote

    task = _get_accessible_task_or_404(request.user, task_id)
    if not can_view_signing_packet(request.user, task.packet):
        return Response({'detail': 'Ban khong duoc xem PDF ky nay.'}, status=status.HTTP_403_FORBIDDEN)
    CompanyRuntimeGuard.assert_file_field(
        task.packet.working_pdf,
        target=task.packet,
        detail='File PDF ky dang tro sang cong ty khac.',
    )

    response = FileResponse(task.packet.working_pdf.open('rb'), content_type='application/pdf')
    name = quote(f'{task.packet.document.title}_signing.pdf')
    response['Content-Disposition'] = f'inline; filename="{name}"'
    return response

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def signing_task_sign(request, task_id):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `signing_task_sign` la endpoint hoac diem vao REST cua file `api/views/signing.py`, chiu trach nhiem thuc hien buoc ky so hoac ghi nhan chu ky theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can thuc hien buoc ky so hoac ghi nhan chu ky tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_flow_error_response`, `_resolve_signers`, `_multi_value_query_param` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac thuc hien buoc ky so hoac ghi nhan chu ky tren giao dien.
    """
    task = _get_accessible_task_or_404(request.user, task_id)
    password = request.data.get('reauth_password') or request.data.get('password') or ''
    try:
        result = sign_task(task, request.user, password)
    except SigningFlowError as exc:
        return _signing_flow_error_response(exc)
    task.refresh_from_db()
    payload = {
        'task': SigningTaskSerializer(task).data,
        'signed_pdf': SignedPdfDocumentSerializer(result.get('signed_pdf')).data if result.get('signed_pdf') else None,
        'verification': result.get('verification_report'),
    }
    return Response(payload)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def signing_task_reject(request, task_id):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `signing_task_reject` la endpoint hoac diem vao REST cua file `api/views/signing.py`, chiu trach nhiem tu choi mot yeu cau nghiep vu theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can tu choi mot yeu cau nghiep vu tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_flow_error_response`, `_resolve_signers`, `_multi_value_query_param` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac tu choi mot yeu cau nghiep vu tren giao dien.
    """
    task = _get_accessible_task_or_404(request.user, task_id)
    reason = str(request.data.get('reason') or '').strip()
    if not reason:
        return Response({'detail': 'Phai co ly do tu choi yeu cau ky.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        reject_task(task, request.user, reason)
    except SigningFlowError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    task.refresh_from_db()
    return Response(SigningTaskSerializer(task).data)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def signing_delegations(request):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `signing_delegations` la endpoint hoac diem vao REST cua file `api/views/signing.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can thuc hien phan xu ly chuyen trach cua symbol hien tai tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_flow_error_response`, `_resolve_signers`, `_multi_value_query_param` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac thuc hien phan xu ly chuyen trach cua symbol hien tai tren giao dien.
    """
    can_manage_hr = can_manage_hr_delegations(request.user)
    can_manage_accounting = can_manage_accounting_delegations(request.user)
    if not can_manage_hr and not can_manage_accounting:
        return Response({'detail': 'Ban khong co quyen quan ly uy quyen ky so.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        qs = DepartmentDelegation.objects.filter(is_active=True).select_related('department', 'delegate_user')
        company = get_user_company(request.user)
        if company is not None:
            qs = qs.filter(department__company=company)
        if can_manage_hr and can_manage_accounting:
            pass
        elif can_manage_hr:
            qs = qs.filter(permission_type=DELEGATION_APPROVE_PROPOSAL)
        else:
            qs = qs.filter(permission_type=DELEGATION_VIEW_SIGNED_PDF)
        return Response(DepartmentDelegationSerializer(qs.order_by('department__name', 'delegate_user__username'), many=True).data)

    serializer = DepartmentDelegationCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    permission_type = serializer.validated_data['permission_type']
    delegate_user_qs = User.objects.filter(pk=serializer.validated_data['delegate_user_id'], is_active=True)
    company = get_user_company(request.user)
    if company is not None:
        delegate_user_qs = delegate_user_qs.filter(company_membership__company=company, company_membership__is_active=True)
    delegate_user = get_object_or_404(delegate_user_qs.distinct())
    if permission_type == DELEGATION_APPROVE_PROPOSAL:
        if not can_manage_hr:
            return Response({'detail': 'Ban khong the cap quyen duyet de xuat ky.'}, status=status.HTTP_403_FORBIDDEN)
        department = get_hr_department(request.user)
        group = get_hr_group(request.user)
    else:
        if not can_manage_accounting:
            return Response({'detail': 'Ban khong the cap quyen xem PDF da ky.'}, status=status.HTTP_403_FORBIDDEN)
        department = get_accounting_department(request.user)
        group = get_accounting_group(request.user)
    if department is None:
        return Response({'detail': 'Chua xac dinh duoc phong ban dac biet cho quy trinh ky.'}, status=status.HTTP_400_BAD_REQUEST)
    if not is_special_department_member(delegate_user, department, group):
        return Response(
            {'detail': 'Chi co the uy quyen cho nhan vien thuoc dung phong ban dac biet.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    delegation, created = DepartmentDelegation.objects.get_or_create(
        department=department,
        delegate_user=delegate_user,
        permission_type=permission_type,
        defaults={'created_by': request.user, 'is_active': True},
    )
    if not created and not delegation.is_active:
        delegation.is_active = True
        delegation.created_by = request.user
        delegation.save(update_fields=['is_active', 'created_by'])
    return Response(DepartmentDelegationSerializer(delegation).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def signing_delegation_detail(request, delegation_id):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `signing_delegation_detail` la endpoint hoac diem vao REST cua file `api/views/signing.py`, chiu trach nhiem tra du lieu chi tiet cho mot doi tuong cu the theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can tra du lieu chi tiet cho mot doi tuong cu the tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_flow_error_response`, `_resolve_signers`, `_multi_value_query_param` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac tra du lieu chi tiet cho mot doi tuong cu the tren giao dien.
    """
    delegation_qs = DepartmentDelegation.objects.select_related('department')
    company = get_user_company(request.user)
    if company is not None:
        delegation_qs = delegation_qs.filter(department__company=company)
    delegation = get_object_or_404(delegation_qs, pk=delegation_id)
    if delegation.permission_type == DELEGATION_APPROVE_PROPOSAL:
        if not can_manage_hr_delegations(request.user):
            return Response({'detail': 'Ban khong the xoa uy quyen duyet.'}, status=status.HTTP_403_FORBIDDEN)
    else:
        if not can_manage_accounting_delegations(request.user):
            return Response({'detail': 'Ban khong the xoa uy quyen xem PDF.'}, status=status.HTTP_403_FORBIDDEN)
    delegation.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def signed_pdf_list(request):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `signed_pdf_list` la endpoint hoac diem vao REST cua file `api/views/signing.py`, chiu trach nhiem tra danh sach du lieu theo bo loc hien tai theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can tra danh sach du lieu theo bo loc hien tai tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_flow_error_response`, `_resolve_signers`, `_multi_value_query_param` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac tra danh sach du lieu theo bo loc hien tai tren giao dien.
    """
    q = (request.GET.get('q') or '').strip()
    status_filter = _multi_value_query_param(request, 'status')
    mode_filter = _multi_value_query_param(request, 'mode')
    forwarded = (request.GET.get('forwarded') or '').strip()

    signed_docs = get_accessible_signed_pdfs(request.user).order_by('-created_at')
    if q:
        signed_docs = signed_docs.filter(
            models.Q(title__icontains=q)
            | models.Q(owner__username__icontains=q)
            | models.Q(owner__first_name__icontains=q)
            | models.Q(owner__last_name__icontains=q)
            | models.Q(packet__proposal__proposed_by__username__icontains=q)
            | models.Q(packet__proposal__proposed_by__first_name__icontains=q)
            | models.Q(packet__proposal__proposed_by__last_name__icontains=q)
            | models.Q(packet__tasks__signer_user__username__icontains=q)
            | models.Q(packet__tasks__signer_user__first_name__icontains=q)
            | models.Q(packet__tasks__signer_user__last_name__icontains=q)
            | models.Q(signature_records__certificate_subject_dn__icontains=q)
            | models.Q(signature_records__certificate_serial_number__icontains=q)
            | models.Q(mailbox_threads__entries__forwarded_by__username__icontains=q)
            | models.Q(mailbox_threads__entries__forwarded_by__first_name__icontains=q)
            | models.Q(mailbox_threads__entries__forwarded_by__last_name__icontains=q)
            | models.Q(mailbox_threads__entries__forwarded_to__username__icontains=q)
            | models.Q(mailbox_threads__entries__forwarded_to__first_name__icontains=q)
            | models.Q(mailbox_threads__entries__forwarded_to__last_name__icontains=q)
        ).distinct()
    if status_filter:
        signed_docs = signed_docs.filter(
            verification_status__in=[normalize_verification_status(item) for item in status_filter]
        )
    if mode_filter:
        signed_docs = signed_docs.filter(
            signature_mode__in=[normalize_signature_mode(item) for item in mode_filter]
        )
    if forwarded == '1':
        signed_docs = signed_docs.filter(mailbox_threads__isnull=False).distinct()
    elif forwarded == '0':
        signed_docs = signed_docs.filter(mailbox_threads__isnull=True)
    return Response(SignedPdfDocumentSerializer(signed_docs, many=True).data)

def _get_signed_pdf_or_404(user, pk):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_get_signed_pdf_or_404` la helper noi bo cua lop API trong file `api/views/signing.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai truoc khi endpoint chinh phan hoi.
    Vai tro cua no trong frontend: Frontend Flutter khong goi truc tiep helper nay; endpoint cung file dung no khi giao dien can thuc hien phan xu ly chuyen trach cua symbol hien tai nhung khong nen tu xu ly o client.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `signing_summary`, `signing_candidates`, `document_signing_start` goi lai.
    Tac dung: Co lap rieng buoc thuc hien phan xu ly chuyen trach cua symbol hien tai de cac endpoint cung file tai su dung dung mot quy tac.
    """
    return get_object_or_404(get_accessible_signed_pdfs(user), pk=pk)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def signed_pdf_detail(request, pk):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `signed_pdf_detail` la endpoint hoac diem vao REST cua file `api/views/signing.py`, chiu trach nhiem tra du lieu chi tiet cho mot doi tuong cu the theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can tra du lieu chi tiet cho mot doi tuong cu the tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_flow_error_response`, `_resolve_signers`, `_multi_value_query_param` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac tra du lieu chi tiet cho mot doi tuong cu the tren giao dien.
    """
    signed_pdf = _get_signed_pdf_or_404(request.user, pk)
    return Response(SignedPdfDocumentSerializer(signed_pdf).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def signed_pdf_verify(request, pk):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `signed_pdf_verify` la endpoint hoac diem vao REST cua file `api/views/signing.py`, chiu trach nhiem xac minh tinh hop le hoac toan ven theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can xac minh tinh hop le hoac toan ven tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_flow_error_response`, `_resolve_signers`, `_multi_value_query_param` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac xac minh tinh hop le hoac toan ven tren giao dien.
    """
    signed_pdf = _get_signed_pdf_or_404(request.user, pk)
    if not can_view_signed_pdf(request.user, signed_pdf):
        return Response({'detail': 'Ban khong duoc kiem tra PDF da ky nay.'}, status=status.HTTP_403_FORBIDDEN)
    CompanyRuntimeGuard.assert_file_field(
        signed_pdf.signed_pdf_file,
        target=signed_pdf,
        detail='File PDF da ky dang tro sang cong ty khac.',
    )
    report = get_signed_pdf_integrity_report(signed_pdf)
    if is_internal_approval_status(report.get('status')):
        response_status = status.HTTP_200_OK
    else:
        response_status = status.HTTP_200_OK if report.get('is_safe') else status.HTTP_409_CONFLICT
    return Response(report, status=response_status)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def signed_pdf_preview_pdf(request, pk):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `signed_pdf_preview_pdf` la endpoint hoac diem vao REST cua file `api/views/signing.py`, chiu trach nhiem chuan bi noi dung xem truoc theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can chuan bi noi dung xem truoc tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_flow_error_response`, `_resolve_signers`, `_multi_value_query_param` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac chuan bi noi dung xem truoc tren giao dien.
    """
    from urllib.parse import quote

    signed_pdf = _get_signed_pdf_or_404(request.user, pk)
    if not can_view_signed_pdf(request.user, signed_pdf):
        return Response({'detail': 'Ban khong duoc xem PDF da ky nay.'}, status=status.HTTP_403_FORBIDDEN)
    CompanyRuntimeGuard.assert_file_field(
        signed_pdf.signed_pdf_file,
        target=signed_pdf,
        detail='File PDF da ky dang tro sang cong ty khac.',
    )
    try:
        ensure_signed_pdf_integrity(signed_pdf)
    except SigningFlowError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
    response = FileResponse(signed_pdf.signed_pdf_file.open('rb'), content_type='application/pdf')
    name = quote(f'{signed_pdf.title}.pdf')
    response['Content-Disposition'] = f'inline; filename="{name}"'
    return response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def signed_pdf_download(request, pk):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `signed_pdf_download` la endpoint hoac diem vao REST cua file `api/views/signing.py`, chiu trach nhiem tra tep de frontend tai xuong theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can tra tep de frontend tai xuong tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_flow_error_response`, `_resolve_signers`, `_multi_value_query_param` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac tra tep de frontend tai xuong tren giao dien.
    """
    from urllib.parse import quote

    signed_pdf = _get_signed_pdf_or_404(request.user, pk)
    if not can_view_signed_pdf(request.user, signed_pdf):
        return Response({'detail': 'Ban khong duoc tai PDF da ky nay.'}, status=status.HTTP_403_FORBIDDEN)
    CompanyRuntimeGuard.assert_file_field(
        signed_pdf.signed_pdf_file,
        target=signed_pdf,
        detail='File PDF da ky dang tro sang cong ty khac.',
    )
    try:
        ensure_signed_pdf_integrity(signed_pdf)
    except SigningFlowError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
    response = FileResponse(signed_pdf.signed_pdf_file.open('rb'), content_type='application/pdf')
    name = quote(f'{signed_pdf.title}.pdf')
    response['Content-Disposition'] = f'attachment; filename="{name}"'
    return response

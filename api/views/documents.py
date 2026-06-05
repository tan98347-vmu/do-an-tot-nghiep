"""
Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
Vai tro backend: File `api/views/documents.py` giu hoac ho tro luong backend cho danh sach van ban, chi tiet van ban, version, chia se, luu tru, preview PDF, hom thu va xoa mem.
Vai tro cua no trong frontend: Cac man `/documents`, `/mailbox`, `/trash` va badge phe duyet doc ket qua do file nay cung cap hoac gian tiep lam thay doi.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`.
Tac dung: Bao dam vong doi van ban tu luc tao, chia se, xu ly hom thu toi luc phuc hoi hoac xoa vinh vien khong bi lech trang thai.
"""

import logging

from django.contrib.auth.models import User
from django.db import models
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from documents.models import (
    Document, DocumentFavorite, DocumentMailboxEntry, DocumentMailboxThread,
    DOC_STATUS_DRAFT, DOC_STATUS_FINAL, DOC_STATUS_ARCHIVED,
    SOURCE_UPLOADED, SHARE_ACTIVE, SHARE_PENDING_ADMIN, SHARE_PENDING_LEADER
)
from documents.mailbox_services import (
    MailboxFlowError,
    complete_mailbox_entry,
    ensure_mailbox_entry_signing_task,
    forward_document,
    mailbox_integrity_report,
    mailbox_thread_integrity_report,
    reject_mailbox_entry,
)
from documents.pdf_preview import (
    DocumentPreviewUnavailable,
    build_document_preview_pdf,
    build_document_version_preview_pdf,
    build_template_preview_pdf,
    schedule_document_preview_regeneration,
)
from documents.ai_summary import (
    DocumentSummaryUnavailable,
    summarize_document_content,
)
from documents.runtime_helpers import _ascii_safe_name, _extract_text_from_docx
from documents.edit_lock_state import get_document_edit_lock_state
from accounts.permissions import (
    can_delete_document,
    can_edit_document,
    get_accessible_documents,
    get_document_detail_queryset,
    is_document_edit_locked,
    get_template_detail_queryset,
)
from accounts.runtime_guard import CompanyRuntimeGuard
from accounts.tenancy import filter_queryset_by_current_company, get_user_company
from ..serializers.documents import (
    DocumentDetailSerializer,
    DocumentListSerializer,
    DocumentMailboxThreadSerializer,
    DocumentWriteSerializer,
)
from ..serializers.signing import SigningTaskSerializer
from ..trash_services import mark_deleted

_preview_logger = logging.getLogger('documents.preview_pdf')
_summary_logger = logging.getLogger('documents.ai_summary')

def _document_edit_locked_response(document):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_document_edit_locked_response` la helper noi bo cua lop API trong file `api/views/documents.py`, chiu trach nhiem chinh sua du lieu theo input vua gui len truoc khi endpoint chinh phan hoi.
    Vai tro cua no trong frontend: Frontend Flutter khong goi truc tiep helper nay; endpoint cung file dung no khi giao dien can chinh sua du lieu theo input vua gui len nhung khong nen tu xu ly o client.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Thuong duoc cac ham public nhu `document_list_create`, `document_detail_view`, `document_download` goi lai.
    Tac dung: Co lap rieng buoc chinh sua du lieu theo input vua gui len de cac endpoint cung file tai su dung dung mot quy tac.
    """
    return Response(
        {'detail': get_document_edit_lock_state(document).detail},
        status=status.HTTP_409_CONFLICT,
    )

def _normalize_search_terms(raw_query):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_normalize_search_terms` la helper noi bo cua lop API trong file `api/views/documents.py`, chiu trach nhiem chuan hoa du lieu dau vao hoac du lieu trung gian truoc khi endpoint chinh phan hoi.
    Vai tro cua no trong frontend: Frontend Flutter khong goi truc tiep helper nay; endpoint cung file dung no khi giao dien can chuan hoa du lieu dau vao hoac du lieu trung gian nhung khong nen tu xu ly o client.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Thuong duoc cac ham public nhu `document_list_create`, `document_detail_view`, `document_download` goi lai.
    Tac dung: Co lap rieng buoc chuan hoa du lieu dau vao hoac du lieu trung gian de cac endpoint cung file tai su dung dung mot quy tac.
    """
    import re

    normalized = re.sub(r'[#,:;]+', ' ', str(raw_query or '').strip())
    return [term for term in re.split(r'\s+', normalized) if term]

def _build_document_search_query(raw_query):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_build_document_search_query` la helper noi bo cua lop API trong file `api/views/documents.py`, chiu trach nhiem dung payload hoac cau truc du lieu trung gian truoc khi endpoint chinh phan hoi.
    Vai tro cua no trong frontend: Frontend Flutter khong goi truc tiep helper nay; endpoint cung file dung no khi giao dien can dung payload hoac cau truc du lieu trung gian nhung khong nen tu xu ly o client.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Thuong duoc cac ham public nhu `document_list_create`, `document_detail_view`, `document_download` goi lai.
    Tac dung: Co lap rieng buoc dung payload hoac cau truc du lieu trung gian de cac endpoint cung file tai su dung dung mot quy tac.
    """
    from django.db.models import Q

    fields = (
        'title',
        'doc_number',
        'notes',
        'tags__icontains',
        'template__title',
        'department__name',
        'department__code',
        'category__name',
        'group__name',
        'source_type',
        'status',
        'share_status',
        'owner__username',
        'owner__first_name',
        'owner__last_name',
    )
    raw = str(raw_query or '').strip()
    if not raw:
        return Q()

    

    def _field_q(value):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `_field_q` la helper noi bo cua lop API trong file `api/views/documents.py`, chiu trach nhiem chuan bi hoac dong bo truong du lieu lien quan truoc khi endpoint chinh phan hoi.
        Vai tro cua no trong frontend: Frontend Flutter khong goi truc tiep helper nay; endpoint cung file dung no khi giao dien can chuan bi hoac dong bo truong du lieu lien quan nhung khong nen tu xu ly o client.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Thuong duoc cac ham public nhu `document_list_create`, `document_detail_view`, `document_download` goi lai.
        Tac dung: Co lap rieng buoc chuan bi hoac dong bo truong du lieu lien quan de cac endpoint cung file tai su dung dung mot quy tac.
        """
        query = Q()
        for field in fields:
            query |= Q(**{f'{field}__icontains': value})
        return query

    combined = _field_q(raw)
    terms = _normalize_search_terms(raw)
    if len(terms) <= 1:
        return combined

    token_query = Q()
    for term in terms:
        term_query = _field_q(term)
        token_query = term_query if not token_query.children else token_query & term_query
    return combined | token_query

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def document_list_create(request):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `document_list_create` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem tra danh sach du lieu theo bo loc hien tai theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can tra danh sach du lieu theo bo loc hien tai tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac tra danh sach du lieu theo bo loc hien tai tren giao dien.
    """
    if request.method == 'GET':
        group = request.GET.get('group', '')
        q = request.GET.get('q', '').strip()
        status_filter = request.GET.get('status', '')
        admin_mode = request.GET.get('admin') == '1' and request.user.is_superuser
        owner_id_filter = request.GET.get('owner_id', '')
        group_id_filter = request.GET.get('group_id', '')

        if admin_mode:
            from documents.models import Document as DocModel
            qs = DocModel.objects.all()
        else:
            qs = get_accessible_documents(request.user).filter(is_archived=False)
        qs = qs.select_related('owner', 'template', 'department', 'category', 'group')

        if not admin_mode:
            if group == 'private':
                qs = qs.filter(owner=request.user)
            elif group == 'group':
                from accounts.models import UserGroupMembership
                from django.contrib.contenttypes.models import ContentType
                from sharing.constants import APPROVAL_ACTIVE, SCOPE_GROUP
                from sharing.models import ShareGrant
                gids = list(
                    UserGroupMembership.objects.filter(user=request.user)
                    .values_list('group_id', flat=True)
                )
                ct = ContentType.objects.get_for_model(Document)
                group_shared_ids = ShareGrant.objects.filter(
                    content_type=ct,
                    approval_status=APPROVAL_ACTIVE,
                    scope=SCOPE_GROUP,
                    target_group_id__in=gids,
                ).values_list('object_id', flat=True)
                # Chia se nhom qua ShareGrant (target_group) + legacy (visibility/group FK).
                qs = qs.filter(
                    models.Q(pk__in=list(group_shared_ids))
                    | models.Q(visibility='group', group_id__in=gids)
                )
            elif group == 'public':
                from django.contrib.contenttypes.models import ContentType
                from sharing.constants import APPROVAL_ACTIVE, SCOPE_EVERYONE
                from sharing.models import ShareGrant
                ct = ContentType.objects.get_for_model(Document)
                everyone_ids = ShareGrant.objects.filter(
                    content_type=ct,
                    approval_status=APPROVAL_ACTIVE,
                    scope=SCOPE_EVERYONE,
                ).values_list('object_id', flat=True)
                qs = qs.filter(models.Q(visibility='public') | models.Q(pk__in=list(everyone_ids)))
            elif group == 'favorite':
                fav_ids = DocumentFavorite.objects.filter(user=request.user).values_list('document_id', flat=True)
                qs = qs.filter(id__in=fav_ids)
            elif group == 'archived':
                qs = get_accessible_documents(request.user).filter(owner=request.user, is_archived=True)

        if owner_id_filter and request.user.is_superuser:
            qs = qs.filter(owner_id=owner_id_filter)
        if group_id_filter and request.user.is_superuser:
            qs = qs.filter(group_id=group_id_filter)
        if q:
            qs = qs.filter(_build_document_search_query(q))
        if status_filter:
            qs = qs.filter(status=status_filter)
        serializer = DocumentListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    
    serializer = DocumentWriteSerializer(data=request.data)
    if serializer.is_valid():
        company = get_user_company(request.user)
        category = serializer.validated_data.get('category')
        if category is not None and getattr(category, 'company_id', None) is None and company is not None:
            category.company = company
            category.save(update_fields=['company'])
        doc = Document(owner=request.user, status=DOC_STATUS_DRAFT,
                       visibility='private', share_status=SHARE_ACTIVE, company=company)
        for attr, value in serializer.validated_data.items():
            setattr(doc, attr, value)
        if doc.template_id and not doc.tags:
            doc.tags = list(getattr(doc.template, 'tags', []) or [])
        doc.save()
        return Response(
            DocumentDetailSerializer(doc, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def document_detail_view(request, pk):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `document_detail_view` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem tra du lieu chi tiet cho mot doi tuong cu the theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can tra du lieu chi tiet cho mot doi tuong cu the tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac tra du lieu chi tiet cho mot doi tuong cu the tren giao dien.
    """
    qs = get_document_detail_queryset(request.user)
    doc = get_object_or_404(qs, pk=pk)
    CompanyRuntimeGuard.assert_file_field(
        doc.output_file,
        target=doc,
        detail='File van ban dang tro sang cong ty khac.',
    )

    if request.method == 'GET':
        return Response(DocumentDetailSerializer(doc, context={'request': request}).data)

    if request.method == 'DELETE':
        if is_document_edit_locked(doc):
            return _document_edit_locked_response(doc)
        can_delete = can_delete_document(request.user, doc)
        if not can_delete:
            return Response({'detail': 'KhÃ´ng cÃ³ quyá»n xÃ³a.'}, status=status.HTTP_403_FORBIDDEN)
        mark_deleted(doc, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    if is_document_edit_locked(doc):
        return _document_edit_locked_response(doc)

    if not can_edit_document(request.user, doc):
        return Response({'detail': 'KhÃ´ng cÃ³ quyá»n sá»­a.'}, status=status.HTTP_403_FORBIDDEN)
    partial = request.method == 'PATCH'
    serializer = DocumentWriteSerializer(doc, data=request.data, partial=partial)
    if serializer.is_valid():
        before_snapshot = (
            doc.title,
            doc.content,
            doc.notes,
            doc.department_id,
            doc.category_id,
        )
        serializer.save()
        after_snapshot = (
            doc.title,
            doc.content,
            doc.notes,
            doc.department_id,
            doc.category_id,
        )
        if before_snapshot != after_snapshot and doc.visibility == 'group':
            doc.share_status = SHARE_PENDING_LEADER
            doc.save(update_fields=['share_status'])
        elif before_snapshot != after_snapshot and doc.visibility == 'public':
            doc.share_status = SHARE_PENDING_ADMIN
            doc.save(update_fields=['share_status'])
        return Response(DocumentDetailSerializer(doc, context={'request': request}).data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_download(request, pk):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `document_download` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem tra tep de frontend tai xuong theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can tra tep de frontend tai xuong tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac tra tep de frontend tai xuong tren giao dien.
    """
    from django.http import HttpResponse
    from urllib.parse import quote
    qs = get_document_detail_queryset(request.user)
    doc = get_object_or_404(qs, pk=pk)
    CompanyRuntimeGuard.assert_file_field(
        doc.output_file,
        target=doc,
        detail='File van ban dang tro sang cong ty khac.',
    )
    if not doc.output_file:
        return Response({'detail': 'KhÃ´ng cÃ³ file.'}, status=status.HTTP_404_NOT_FOUND)
    with doc.output_file.open('rb') as f:
        content = f.read()
    response = HttpResponse(
        content,
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    name = quote(f'{doc.title}.docx')
    response['Content-Disposition'] = f'attachment; filename="{name}"'
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def document_summarize(request, pk):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `document_summarize` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem tom tat noi dung van ban bang AI theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung bam yeu cau tom tat noi dung tren man chi tiet van ban.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.ai_summary`, `documents.runtime_helpers`, `accounts.permissions`, `accounts.runtime_guard`.
    Tac dung: Tra ban tom tat AI cua noi dung van ban hien tai de hien thi ngay tren giao dien.
    """
    qs = get_document_detail_queryset(request.user)
    doc = get_object_or_404(qs, pk=pk)
    if doc.output_file:
        CompanyRuntimeGuard.assert_file_field(
            doc.output_file,
            target=doc,
            detail='File van ban dang tro sang cong ty khac.',
        )

    raw_options = request.data.get('options')
    if not isinstance(raw_options, dict):
        raw_options = {
            'length': request.data.get('length'),
            'language': request.data.get('language'),
            'style': request.data.get('style'),
            'max_words': request.data.get('max_words'),
        }
    try:
        payload = summarize_document_content(doc, user=request.user, options=raw_options)
    except DocumentSummaryUnavailable as exc:
        return Response({'detail': exc.detail}, status=exc.status_code)
    except Exception as exc:
        _summary_logger.exception(
            'document summarize failed | document_id=%s | user_id=%s | error=%r',
            doc.pk,
            getattr(request.user, 'id', None),
            exc,
        )
        return Response(
            {
                'detail': 'Khong the tom tat van ban luc nay. Vui long thu lai sau.',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return Response(payload)


def _do_summarize_task(task_id, user_id, document_id, options_payload, safe_user_rules_block):
    from django.contrib.auth.models import User
    from documents.ai_summary import (
        DocumentSummaryUnavailable, summarize_document_content,
    )
    from ai_tasks.services.task_runner import update_progress, check_cancel

    user = User.objects.get(pk=user_id)
    qs = get_document_detail_queryset(user)
    doc = qs.filter(pk=document_id).first()
    if not doc:
        raise ValueError('Van ban khong ton tai hoac khong co quyen.')

    def _cb(pct, stage, detail=''):
        update_progress(task_id, pct, stage, detail)

    def _cancel_cb():
        check_cancel(task_id)

    try:
        payload = summarize_document_content(
            doc, user=user, options=options_payload,
            safe_user_rules_block=safe_user_rules_block or '',
            on_progress=_cb, cancel_check=_cancel_cb,
        )
    except DocumentSummaryUnavailable as exc:
        raise ValueError(exc.detail)
    return payload


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def document_summarize_async(request, pk):
    from ai_tasks.models import TASK_TYPE_SUMMARIZE
    from ai_tasks.services.task_runner import create_task, run_in_thread

    qs = get_document_detail_queryset(request.user)
    if not qs.filter(pk=pk).exists():
        return Response({'detail': 'Van ban khong ton tai.'}, status=status.HTTP_404_NOT_FOUND)

    raw_options = request.data.get('options')
    if not isinstance(raw_options, dict):
        raw_options = {
            'length': request.data.get('length'),
            'language': request.data.get('language'),
            'style': request.data.get('style'),
            'max_words': request.data.get('max_words'),
        }
    safe_block = str(request.data.get('safe_user_rules_block') or '').strip()

    task = create_task(
        user=request.user,
        task_type=TASK_TYPE_SUMMARIZE,
        related_entity_type='document',
        related_entity_id=pk,
    )
    run_in_thread(task, _do_summarize_task, request.user.pk, pk, raw_options, safe_block)
    return Response({
        'task_id': str(task.task_id),
        'polling_url': f'/api/ai-tasks/{task.task_id}/',
        'status': 'queued',
    }, status=status.HTTP_202_ACCEPTED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_preview_pdf(request, pk):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `document_preview_pdf` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem chuan bi noi dung xem truoc theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can chuan bi noi dung xem truoc tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac chuan bi noi dung xem truoc tren giao dien.
    """
    from django.http import FileResponse
    from urllib.parse import quote

    qs = get_document_detail_queryset(request.user)
    doc = get_object_or_404(qs, pk=pk)

    try:
        pdf_path = build_document_preview_pdf(doc)
    except DocumentPreviewUnavailable as exc:
        _preview_logger.warning(
            'preview convert failed | document_id=%s | code=%s | detail=%s',
            doc.pk,
            exc.code,
            exc.detail,
        )
        return Response(
            {
                'detail': exc.detail,
                'code': exc.code,
                'fallback': 'content_html',
            },
            status=exc.status_code,
        )
    CompanyRuntimeGuard.assert_preview_path(
        pdf_path,
        target=doc,
        namespace='documents',
        detail='Preview PDF cua van ban dang tro sang cong ty khac.',
    )

    response = FileResponse(pdf_path.open('rb'), content_type='application/pdf')
    name = quote(f'{doc.title}.pdf')
    response['Content-Disposition'] = f'inline; filename="{name}"'
    response['X-Document-Preview'] = 'pdf'
    return response


def _ascii_safe_pdf_name(title: str) -> str:
    import re
    safe = re.sub(r'[^A-Za-z0-9._-]+', '_', str(title or '').strip())
    safe = safe.strip('._') or 'document'
    return safe[:120]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_download_pdf(request, pk):
    """Tai PDF cua van ban (convert tu file DOCX bang LibreOffice, co cache)."""
    from django.http import FileResponse
    from urllib.parse import quote

    qs = get_document_detail_queryset(request.user)
    doc = get_object_or_404(qs, pk=pk)
    try:
        pdf_path = build_document_preview_pdf(doc)
    except DocumentPreviewUnavailable as exc:
        _preview_logger.warning(
            'download pdf failed | document_id=%s | code=%s | detail=%s',
            doc.pk, exc.code, exc.detail,
        )
        return Response(
            {'detail': exc.detail, 'code': exc.code},
            status=exc.status_code,
        )
    CompanyRuntimeGuard.assert_preview_path(
        pdf_path,
        target=doc,
        namespace='documents',
        detail='PDF cua van ban dang tro sang cong ty khac.',
    )
    response = FileResponse(pdf_path.open('rb'), content_type='application/pdf')
    safe_name = _ascii_safe_pdf_name(doc.title) + '.pdf'
    quoted_name = quote(f'{doc.title}.pdf')
    response['Content-Disposition'] = (
        f"attachment; filename=\"{safe_name}\"; filename*=UTF-8''{quoted_name}"
    )
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_version_download_pdf(request, pk, version):
    """Tai PDF cua mot phien ban van ban."""
    from django.http import FileResponse
    from urllib.parse import quote
    from documents.models import DocumentVersion

    qs = get_document_detail_queryset(request.user)
    doc = get_object_or_404(qs, pk=pk)
    ver = get_object_or_404(DocumentVersion, document=doc, version_number=version)
    try:
        pdf_path = build_document_version_preview_pdf(ver)
    except DocumentPreviewUnavailable as exc:
        _preview_logger.warning(
            'download pdf failed | document_id=%s | version=%s | code=%s | detail=%s',
            doc.pk, version, exc.code, exc.detail,
        )
        return Response(
            {'detail': exc.detail, 'code': exc.code},
            status=exc.status_code,
        )
    response = FileResponse(pdf_path.open('rb'), content_type='application/pdf')
    safe_name = _ascii_safe_pdf_name(f'{doc.title}_v{version}') + '.pdf'
    quoted_name = quote(f'{doc.title}_v{version}.pdf')
    response['Content-Disposition'] = (
        f"attachment; filename=\"{safe_name}\"; filename*=UTF-8''{quoted_name}"
    )
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_content_html(request, pk):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `document_content_html` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi van ban theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can xu ly du lieu hoac thao tac lien quan toi van ban tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac xu ly du lieu hoac thao tac lien quan toi van ban tren giao dien.
    """
    import mammoth
    qs = get_document_detail_queryset(request.user)
    doc = get_object_or_404(qs, pk=pk)

    if doc.output_file:
        CompanyRuntimeGuard.assert_file_field(
            doc.output_file,
            target=doc,
            detail='File van ban dang tro sang cong ty khac.',
        )
        try:
            with doc.output_file.open('rb') as f:
                result = mammoth.convert_to_html(f)
            html_body = result.value
        except Exception as e:
            html_body = f'<p style="color:red">Lá»—i chuyá»ƒn Ä‘á»•i: {e}</p>'
    elif doc.content:
        html_body = doc.content
    else:
        html_body = '<p style="color:#888">KhÃ´ng cÃ³ ná»™i dung.</p>'

    full_html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Times New Roman', Times, serif;
    font-size: 14pt;
    background: #e0e0e0;
    padding: 24px;
    line-height: 1.6;
  }}
  .page {{
    background: #ffffff;
    max-width: 210mm;
    min-height: 297mm;
    margin: 0 auto;
    padding: 20mm 25mm 20mm 30mm;
    box-shadow: 0 2px 12px rgba(0,0,0,0.18);
  }}
  h1,h2,h3,h4 {{ font-family: 'Times New Roman', Times, serif; }}
  table {{ border-collapse: collapse; width: 100%; margin: 8px 0; }}
  td, th {{ border: 1px solid #888; padding: 4px 8px; }}
  p {{ margin-bottom: 6px; }}
</style>
</head>
<body>
  <div class="page">{html_body}</div>
</body>
</html>"""
    return Response({'html': full_html})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def template_preview_pdf(request, pk):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `template_preview_pdf` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem chuan bi noi dung xem truoc theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can chuan bi noi dung xem truoc tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac chuan bi noi dung xem truoc tren giao dien.
    """
    from django.http import FileResponse
    from urllib.parse import quote
    tmpl = get_object_or_404(get_template_detail_queryset(request.user), pk=pk)

    try:
        pdf_path = build_template_preview_pdf(tmpl)
    except DocumentPreviewUnavailable as exc:
        _preview_logger.warning(
            'template preview convert failed | template_id=%s | code=%s | detail=%s',
            tmpl.pk,
            exc.code,
            exc.detail,
        )
        return Response(
            {
                'detail': exc.detail,
                'code': exc.code,
                'fallback': 'content_html',
            },
            status=exc.status_code,
        )
    CompanyRuntimeGuard.assert_preview_path(
        pdf_path,
        target=tmpl,
        namespace='templates',
        detail='Preview PDF cua mau dang tro sang cong ty khac.',
    )

    response = FileResponse(pdf_path.open('rb'), content_type='application/pdf')
    name = quote(f'{tmpl.title}.pdf')
    response['Content-Disposition'] = f'inline; filename="{name}"'
    response['X-Template-Preview'] = 'pdf'
    return response

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def document_finalize(request, pk):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `document_finalize` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem chot du lieu sang trang thai hoan tat theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can chot du lieu sang trang thai hoan tat tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac chot du lieu sang trang thai hoan tat tren giao dien.
    """
    doc = get_object_or_404(Document, pk=pk, owner=request.user)
    if doc.status != DOC_STATUS_DRAFT:
        return Response({'detail': 'Chá»‰ chuyá»ƒn tá»« NhÃ¡p sang ChÃ­nh thá»©c.'}, status=status.HTTP_400_BAD_REQUEST)
    doc.status = DOC_STATUS_FINAL
    doc.save(update_fields=['status'])
    return Response({'status': doc.status})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def document_archive(request, pk):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `document_archive` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem chuyen du lieu sang trang thai luu tru theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can chuyen du lieu sang trang thai luu tru tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac chuyen du lieu sang trang thai luu tru tren giao dien.
    """
    doc = get_object_or_404(Document, pk=pk, owner=request.user)
    if doc.visibility != 'private':
        return Response(
            {'detail': 'Chi co the luu tru van ban rieng cua toi.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    doc.status = DOC_STATUS_ARCHIVED
    doc.is_archived = True
    doc.archived_at = timezone.now()
    doc.save(update_fields=['status', 'is_archived', 'archived_at'])
    return Response({'status': 'archived'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def document_unarchive(request, pk):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `document_unarchive` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem dua du lieu ra khoi trang thai luu tru theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can dua du lieu ra khoi trang thai luu tru tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac dua du lieu ra khoi trang thai luu tru tren giao dien.
    """
    doc = get_object_or_404(Document, pk=pk, owner=request.user, is_archived=True)
    doc.status = DOC_STATUS_FINAL
    doc.is_archived = False
    doc.archived_at = None
    doc.save(update_fields=['status', 'is_archived', 'archived_at'])
    return Response({'status': 'final'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def document_share(request, pk):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `document_share` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem khoi tao hoac xu ly quy trinh chia se du lieu theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can khoi tao hoac xu ly quy trinh chia se du lieu tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac khoi tao hoac xu ly quy trinh chia se du lieu tren giao dien.
    """
    doc = get_object_or_404(Document, pk=pk, owner=request.user)
    if doc.is_archived:
        return Response(
            {'detail': 'Khong the chia se van ban da luu tru.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    visibility = request.data.get('visibility', 'private')
    group_id = request.data.get('group_id')
    from accounts.models import UserGroup

    if visibility == 'private':
        doc.visibility = 'private'
        doc.group = None
        doc.share_status = SHARE_ACTIVE
    elif visibility == 'group' and group_id:
        group = get_object_or_404(UserGroup, pk=group_id)
        doc.visibility = 'group'
        doc.group = group
        doc.share_status = SHARE_PENDING_LEADER
    elif visibility == 'public':
        doc.visibility = 'public'
        doc.group = None
        doc.share_status = SHARE_ACTIVE if request.user.is_superuser else SHARE_PENDING_ADMIN
    doc.save(update_fields=['visibility', 'group', 'share_status'])
    return Response({'visibility': doc.visibility, 'share_status': doc.share_status})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def document_favorite(request, pk):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `document_favorite` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem danh dau hoac bo danh dau yeu thich theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can danh dau hoac bo danh dau yeu thich tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac danh dau hoac bo danh dau yeu thich tren giao dien.
    """
    doc = get_object_or_404(get_accessible_documents(request.user), pk=pk)
    fav, created = DocumentFavorite.objects.get_or_create(user=request.user, document=doc)
    if not created:
        fav.delete()
        return Response({'favorited': False})
    return Response({'favorited': True})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_pending_shares(request):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `document_pending_shares` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi van ban theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can xu ly du lieu hoac thao tac lien quan toi van ban tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac xu ly du lieu hoac thao tac lien quan toi van ban tren giao dien.
    """
    from accounts.models import UserGroupMembership
    from django.db.models import Q

    qs = Document.objects.none()

    if request.user.is_superuser:
        qs = Document.objects.filter(share_status=SHARE_PENDING_ADMIN)

    leader_gids = list(
        UserGroupMembership.objects.filter(user=request.user, role='leader')
        .values_list('group_id', flat=True)
    )
    if leader_gids:
        leader_qs = Document.objects.filter(
            share_status=SHARE_PENDING_LEADER, group_id__in=leader_gids
        )
        qs = (qs | leader_qs) if request.user.is_superuser else leader_qs

    serializer = DocumentListSerializer(qs.order_by('-created_at'), many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def document_approve_share(request, pk):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `document_approve_share` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem khoi tao hoac xu ly quy trinh chia se du lieu theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can khoi tao hoac xu ly quy trinh chia se du lieu tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac khoi tao hoac xu ly quy trinh chia se du lieu tren giao dien.
    """
    from accounts.permissions import is_leader_of

    doc = get_object_or_404(Document, pk=pk)
    action = request.data.get('action', 'approve')

    can_approve = False
    if request.user.is_superuser and doc.share_status == SHARE_PENDING_ADMIN:
        can_approve = True
    if doc.share_status == SHARE_PENDING_LEADER and doc.group and is_leader_of(request.user, doc.group):
        can_approve = True

    if not can_approve:
        return Response({'detail': 'KhÃ´ng cÃ³ quyá»n phÃª duyá»‡t.'}, status=status.HTTP_403_FORBIDDEN)

    if action == 'approve':
        doc.share_status = SHARE_ACTIVE
        doc.save(update_fields=['share_status'])
    else:
        doc.share_status = 'rejected'
        doc.visibility = 'private'
        doc.group = None
        doc.save(update_fields=['share_status', 'visibility', 'group'])

    return Response(DocumentDetailSerializer(doc, context={'request': request}).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_check_title(request):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `document_check_title` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi van ban theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can xu ly du lieu hoac thao tac lien quan toi van ban tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac xu ly du lieu hoac thao tac lien quan toi van ban tren giao dien.
    """
    title = request.GET.get('title', '').strip()
    if not title:
        return Response({'match': None})
    doc = Document.objects.filter(owner=request.user, title__iexact=title, is_archived=False).first()
    if not doc:
        return Response({'match': None})
    return Response({'match': {
        'id': doc.id,
        'title': doc.title,
        'version_number': doc.version_number,
        'version_count': doc.versions.count(),
    }})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_versions(request, pk):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `document_versions` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi van ban theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can xu ly du lieu hoac thao tac lien quan toi van ban tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac xu ly du lieu hoac thao tac lien quan toi van ban tren giao dien.
    """
    from documents.models import DocumentVersion
    from ..serializers.documents import DocumentVersionSerializer
    qs = get_document_detail_queryset(request.user)
    doc = get_object_or_404(qs, pk=pk)
    versions = DocumentVersion.objects.filter(document=doc)
    return Response(DocumentVersionSerializer(versions, many=True).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def document_version_restore(request, pk, ver_id):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `document_version_restore` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem khoi phuc du lieu hoac trang thai cu theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can khoi phuc du lieu hoac trang thai cu tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac khoi phuc du lieu hoac trang thai cu tren giao dien.
    """
    from django.core.files.base import ContentFile
    from documents.models import DocumentVersion
    from ..serializers.documents import DocumentDetailSerializer

    doc = get_object_or_404(get_document_detail_queryset(request.user), pk=pk)
    if is_document_edit_locked(doc):
        return _document_edit_locked_response(doc)
    if not can_edit_document(request.user, doc):
        return Response({'detail': 'Khong co quyen sua.'}, status=status.HTTP_403_FORBIDDEN)
    ver = get_object_or_404(DocumentVersion, pk=ver_id, document=doc)

    new_ver_num = doc.version_number + 1
    new_ver = DocumentVersion(
        document=doc,
        version_number=new_ver_num,
        content=ver.content,
        change_note=f'KhÃ´i phá»¥c tá»« phiÃªn báº£n {ver.version_number}',
        variables_used=ver.variables_used,
        created_by=request.user,
    )
    
    if ver.output_file:
        CompanyRuntimeGuard.assert_file_field(
            ver.output_file,
            target=doc,
            detail='File phien ban van ban dang tro sang cong ty khac.',
        )
        try:
            with ver.output_file.open('rb') as f:
                file_bytes = f.read()
            new_ver.output_file.save(
                f'{_ascii_safe_name(doc.title)}_v{new_ver_num}.docx',
                ContentFile(file_bytes), save=False
            )
        except Exception:
            pass

    new_ver.save()

    
    doc.version_number = new_ver_num
    doc.content = ver.content
    if new_ver.output_file:
        doc.output_file = new_ver.output_file
    else:
        doc.output_file = None
    update_fields = ['version_number', 'content', 'output_file', 'updated_at']
    if doc.visibility == 'group':
        doc.share_status = SHARE_PENDING_LEADER
        update_fields.append('share_status')
    elif doc.visibility == 'public':
        doc.share_status = SHARE_ACTIVE if request.user.is_superuser else SHARE_PENDING_ADMIN
        update_fields.append('share_status')
    doc.save(update_fields=update_fields)
    if doc.output_file:
        schedule_document_preview_regeneration(doc)

    return Response(DocumentDetailSerializer(doc, context={'request': request}).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def document_version_toggle_hide(request, pk, ver_id):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `document_version_toggle_hide` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem quan ly du lieu phien ban theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can quan ly du lieu phien ban tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac quan ly du lieu phien ban tren giao dien.
    """
    from documents.models import DocumentVersion
    from ..serializers.documents import DocumentVersionSerializer
    qs = get_document_detail_queryset(request.user)
    doc = get_object_or_404(qs, pk=pk)
    if is_document_edit_locked(doc):
        return _document_edit_locked_response(doc)
    if not can_edit_document(request.user, doc):
        return Response({'detail': 'Khong co quyen sua.'}, status=status.HTTP_403_FORBIDDEN)
    ver = get_object_or_404(DocumentVersion, pk=ver_id, document=doc)
    ver.is_hidden = not ver.is_hidden
    ver.save(update_fields=['is_hidden'])
    return Response(DocumentVersionSerializer(ver).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def document_upload(request):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `document_upload` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem nhan tep tu frontend va luu xuong backend theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can nhan tep tu frontend va luu xuong backend tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac nhan tep tu frontend va luu xuong backend tren giao dien.
    """
    from django.core.files.base import ContentFile
    title = request.data.get('title', '').strip()
    docx_file = request.FILES.get('docx_file')
    if not title or not docx_file:
        return Response({'detail': 'Cáº§n title vÃ  docx_file.'}, status=status.HTTP_400_BAD_REQUEST)
    if not docx_file.name.lower().endswith('.docx'):
        return Response({'detail': 'Chá»‰ há»— trá»£ .docx.'}, status=status.HTTP_400_BAD_REQUEST)
    text_content = _extract_text_from_docx(docx_file)
    doc = Document(
        title=title, content=text_content, owner=request.user,
        source_type=SOURCE_UPLOADED, status=DOC_STATUS_DRAFT,
        visibility='private',
        share_status=SHARE_ACTIVE,
        tags=[],
    )
    docx_file.seek(0)
    doc.output_file.save(f'{_ascii_safe_name(title)}.docx', ContentFile(docx_file.read()), save=False)
    doc.save()
    schedule_document_preview_regeneration(doc)
    return Response(
        DocumentDetailSerializer(doc, context={'request': request}).data,
        status=status.HTTP_201_CREATED,
    )

def _accessible_mailbox_threads(user):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_accessible_mailbox_threads` la helper noi bo cua lop API trong file `api/views/documents.py`, chiu trach nhiem danh gia pham vi quyen truy cap truoc khi endpoint chinh phan hoi.
    Vai tro cua no trong frontend: Frontend Flutter khong goi truc tiep helper nay; endpoint cung file dung no khi giao dien can danh gia pham vi quyen truy cap nhung khong nen tu xu ly o client.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Thuong duoc cac ham public nhu `document_list_create`, `document_detail_view`, `document_download` goi lai.
    Tac dung: Co lap rieng buoc danh gia pham vi quyen truy cap de cac endpoint cung file tai su dung dung mot quy tac.
    """
    if not user or not user.is_authenticated:
        return DocumentMailboxThread.objects.none()
    if user.is_superuser and get_user_company(user) is None:
        return DocumentMailboxThread.objects.all()
    queryset = DocumentMailboxThread.objects.filter(
        models.Q(created_by=user)
        | models.Q(entries__forwarded_to=user)
        | models.Q(entries__forwarded_by=user)
    ).select_related(
        'document',
        'created_by',
        'source_signed_pdf',
        'last_action_by',
    ).prefetch_related(
        'entries__forwarded_by',
        'entries__forwarded_to',
        'entries__signed_pdf',
        'entries__actioned_by',
    ).distinct()
    return filter_queryset_by_current_company(queryset, user)

def _accessible_mailbox_entries(user):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_accessible_mailbox_entries` la helper noi bo cua lop API trong file `api/views/documents.py`, chiu trach nhiem danh gia pham vi quyen truy cap truoc khi endpoint chinh phan hoi.
    Vai tro cua no trong frontend: Frontend Flutter khong goi truc tiep helper nay; endpoint cung file dung no khi giao dien can danh gia pham vi quyen truy cap nhung khong nen tu xu ly o client.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Thuong duoc cac ham public nhu `document_list_create`, `document_detail_view`, `document_download` goi lai.
    Tac dung: Co lap rieng buoc danh gia pham vi quyen truy cap de cac endpoint cung file tai su dung dung mot quy tac.
    """
    if not user or not user.is_authenticated:
        return DocumentMailboxEntry.objects.none()
    if user.is_superuser and get_user_company(user) is None:
        return DocumentMailboxEntry.objects.all()
    queryset = DocumentMailboxEntry.objects.filter(
        models.Q(forwarded_to=user) | models.Q(forwarded_by=user) | models.Q(thread__created_by=user)
    ).select_related(
        'thread',
        'thread__document',
        'forwarded_by',
        'forwarded_to',
        'signed_pdf',
        'actioned_by',
    ).distinct()
    return filter_queryset_by_current_company(queryset, user)

def _resolve_forward_recipients(actor, user_ids):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_resolve_forward_recipients` la helper noi bo cua lop API trong file `api/views/documents.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai truoc khi endpoint chinh phan hoi.
    Vai tro cua no trong frontend: Frontend Flutter khong goi truc tiep helper nay; endpoint cung file dung no khi giao dien can thuc hien phan xu ly chuyen trach cua symbol hien tai nhung khong nen tu xu ly o client.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Thuong duoc cac ham public nhu `document_list_create`, `document_detail_view`, `document_download` goi lai.
    Tac dung: Co lap rieng buoc thuc hien phan xu ly chuyen trach cua symbol hien tai de cac endpoint cung file tai su dung dung mot quy tac.
    """
    user_ids = [int(value) for value in user_ids if str(value).strip()]
    recipients_qs = User.objects.filter(id__in=user_ids, is_active=True)
    actor_company = get_user_company(actor)
    if actor_company is not None:
        recipients_qs = recipients_qs.filter(
            company_membership__company=actor_company,
            company_membership__is_active=True,
        )
    recipients = list(recipients_qs.distinct())
    if len(recipients) != len(set(user_ids)):
        raise MailboxFlowError('Danh sach nguoi nhan khong hop le, da bi khoa hoac khac cong ty.')
    return recipients

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def document_forward(request, pk):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `document_forward` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi van ban theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can xu ly du lieu hoac thao tac lien quan toi van ban tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac xu ly du lieu hoac thao tac lien quan toi van ban tren giao dien.
    """
    document = get_object_or_404(get_accessible_documents(request.user), pk=pk)
    try:
        recipients = _resolve_forward_recipients(request.user, request.data.get('user_ids') or [])
        thread = forward_document(
            document,
            request.user,
            recipients,
            note=str(request.data.get('note') or '').strip(),
        )
    except MailboxFlowError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(DocumentMailboxThreadSerializer(thread, context={'request': request}).data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mailbox_thread_list(request):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `mailbox_thread_list` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem tra danh sach du lieu theo bo loc hien tai theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can tra danh sach du lieu theo bo loc hien tai tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac tra danh sach du lieu theo bo loc hien tai tren giao dien.
    """
    threads = _accessible_mailbox_threads(request.user)
    q = (request.GET.get('q') or '').strip()
    status_filter = (request.GET.get('status') or '').strip()
    if q:
        threads = threads.filter(
            models.Q(document__title__icontains=q)
            | models.Q(created_by__username__icontains=q)
            | models.Q(created_by__first_name__icontains=q)
            | models.Q(created_by__last_name__icontains=q)
            | models.Q(entries__forwarded_by__username__icontains=q)
            | models.Q(entries__forwarded_to__username__icontains=q)
        ).distinct()
    if status_filter:
        threads = threads.filter(status=status_filter)
    return Response(DocumentMailboxThreadSerializer(threads.order_by('-updated_at'), many=True, context={'request': request}).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mailbox_thread_detail(request, thread_id):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `mailbox_thread_detail` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem tra du lieu chi tiet cho mot doi tuong cu the theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can tra du lieu chi tiet cho mot doi tuong cu the tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac tra du lieu chi tiet cho mot doi tuong cu the tren giao dien.
    """
    thread = get_object_or_404(_accessible_mailbox_threads(request.user), pk=thread_id)
    return Response(DocumentMailboxThreadSerializer(thread, context={'request': request}).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mailbox_thread_verify(request, thread_id):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `mailbox_thread_verify` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem xac minh tinh hop le hoac toan ven theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can xac minh tinh hop le hoac toan ven tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac xac minh tinh hop le hoac toan ven tren giao dien.
    """
    thread = get_object_or_404(_accessible_mailbox_threads(request.user), pk=thread_id)
    CompanyRuntimeGuard.assert_file_field(
        thread.source_signed_pdf.signed_pdf_file,
        target=thread,
        detail='File hom thu dang tro sang cong ty khac.',
    )
    try:
        report = mailbox_thread_integrity_report(thread)
    except MailboxFlowError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(report, status=status.HTTP_200_OK if report.get('is_safe') else status.HTTP_409_CONFLICT)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mailbox_thread_preview_pdf(request, thread_id):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `mailbox_thread_preview_pdf` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem chuan bi noi dung xem truoc theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can chuan bi noi dung xem truoc tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac chuan bi noi dung xem truoc tren giao dien.
    """
    from django.http import FileResponse
    from urllib.parse import quote

    thread = get_object_or_404(_accessible_mailbox_threads(request.user), pk=thread_id)
    CompanyRuntimeGuard.assert_file_field(
        thread.source_signed_pdf.signed_pdf_file,
        target=thread,
        detail='File hom thu dang tro sang cong ty khac.',
    )
    try:
        report = mailbox_thread_integrity_report(thread)
    except MailboxFlowError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    if not report.get('is_safe'):
        return Response({'detail': report.get('summary')}, status=status.HTTP_409_CONFLICT)
    response = FileResponse(thread.source_signed_pdf.signed_pdf_file.open('rb'), content_type='application/pdf')
    name = quote(f'{thread.document.title}_mailbox.pdf')
    response['Content-Disposition'] = f'inline; filename=\"{name}\"'
    return response

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mailbox_entry_forward(request, entry_id):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `mailbox_entry_forward` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem xu ly luong hom thu hoac diem chuyen tiep tai lieu theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can xu ly luong hom thu hoac diem chuyen tiep tai lieu tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac xu ly luong hom thu hoac diem chuyen tiep tai lieu tren giao dien.
    """
    entry = get_object_or_404(_accessible_mailbox_entries(request.user), pk=entry_id)
    try:
        recipients = _resolve_forward_recipients(request.user, request.data.get('user_ids') or [])
        thread = forward_document(
            entry.thread.document,
            request.user,
            recipients,
            note=str(request.data.get('note') or '').strip(),
            parent_entry=entry,
        )
    except MailboxFlowError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(DocumentMailboxThreadSerializer(thread, context={'request': request}).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mailbox_entry_complete(request, entry_id):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `mailbox_entry_complete` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem xu ly luong hom thu hoac diem chuyen tiep tai lieu theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can xu ly luong hom thu hoac diem chuyen tiep tai lieu tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac xu ly luong hom thu hoac diem chuyen tiep tai lieu tren giao dien.
    """
    entry = get_object_or_404(_accessible_mailbox_entries(request.user), pk=entry_id)
    try:
        complete_mailbox_entry(entry, request.user, str(request.data.get('reason') or '').strip())
    except MailboxFlowError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    entry.refresh_from_db()
    return Response({'detail': entry.thread.last_action_summary, 'thread_id': entry.thread_id, 'entry_id': entry.id})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mailbox_entry_reject(request, entry_id):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `mailbox_entry_reject` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem tu choi mot yeu cau nghiep vu theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can tu choi mot yeu cau nghiep vu tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac tu choi mot yeu cau nghiep vu tren giao dien.
    """
    entry = get_object_or_404(_accessible_mailbox_entries(request.user), pk=entry_id)
    try:
        reject_mailbox_entry(entry, request.user, str(request.data.get('reason') or '').strip())
    except MailboxFlowError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    entry.refresh_from_db()
    return Response({'detail': entry.thread.last_action_summary, 'thread_id': entry.thread_id, 'entry_id': entry.id})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mailbox_entry_sign(request, entry_id):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `mailbox_entry_sign` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem thuc hien buoc ky so hoac ghi nhan chu ky theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can thuc hien buoc ky so hoac ghi nhan chu ky tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac thuc hien buoc ky so hoac ghi nhan chu ky tren giao dien.
    """
    entry = get_object_or_404(_accessible_mailbox_entries(request.user), pk=entry_id)
    try:
        result = ensure_mailbox_entry_signing_task(entry, request.user)
    except MailboxFlowError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    task = result.get('task')
    packet = result.get('packet')
    signed_pdf = result.get('signed_pdf')
    payload = {
        'detail': (
            'Nguoi nhan da ky xong phien ban hien tai cua van ban.'
            if result.get('already_signed')
            else 'Tac vu ky trong hom thu da san sang.'
        ),
        'created': bool(result.get('created')),
        'already_signed': bool(result.get('already_signed')),
        'task': SigningTaskSerializer(task).data if task is not None else None,
        'packet_id': packet.id if packet is not None else None,
        'signed_pdf_id': signed_pdf.id if signed_pdf is not None else None,
    }
    return Response(payload, status=status.HTTP_201_CREATED if result.get('created') else status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mailbox_entry_verify(request, entry_id):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `mailbox_entry_verify` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem xac minh tinh hop le hoac toan ven theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can xac minh tinh hop le hoac toan ven tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac xac minh tinh hop le hoac toan ven tren giao dien.
    """
    entry = get_object_or_404(_accessible_mailbox_entries(request.user), pk=entry_id)
    CompanyRuntimeGuard.assert_file_field(
        entry.signed_pdf.signed_pdf_file,
        target=entry,
        detail='File hom thu dang tro sang cong ty khac.',
    )
    try:
        report = mailbox_integrity_report(entry)
    except MailboxFlowError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(report, status=status.HTTP_200_OK if report.get('is_safe') else status.HTTP_409_CONFLICT)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mailbox_entry_preview_pdf(request, entry_id):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `mailbox_entry_preview_pdf` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem chuan bi noi dung xem truoc theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can chuan bi noi dung xem truoc tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac chuan bi noi dung xem truoc tren giao dien.
    """
    from django.http import FileResponse
    from urllib.parse import quote

    entry = get_object_or_404(_accessible_mailbox_entries(request.user), pk=entry_id)
    CompanyRuntimeGuard.assert_file_field(
        entry.signed_pdf.signed_pdf_file,
        target=entry,
        detail='File hom thu dang tro sang cong ty khac.',
    )
    try:
        report = mailbox_integrity_report(entry)
    except MailboxFlowError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    if not report.get('is_safe'):
        return Response({'detail': report.get('summary')}, status=status.HTTP_409_CONFLICT)
    response = FileResponse(entry.signed_pdf.signed_pdf_file.open('rb'), content_type='application/pdf')
    name = quote(f'{entry.thread.document.title}_mailbox.pdf')
    response['Content-Disposition'] = f'inline; filename=\"{name}\"'
    return response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def template_content_html(request, pk):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `template_content_html` la endpoint hoac diem vao REST cua file `api/views/documents.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi mau van ban theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can xu ly du lieu hoac thao tac lien quan toi mau van ban tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_document_edit_locked_response`, `_normalize_search_terms`, `_build_document_search_query` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac xu ly du lieu hoac thao tac lien quan toi mau van ban tren giao dien.
    """
    import mammoth

    tmpl = get_object_or_404(get_template_detail_queryset(request.user), pk=pk)

    if tmpl.content and str(tmpl.content).strip():
        html_body = tmpl.content
    elif tmpl.source_type == 'docx' and tmpl.docx_file:
        CompanyRuntimeGuard.assert_file_field(
            tmpl.docx_file,
            target=tmpl,
            detail='File DOCX cua mau dang tro sang cong ty khac.',
        )
        try:
            with tmpl.docx_file.open('rb') as f:
                result = mammoth.convert_to_html(f)
            html_body = result.value
        except Exception as exc:
            html_body = f'<p style="color:red">Loi chuyen doi: {exc}</p>'
    else:
        html_body = '<p style="color:#888">Khong co noi dung.</p>'

    full_html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Times New Roman', Times, serif;
    font-size: 14pt;
    background: #e0e0e0;
    padding: 24px;
    line-height: 1.6;
  }}
  .page {{
    background: #ffffff;
    max-width: 210mm;
    min-height: 297mm;
    margin: 0 auto;
    padding: 20mm 25mm 20mm 30mm;
    box-shadow: 0 2px 12px rgba(0,0,0,0.18);
  }}
  h1,h2,h3,h4 {{ font-family: 'Times New Roman', Times, serif; }}
  table {{ border-collapse: collapse; width: 100%; margin: 8px 0; }}
  td, th {{ border: 1px solid #888; padding: 4px 8px; }}
  p {{ margin-bottom: 6px; }}
</style>
</head>
<body>
  <div class="page">{html_body}</div>
</body>
</html>"""
    return Response({'html': full_html})

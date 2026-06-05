from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.company_lifecycle_services import (
    CompanyHardDeleteError,
    hard_delete_company,
    list_deleted_companies,
    restore_company_from_trash,
    soft_delete_company,
)
from accounts.company_services import (
    build_company_credentials_workbook_bytes,
    build_company_import_template_bytes,
    commit_company_import,
    create_company_from_payload,
    preview_company_import,
    reset_company_bootstrap_admin,
    serialize_company_credential_rows,
)
from accounts.models import Company, CompanyAIConfig, CompanyImportBatch, CompanyStatus
from accounts.tenancy import is_platform_admin
from ..serializers.companies import (
    CompanyAIConfigSerializer,
    CompanyCreateUpdateSerializer,
    CompanyDetailSerializer,
    CompanySummarySerializer,
)


def _company_creation_payload(result):
    return {
        'company': CompanyDetailSerializer(result.company).data,
        'bootstrap_admin': {
            'username': result.bootstrap_admin.membership.local_username,
            'email': result.bootstrap_admin.user.email,
            'password': result.bootstrap_admin.raw_password,
        },
        'created_group_count': result.created_group_count,
        'created_employee_count': result.created_employee_count,
        'credential_rows': serialize_company_credential_rows(result.credential_rows),
    }


def _platform_forbidden_response():
    return Response({'detail': 'Chi platform admin moi duoc thao tac.'}, status=status.HTTP_403_FORBIDDEN)


def _require_platform_admin(request):
    if not is_platform_admin(request.user):
        return _platform_forbidden_response()
    return None


def _company_trash_payload(item):
    company = item.company
    return {
        **CompanySummarySerializer(company).data,
        'bootstrap_admin_username': item.bootstrap_admin_username,
        'bootstrap_admin_email': item.bootstrap_admin_email,
        'deleted_at': company.updated_at,
    }


@api_view(['GET'])
@permission_classes([AllowAny])
def public_company_suggest(request):
    query = str(request.query_params.get('q') or '').strip()
    if len(query) < 1:
        return Response([])

    companies = list(
        Company.objects.filter(status=CompanyStatus.ACTIVE).filter(
            Q(name__icontains=query) | Q(code__icontains=query)
        )[:20]
    )
    lowered = query.casefold()
    companies.sort(
        key=lambda company: (
            0 if company.name.casefold().startswith(lowered) or company.code.casefold().startswith(lowered) else 1,
            company.name.casefold(),
        )
    )
    return Response(
        [
            {
                'id': company.id,
                'code': company.code,
                'slug': company.slug,
                'name': company.name,
            }
            for company in companies[:10]
        ]
    )


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def platform_company_list_create(request):
    forbidden = _require_platform_admin(request)
    if forbidden is not None:
        return forbidden

    if request.method == 'GET':
        query = str(request.query_params.get('q') or '').strip()
        status_filter = str(request.query_params.get('status') or '').strip().lower()
        companies = Company.objects.exclude(status=CompanyStatus.DELETED).order_by('name', 'code')
        if query:
            companies = companies.filter(Q(name__icontains=query) | Q(code__icontains=query))
        if status_filter:
            companies = companies.filter(status=status_filter)
        return Response(CompanySummarySerializer(companies, many=True).data)

    serializer = CompanyCreateUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = {
        'company': serializer.validated_data,
        'groups': request.data.get('groups') or [],
        'employees': request.data.get('employees') or [],
    }
    try:
        result = create_company_from_payload(payload, actor=request.user)
    except ValueError as exc:
        if isinstance(exc.args[0], list):
            errors = [str(item) for item in exc.args[0] if str(item).strip()]
            return Response(
                {
                    'detail': errors[0] if errors else 'Du lieu tao cong ty thu cong khong hop le.',
                    'errors': errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(_company_creation_payload(result), status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def platform_company_detail(request, pk):
    forbidden = _require_platform_admin(request)
    if forbidden is not None:
        return forbidden

    company = get_object_or_404(Company, pk=pk)

    if request.method == 'GET':
        return Response(CompanyDetailSerializer(company).data)

    if request.method == 'DELETE':
        soft_delete_company(company, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = CompanyCreateUpdateSerializer(
        data=request.data,
        context={'company': company},
        partial=True,
    )
    serializer.is_valid(raise_exception=True)
    for field in (
        'code',
        'name',
        'status',
        'description',
        'industry',
        'address',
        'email',
        'phone',
        'website',
        'company_context',
    ):
        if field in serializer.validated_data:
            setattr(company, field, serializer.validated_data[field])
    company.updated_by = request.user
    company.save()
    CompanyAIConfig.seed_defaults(company, actor=request.user)
    return Response(CompanyDetailSerializer(company).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def platform_company_trash(request):
    forbidden = _require_platform_admin(request)
    if forbidden is not None:
        return forbidden

    query = str(request.query_params.get('q') or '').strip()
    items = list_deleted_companies(query=query)
    return Response([_company_trash_payload(item) for item in items])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def platform_company_restore(request, pk):
    forbidden = _require_platform_admin(request)
    if forbidden is not None:
        return forbidden

    company = get_object_or_404(Company, pk=pk)
    try:
        restore_company_from_trash(company, actor=request.user)
    except CompanyHardDeleteError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(CompanyDetailSerializer(company).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def platform_company_hard_delete(request, pk):
    forbidden = _require_platform_admin(request)
    if forbidden is not None:
        return forbidden

    company = get_object_or_404(Company, pk=pk)
    try:
        result = hard_delete_company(
            company,
            platform_admin_user=request.user,
            platform_admin_password=str(request.data.get('platform_admin_password') or ''),
        )
    except CompanyHardDeleteError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(
        {
            'company_id': result.company_id,
            'company_code': result.company_code,
            'company_name': result.company_name,
            'deleted_user_count': result.deleted_user_count,
            'deleted_membership_count': result.deleted_membership_count,
        }
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def platform_admin_change_password(request):
    """Doi mat khau cho admin quan tri nen tang (yeu cau mat khau cu)."""
    forbidden = _require_platform_admin(request)
    if forbidden is not None:
        return forbidden

    old_password = str(request.data.get('old_password') or '')
    new_password = str(request.data.get('new_password') or '')

    if not request.user.check_password(old_password):
        return Response(
            {'detail': 'Mat khau cu khong dung.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if len(new_password) < 6:
        return Response(
            {'detail': 'Mat khau moi phai co it nhat 6 ky tu.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if new_password == old_password:
        return Response(
            {'detail': 'Mat khau moi phai khac mat khau cu.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    request.user.set_password(new_password)
    request.user.save(update_fields=['password'])
    return Response({'detail': 'Da doi mat khau thanh cong.'})


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def platform_company_ai_config(request, pk):
    forbidden = _require_platform_admin(request)
    if forbidden is not None:
        return forbidden

    company = get_object_or_404(Company, pk=pk)
    config = CompanyAIConfig.seed_defaults(company, actor=request.user)
    if request.method == 'GET':
        return Response(CompanyAIConfigSerializer(config).data)
    serializer = CompanyAIConfigSerializer(config, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save(updated_by=request.user)
    if 'company_context' in serializer.validated_data:
        company.company_context = serializer.validated_data['company_context']
        company.updated_by = request.user
        company.save(update_fields=['company_context', 'updated_by', 'updated_at'])
    return Response(CompanyAIConfigSerializer(config).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def platform_company_import_preview(request):
    forbidden = _require_platform_admin(request)
    if forbidden is not None:
        return forbidden

    excel_file = request.FILES.get('excel_file')
    if excel_file is None:
        return Response({'detail': 'Can file excel_file.'}, status=status.HTTP_400_BAD_REQUEST)
    batch = preview_company_import(excel_file, actor=request.user)
    return Response(
        {
            'batch_id': batch.id,
            'status': batch.status,
            'preview_payload': batch.preview_payload,
            'validation_errors': batch.validation_errors,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def platform_company_import_batches(request):
    forbidden = _require_platform_admin(request)
    if forbidden is not None:
        return forbidden

    batches = CompanyImportBatch.objects.select_related('target_company', 'uploaded_by').order_by('-created_at')[:50]
    return Response(
        [
            {
                'id': batch.id,
                'status': batch.status,
                'source_type': batch.source_type,
                'target_company_id': batch.target_company_id,
                'target_company_name': batch.target_company.name if batch.target_company_id else '',
                'validation_error_count': len(batch.validation_errors or []),
                'commit_summary': batch.commit_summary or {},
                'created_at': batch.created_at,
            }
            for batch in batches
        ]
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def platform_company_import_commit(request, batch_id):
    forbidden = _require_platform_admin(request)
    if forbidden is not None:
        return forbidden

    batch = get_object_or_404(CompanyImportBatch, pk=batch_id)
    try:
        result = commit_company_import(batch, actor=request.user)
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    payload = _company_creation_payload(result)
    payload['batch_id'] = batch.id
    return Response(payload)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def platform_company_bootstrap_reset(request, pk):
    forbidden = _require_platform_admin(request)
    if forbidden is not None:
        return forbidden

    company = get_object_or_404(Company, pk=pk)
    bootstrap = reset_company_bootstrap_admin(company, actor=request.user)
    return Response(
        {
            'username': bootstrap.membership.local_username,
            'email': bootstrap.user.email,
            'password': bootstrap.raw_password,
            'must_change_password': bootstrap.membership.must_change_password,
        }
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def platform_company_import_template(request):
    forbidden = _require_platform_admin(request)
    if forbidden is not None:
        return forbidden

    response = HttpResponse(
        build_company_import_template_bytes(include_company_sheet=True),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="company_import_template.xlsx"'
    return response


# === BEGIN R5: platform company dashboard + activity ===
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def platform_company_dashboard(request, pk):
    forbidden = _require_platform_admin(request)
    if forbidden is not None:
        return forbidden
    company = get_object_or_404(Company, pk=pk)
    from accounts.services.company_stats import compute_company_stats
    return Response(compute_company_stats(company))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def platform_company_activity(request, pk):
    forbidden = _require_platform_admin(request)
    if forbidden is not None:
        return forbidden
    company = get_object_or_404(Company, pk=pk)
    try:
        limit = int(request.query_params.get('limit') or 20)
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(limit, 100))

    activities: list[dict] = []
    # Gop tu nhieu nguon: backup created, restored; import batches; user memberships added.
    try:
        from company_backups.models import CompanyBackup
        for b in CompanyBackup.objects.filter(company=company).order_by('-created_at')[:limit]:
            activities.append({
                'at': b.created_at.isoformat(),
                'actor': (b.created_by.get_full_name() or b.created_by.username) if b.created_by else '',
                'action': 'backup_created',
                'detail': f'Backup #{b.id} ({b.kind}) status={b.status}',
                'target_type': 'backup',
                'target_id': b.id,
            })
            if b.restored_at:
                activities.append({
                    'at': b.restored_at.isoformat(),
                    'actor': (b.restored_by.get_full_name() or b.restored_by.username) if b.restored_by else '',
                    'action': 'backup_restored',
                    'detail': f'Backup #{b.id} da khoi phuc',
                    'target_type': 'backup',
                    'target_id': b.id,
                })
    except Exception:
        pass

    try:
        for batch in company.import_batches.order_by('-created_at')[:limit]:
            activities.append({
                'at': batch.created_at.isoformat(),
                'actor': (batch.uploaded_by.get_full_name() or batch.uploaded_by.username) if getattr(batch, 'uploaded_by', None) else '',
                'action': 'import_batch',
                'detail': f'Import batch #{batch.id} status={batch.status}',
                'target_type': 'import_batch',
                'target_id': batch.id,
            })
    except Exception:
        pass

    activities.sort(key=lambda x: x['at'], reverse=True)
    return Response({'activities': activities[:limit]})
# === END R5 ===


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def platform_company_credentials_workbook(request):
    forbidden = _require_platform_admin(request)
    if forbidden is not None:
        return forbidden

    company_name = str(request.data.get('company_name') or '').strip()
    company_code = str(request.data.get('company_code') or '').strip().lower()
    credential_rows = request.data.get('credential_rows') or []
    if not company_name or not company_code:
        return Response({'detail': 'Can company_name va company_code.'}, status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(credential_rows, list) or not credential_rows:
        return Response({'detail': 'Can danh sach credential_rows hop le.'}, status=status.HTTP_400_BAD_REQUEST)

    response = HttpResponse(
        build_company_credentials_workbook_bytes(
            company_name=company_name,
            company_code=company_code,
            credential_rows=credential_rows,
        ),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    safe_code = company_code.replace(' ', '_') or 'company'
    response['Content-Disposition'] = f'attachment; filename="company_credentials_{safe_code}.xlsx"'
    return response

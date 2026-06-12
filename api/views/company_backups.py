import logging
import os
from pathlib import Path

from django.conf import settings as dj_settings
from django.http import FileResponse, Http404, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.tenancy import get_user_company, is_company_admin
from company_backups.logging_utils import (
    format_log_message, password_log_value,
)
from company_backups.models import (
    CompanyBackup, KIND_MANUAL, STATUS_READY,
    SIGNATURE_STATUS_SIGNED, SIGNATURE_STATUS_INVALID,
)
from company_backups.services.components import (
    ALL_COMPONENTS, COMPONENT_LABELS,
)
from company_backups.services.crypto import (
    decrypt_to_response, resolve_master_key_for_meta,
)
from company_backups.services.manager import (
    create_backup, delete_backup_file, enforce_retention,
)
from company_backups.services.password import (
    ensure_settings, set_backup_password, verify_backup_password,
)
from company_backups.services.restore import (
    BackupVerificationError, RestoreError, restore_company_zip,
)
from api.serializers.company_backups import (
    CompanyBackupSerializer, CompanyBackupSettingsSerializer,
)

logger = logging.getLogger(__name__)


# Là gì: `_log_request` là helper nội bộ của module `company_backups.py`, phục vụ nhóm tạo, theo dõi, tải xuống, khôi phục và xóa bản sao lưu công ty.
# Chức năng backend: Hàm xử lý phần việc `log request` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ màn hình quản lý backup của công ty.
# Mối liên hệ: Hàm phối hợp với `log_fn`, `format_log_message` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _log_request(level: str, event: str, request, *, company=None, backup=None, **fields) -> None:
    log_fn = getattr(logger, level)
    company_id = getattr(company, 'pk', company)
    backup_id = getattr(backup, 'pk', backup)
    log_fn(format_log_message(
        event,
        method=request.method,
        path=request.path,
        user_id=getattr(request.user, 'pk', None),
        company_id=company_id,
        backup_id=backup_id,
        **fields,
    ))


# Là gì: `_admin_context` là helper nội bộ của module `company_backups.py`, phục vụ nhóm tạo, theo dõi, tải xuống, khôi phục và xóa bản sao lưu công ty.
# Chức năng backend: Hàm xử lý phần việc `admin context` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ màn hình quản lý backup của công ty.
# Mối liên hệ: Hàm phối hợp với `get_user_company`, `_log_request`, `is_company_admin` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
def _admin_context(request):
    company = get_user_company(request.user)
    if company is None or not is_company_admin(request.user):
        _log_request(
            'warning',
            'admin access denied',
            request,
            company=getattr(company, 'pk', None),
        )
        return None, Response(
            {'detail': 'Chi company admin moi duoc thao tac.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    return company, None


# Là gì: `_require_password` là helper nội bộ của module `company_backups.py`, phục vụ nhóm tạo, theo dõi, tải xuống, khôi phục và xóa bản sao lưu công ty.
# Chức năng backend: Hàm xử lý phần việc `require password` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ màn hình quản lý backup của công ty.
# Mối liên hệ: Hàm phối hợp với `ensure_settings`, `_log_request`, `request.data.get` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
def _require_password(request, company, body_key='password', header_key='HTTP_X_BACKUP_PASSWORD'):
    settings_obj = ensure_settings(company)
    if not settings_obj.has_password:
        _log_request(
            'warning',
            'password required but not configured',
            request,
            company=company,
        )
        return Response(
            {'detail': 'Chua dat mat khau backup. Vui long set password truoc.',
             'code': 'backup_password_not_set'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    raw = request.data.get(body_key) if hasattr(request, 'data') else None
    if not raw:
        raw = request.META.get(header_key, '')
    if not verify_backup_password(settings_obj, raw or ''):
        _log_request(
            'warning',
            'password verification failed',
            request,
            company=company,
            password=password_log_value(raw),
        )
        return Response(
            {'detail': 'Mat khau backup khong dung.',
             'code': 'backup_password_invalid'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    return None


# Là gì: `backup_list_create` là endpoint REST của nhóm tạo, theo dõi, tải xuống, khôi phục và xóa bản sao lưu công ty; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm truy vấn và trả về danh sách dữ liệu phù hợp, đồng thời kiểm tra đầu vào và tạo dữ liệu mới; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được màn hình quản lý backup của công ty sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_admin_context`, `CompanyBackup.objects.filter.order_by`, `request.GET.get` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def backup_list_create(request):
    company, err = _admin_context(request)
    if err:
        return err

    if request.method == 'GET':
        qs = CompanyBackup.objects.filter(company=company).order_by('-created_at')
        kind = request.GET.get('kind')
        if kind in ('auto', 'manual'):
            qs = qs.filter(kind=kind)
        items = qs[:200]
        _log_request(
            'info',
            'backup list requested',
            request,
            company=company,
            kind=kind or 'all',
            result_count=len(items),
        )
        return Response(CompanyBackupSerializer(items, many=True).data)

    # POST: tao backup thu cong.
    err = _require_password(request, company)
    if err:
        return err

    raw_components = request.data.get('components') or []
    if not isinstance(raw_components, list):
        return Response({'detail': 'components phai la mang.'}, status=status.HTTP_400_BAD_REQUEST)
    components = [c for c in raw_components if isinstance(c, str) and c in ALL_COMPONENTS]
    if not components:
        return Response({'detail': 'Phai chon it nhat 1 component.'}, status=status.HTTP_400_BAD_REQUEST)

    raw_password = (
        request.data.get('password')
        or request.META.get('HTTP_X_BACKUP_PASSWORD', '')
    )
    _log_request(
        'info',
        'backup create requested',
        request,
        company=company,
        components=components,
        password=password_log_value(raw_password),
    )
    try:
        record = create_backup(
            company=company, components=components,
            kind=KIND_MANUAL, user=request.user,
            password=raw_password or None,
            signer_user=request.user,
        )
    except Exception as exc:
        logger.exception(format_log_message(
            'backup create failed',
            method=request.method,
            path=request.path,
            user_id=getattr(request.user, 'pk', None),
            company_id=company.pk,
            components=components,
            error=str(exc),
        ))
        return Response({'detail': f'Khong tao duoc backup: {exc}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    _log_request(
        'info',
        'backup create accepted',
        request,
        company=company,
        backup=record,
        status=record.status,
        name=record.name,
        components=record.components,
    )
    return Response(CompanyBackupSerializer(record).data, status=status.HTTP_201_CREATED)


# Là gì: `backup_detail` là endpoint REST của nhóm tạo, theo dõi, tải xuống, khôi phục và xóa bản sao lưu công ty; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm đọc hoặc xử lý một bản ghi cụ thể; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được màn hình quản lý backup của công ty sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_admin_context`, `get_object_or_404`, `_log_request` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; có side effect ghi cơ sở dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def backup_detail(request, pk):
    company, err = _admin_context(request)
    if err:
        return err
    backup = get_object_or_404(CompanyBackup, pk=pk, company=company)

    if request.method == 'GET':
        _log_request(
            'info',
            'backup detail requested',
            request,
            company=company,
            backup=backup,
            status=backup.status,
            is_encrypted=backup.is_encrypted,
            signature_status=backup.signature_status,
        )
        return Response(CompanyBackupSerializer(backup).data)

    err = _require_password(request, company)
    if err:
        return err
    _log_request(
        'info',
        'backup delete requested',
        request,
        company=company,
        backup=backup,
        status=backup.status,
        file_path=backup.file_path,
    )
    delete_backup_file(backup)
    backup.delete()
    _log_request(
        'info',
        'backup deleted',
        request,
        company=company,
        backup=pk,
    )
    return Response(status=status.HTTP_204_NO_CONTENT)


# Là gì: `backup_progress` là endpoint REST của nhóm tạo, theo dõi, tải xuống, khôi phục và xóa bản sao lưu công ty; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xử lý phần việc `backup progress` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được màn hình quản lý backup của công ty sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_admin_context`, `get_object_or_404`, `logger.debug` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def backup_progress(request, pk):
    company, err = _admin_context(request)
    if err:
        return err
    backup = get_object_or_404(CompanyBackup, pk=pk, company=company)
    logger.debug(format_log_message(
        'backup progress requested',
        method=request.method,
        path=request.path,
        user_id=getattr(request.user, 'pk', None),
        company_id=company.pk,
        backup_id=backup.pk,
        status=backup.status,
        progress_percent=backup.progress_percent or 0,
        progress_stage=backup.progress_stage or '',
    ))
    return Response({
        'id': backup.pk,
        'name': backup.name,
        'status': backup.status,
        'progress_percent': backup.progress_percent or 0,
        'progress_stage': backup.progress_stage or '',
        'progress_detail': backup.progress_detail or '',
        'size_bytes': backup.size_bytes,
        'error_message': backup.error_message or '',
    })


# Là gì: `_public_key_pem_from_cert` là helper nội bộ của module `company_backups.py`, phục vụ nhóm tạo, theo dõi, tải xuống, khôi phục và xóa bản sao lưu công ty.
# Chức năng backend: Hàm xử lý phần việc `public key pem from cert` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ màn hình quản lý backup của công ty.
# Mối liên hệ: Hàm phối hợp với `x509.load_pem_x509_certificate`, `cert.public_key`, `pk.public_bytes` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _public_key_pem_from_cert(certificate_pem: str) -> bytes | None:
    """Trich xuat public key PEM tu chuoi X.509 certificate PEM."""
    if not certificate_pem:
        return None
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import serialization
        cert_bytes = certificate_pem.encode('utf-8') if isinstance(certificate_pem, str) else certificate_pem
        cert = x509.load_pem_x509_certificate(cert_bytes)
        pk = cert.public_key()
        return pk.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    except Exception:
        logger.exception('[company_backups] extract public key from cert failed')
        return None


# Là gì: `_resolve_verify_public_keys` là helper nội bộ của module `company_backups.py`, phục vụ nhóm tạo, theo dõi, tải xuống, khôi phục và xóa bản sao lưu công ty.
# Chức năng backend: Hàm xác minh tính hợp lệ hoặc tính toàn vẹn của dữ liệu, đồng thời xác định đối tượng hoặc cấu hình hiệu lực từ ngữ cảnh hiện tại; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ màn hình quản lý backup của công ty.
# Mối liên hệ: Hàm phối hợp với `UserSigningCredential.objects.filter.order_by`, `logger.exception`, `_public_key_pem_from_cert` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _resolve_verify_public_keys(backup) -> list[bytes]:
    """Tra ve danh sach public key PEM co the dung de verify chu ky backup.

    Uu tien chu ky cua created_by (UserSigningCredential active hoac la cer
    moi nhat). Fall back BACKUP_SIGNER_PUBLIC_KEY_PEM cua he thong neu co.
    """
    keys: list[bytes] = []
    try:
        from signing.models import (
            UserSigningCredential, CREDENTIAL_STATUS_ACTIVE,
        )
        signer = backup.created_by
        if signer is not None:
            creds = UserSigningCredential.objects.filter(user=signer).order_by(
                '-status', '-updated_at',
            )
            for cred in creds:
                pk = _public_key_pem_from_cert(cred.certificate_pem or '')
                if pk:
                    keys.append(pk)
                # Only need the active one (first) for primary verify;
                # other (older) cer also work voi backup cu.
                if cred.status == CREDENTIAL_STATUS_ACTIVE and len(keys) >= 1:
                    break
    except Exception:
        logger.exception('[company_backups] resolve user public key failed')
    env_key = getattr(dj_settings, 'BACKUP_SIGNER_PUBLIC_KEY_PEM', None)
    if env_key:
        keys.append(env_key.encode('utf-8') if isinstance(env_key, str) else env_key)
    return keys


# Là gì: `_verify_backup_signature_if_present` là helper nội bộ của module `company_backups.py`, phục vụ nhóm tạo, theo dõi, tải xuống, khôi phục và xóa bản sao lưu công ty.
# Chức năng backend: Hàm xác minh tính hợp lệ hoặc tính toàn vẹn của dữ liệu; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ màn hình quản lý backup của công ty.
# Mối liên hệ: Hàm phối hợp với `_resolve_verify_public_keys`, `verify_generic_file`, `Path` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _verify_backup_signature_if_present(backup, *, password: str | None = None) -> tuple[bool, str]:
    """Verify chu ky cua backup neu da co. Tra (ok, message).

    Uu tien public key trich tu UserSigningCredential cua nguoi tao backup
    (created_by). Fall back env BACKUP_SIGNER_PUBLIC_KEY_PEM.
    Voi backup encrypted: cần decrypt truoc — neu encryption_meta co
    pwd_salt thi can `password` cua admin.
    """
    if backup.signature_status != SIGNATURE_STATUS_SIGNED or not backup.signature_path:
        return True, 'Backup khong co chu ky de verify (bo qua).'
    keys = _resolve_verify_public_keys(backup)
    if not keys:
        return False, (
            'Khong tim thay public key de verify. '
            'Admin can co UserSigningCredential, hoac he thong can BACKUP_SIGNER_PUBLIC_KEY_PEM.'
        )
    from signing.services import verify_generic_file
    sig_path = backup.signature_path
    if not sig_path:
        return False, 'Backup khong co file chu ky tren disk.'

    # Là gì: `_try_keys` là hàm cục bộ bên trong `_verify_backup_signature_if_present`, chỉ phục vụ bước xử lý nội bộ của nhóm tạo, theo dõi, tải xuống, khôi phục và xóa bản sao lưu công ty.
    # Chức năng backend: Hàm xử lý phần việc `try keys` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
    # Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ màn hình quản lý backup của công ty.
    # Mối liên hệ: Hàm phối hợp với `verify_generic_file` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
    # Bản chất và tác dụng: callback cục bộ chỉ có hiệu lực trong hàm bao ngoài; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
    def _try_keys(file_path: str) -> tuple[bool, str]:
        last_err = ''
        for k in keys:
            try:
                ok = verify_generic_file(file_path, sig_path, k)
                if ok:
                    return True, 'OK'
                last_err = 'Chu ky khong khop voi public key cua admin.'
            except Exception as exc:
                last_err = f'Loi verify: {exc}'
        return False, last_err or 'Khong public key nao khop.'

    if backup.is_encrypted:
        import tempfile, shutil
        tmp_dir = Path(tempfile.mkdtemp(prefix='cbk_verify_'))
        plain_path = tmp_dir / 'plaintext.zip'
        try:
            from company_backups.services.crypto import (
                decrypt_file_stream, resolve_master_key_for_meta,
            )
            env_master = getattr(dj_settings, 'BACKUP_ENCRYPTION_MASTER_KEY', None)
            try:
                master_key = resolve_master_key_for_meta(
                    backup.encryption_meta or {}, env_master, password,
                )
            except ValueError as exc:
                return False, str(exc)
            try:
                decrypt_file_stream(
                    str(Path(dj_settings.MEDIA_ROOT) / backup.file_path),
                    str(plain_path),
                    master_key,
                    backup.encryption_meta or {},
                    company_id=backup.company_id,
                )
            except Exception as exc:
                return False, f'Decrypt loi truoc verify: {exc}'
            return _try_keys(str(plain_path))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
    else:
        return _try_keys(str(Path(dj_settings.MEDIA_ROOT) / backup.file_path))


# Là gì: `backup_download` là endpoint REST của nhóm tạo, theo dõi, tải xuống, khôi phục và xóa bản sao lưu công ty; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm chuẩn bị và trả tệp cho phía client tải xuống; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được màn hình quản lý backup của công ty sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_admin_context`, `get_object_or_404`, `_require_password` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; có side effect ghi cơ sở dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def backup_download(request, pk):
    company, err = _admin_context(request)
    if err:
        return err
    backup = get_object_or_404(CompanyBackup, pk=pk, company=company)

    err = _require_password(request, company)
    if err:
        return err
    if backup.status != STATUS_READY:
        return Response({'detail': 'Backup chua san sang de tai.'}, status=status.HTTP_400_BAD_REQUEST)

    media_root = Path(getattr(dj_settings, 'MEDIA_ROOT', '') or '.')
    full = media_root / backup.file_path
    if not full.exists() or not full.is_file():
        _log_request(
            'warning',
            'backup download missing file',
            request,
            company=company,
            backup=backup,
            file_path=str(full),
        )
        raise Http404('Backup file missing on disk.')

    _log_request(
        'info',
        'backup download requested',
        request,
        company=company,
        backup=backup,
        status=backup.status,
        is_encrypted=backup.is_encrypted,
        signature_status=backup.signature_status,
        file_path=backup.file_path,
        size_bytes=backup.size_bytes,
    )

    # Verify chu ky neu co
    if backup.signature_status == SIGNATURE_STATUS_SIGNED and backup.signature_path:
        _pw_for_verify = (
            request.data.get('password') if hasattr(request, 'data') else None
        ) or request.META.get('HTTP_X_BACKUP_PASSWORD', '')
        ok, message = _verify_backup_signature_if_present(
            backup, password=_pw_for_verify or None,
        )
        if not ok:
            backup.signature_status = SIGNATURE_STATUS_INVALID
            backup.save(update_fields=['signature_status'])
            _log_request(
                'warning',
                'backup download blocked by signature verification',
                request,
                company=company,
                backup=backup,
                verify_message=message,
            )
            return Response(
                {'detail': f'Backup nay co dau hieu bi thay doi. Khong the tai. ({message})'},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        _log_request(
            'info',
            'backup download signature verified',
            request,
            company=company,
            backup=backup,
            verify_message=message,
        )

    backup.downloaded_at = timezone.now()
    backup.save(update_fields=['downloaded_at'])

    # Encrypted -> streaming decrypt
    if backup.is_encrypted:
        env_master_key = getattr(dj_settings, 'BACKUP_ENCRYPTION_MASTER_KEY', None)
        raw_password = (
            request.data.get('password') if hasattr(request, 'data') else None
        ) or request.META.get('HTTP_X_BACKUP_PASSWORD', '')
        try:
            master_key = resolve_master_key_for_meta(
                backup.encryption_meta or {},
                env_master_key,
                raw_password or None,
            )
        except ValueError as exc:
            _log_request(
                'warning',
                'backup download missing decrypt password',
                request,
                company=company,
                backup=backup,
                error=str(exc),
            )
            return Response(
                {'detail': str(exc),
                 'code': 'backup_password_required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        gen = decrypt_to_response(
            str(full), master_key, backup.encryption_meta or {},
            company_id=backup.company_id,
        )
        response = StreamingHttpResponse(gen, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{backup.name}"'
        _log_request(
            'info',
            'backup download streaming response ready',
            request,
            company=company,
            backup=backup,
            response_type='streaming_decrypt',
        )
        return response

    # Legacy plaintext
    response = FileResponse(open(full, 'rb'), as_attachment=True, filename=backup.name)
    response['Content-Type'] = 'application/zip'
    response['Content-Length'] = backup.size_bytes
    _log_request(
        'info',
        'backup download file response ready',
        request,
        company=company,
        backup=backup,
        response_type='plain_file',
    )
    return response


# Là gì: `backup_verify` là endpoint REST của nhóm tạo, theo dõi, tải xuống, khôi phục và xóa bản sao lưu công ty; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xác minh tính hợp lệ hoặc tính toàn vẹn của dữ liệu; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được màn hình quản lý backup của công ty sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_admin_context`, `get_object_or_404`, `request.META.get` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; có side effect ghi cơ sở dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def backup_verify(request, pk):
    """Endpoint verify-only chu ky backup. Khong decrypt full neu khong can."""
    company, err = _admin_context(request)
    if err:
        return err
    backup = get_object_or_404(CompanyBackup, pk=pk, company=company)
    if backup.status != STATUS_READY:
        return Response({'detail': 'Backup chua san sang.'}, status=status.HTTP_400_BAD_REQUEST)
    raw_password = (
        request.data.get('password') if hasattr(request, 'data') else None
    ) or request.META.get('HTTP_X_BACKUP_PASSWORD', '')
    _log_request(
        'info',
        'backup verify requested',
        request,
        company=company,
        backup=backup,
        is_encrypted=backup.is_encrypted,
        signature_status=backup.signature_status,
        password=password_log_value(raw_password),
    )
    ok, message = _verify_backup_signature_if_present(
        backup, password=raw_password or None,
    )
    if backup.signature_status == SIGNATURE_STATUS_SIGNED:
        new_status = SIGNATURE_STATUS_SIGNED if ok else SIGNATURE_STATUS_INVALID
        if new_status != backup.signature_status:
            backup.signature_status = new_status
            backup.save(update_fields=['signature_status'])
    _log_request(
        'info',
        'backup verify completed',
        request,
        company=company,
        backup=backup,
        ok=ok,
        signature_status=backup.signature_status,
        details=message,
    )
    return Response({
        'ok': ok,
        'details': message,
        'signature_status': backup.signature_status,
        'is_encrypted': backup.is_encrypted,
    })


# Là gì: `backup_restore` là endpoint REST của nhóm tạo, theo dõi, tải xuống, khôi phục và xóa bản sao lưu công ty; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm khôi phục dữ liệu về trạng thái hoạt động; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được màn hình quản lý backup của công ty sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_admin_context`, `get_object_or_404`, `_require_password` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def backup_restore(request, pk):
    company, err = _admin_context(request)
    if err:
        return err
    backup = get_object_or_404(CompanyBackup, pk=pk, company=company)

    err = _require_password(request, company)
    if err:
        return err
    if backup.status not in (STATUS_READY, 'restored'):
        return Response({'detail': 'Backup khong san sang de khoi phuc.'},
                        status=status.HTTP_400_BAD_REQUEST)
    raw_password = (
        request.data.get('password') if hasattr(request, 'data') else None
    ) or request.META.get('HTTP_X_BACKUP_PASSWORD', '')
    _log_request(
        'info',
        'backup restore requested',
        request,
        company=company,
        backup=backup,
        status=backup.status,
        is_encrypted=backup.is_encrypted,
        signature_status=backup.signature_status,
        password=password_log_value(raw_password),
    )
    try:
        restore_company_zip(
            company=company,
            backup=backup,
            user=request.user,
            password=raw_password or None,
            verify_public_keys=_resolve_verify_public_keys(backup),
        )
    except BackupVerificationError as exc:
        _log_request(
            'warning',
            'backup restore blocked by signature verification',
            request,
            company=company,
            backup=backup,
            error=str(exc),
        )
        return Response({'detail': str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    except RestoreError as exc:
        _log_request(
            'warning',
            'backup restore failed',
            request,
            company=company,
            backup=backup,
            error=str(exc),
        )
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:
        logger.exception(format_log_message(
            'backup restore crashed',
            method=request.method,
            path=request.path,
            user_id=getattr(request.user, 'pk', None),
            company_id=company.pk,
            backup_id=backup.pk,
            error=str(exc),
        ))
        return Response({'detail': f'Restore loi: {exc}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    _log_request(
        'info',
        'backup restore completed',
        request,
        company=company,
        backup=backup,
        status=backup.status,
    )
    return Response(CompanyBackupSerializer(backup).data)


# Là gì: `backup_settings` là endpoint REST của nhóm tạo, theo dõi, tải xuống, khôi phục và xóa bản sao lưu công ty; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xử lý phần việc `backup settings` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được màn hình quản lý backup của công ty sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_admin_context`, `ensure_settings`, `_log_request` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; có side effect ghi cơ sở dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def backup_settings(request):
    company, err = _admin_context(request)
    if err:
        return err
    settings_obj = ensure_settings(company)

    if request.method == 'GET':
        _log_request(
            'info',
            'backup settings requested',
            request,
            company=company,
            has_password=settings_obj.has_password,
        )
        return Response(CompanyBackupSettingsSerializer(settings_obj).data)

    if settings_obj.has_password:
        err = _require_password(request, company)
        if err:
            return err

    data = request.data
    if 'auto_enabled' in data:
        settings_obj.auto_enabled = bool(data.get('auto_enabled'))
    if 'auto_interval_days' in data:
        try:
            v = int(data.get('auto_interval_days'))
            if v < 1 or v > 365:
                raise ValueError
            settings_obj.auto_interval_days = v
        except (TypeError, ValueError):
            return Response({'detail': 'auto_interval_days phai la so nguyen 1-365.'},
                            status=status.HTTP_400_BAD_REQUEST)
    if 'retention_count' in data:
        try:
            v = int(data.get('retention_count'))
            if v < 1 or v > 200:
                raise ValueError
            settings_obj.retention_count = v
        except (TypeError, ValueError):
            return Response({'detail': 'retention_count phai la so nguyen 1-200.'},
                            status=status.HTTP_400_BAD_REQUEST)
    if 'notify_admin_email' in data:
        settings_obj.notify_admin_email = bool(data.get('notify_admin_email'))
    settings_obj.save()
    _log_request(
        'info',
        'backup settings updated',
        request,
        company=company,
        auto_enabled=settings_obj.auto_enabled,
        auto_interval_days=settings_obj.auto_interval_days,
        retention_count=settings_obj.retention_count,
        notify_admin_email=settings_obj.notify_admin_email,
    )
    return Response(CompanyBackupSettingsSerializer(settings_obj).data)


# Là gì: `backup_set_password` là endpoint REST của nhóm tạo, theo dõi, tải xuống, khôi phục và xóa bản sao lưu công ty; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm thiết lập giá trị hoặc trạng thái theo đầu vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được màn hình quản lý backup của công ty sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_admin_context`, `ensure_settings`, `strip` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def backup_set_password(request):
    company, err = _admin_context(request)
    if err:
        return err
    settings_obj = ensure_settings(company)
    new_pw = (request.data.get('new_password') or '').strip()
    current = (request.data.get('current_password') or '').strip()

    if settings_obj.has_password:
        if not verify_backup_password(settings_obj, current):
            _log_request(
                'warning',
                'backup set password rejected by current password',
                request,
                company=company,
                has_existing_password=True,
            )
            return Response({'detail': 'Mat khau hien tai khong dung.',
                             'code': 'backup_password_invalid'},
                            status=status.HTTP_401_UNAUTHORIZED)

    try:
        set_backup_password(settings_obj, new_pw)
    except ValueError as exc:
        _log_request(
            'warning',
            'backup set password validation failed',
            request,
            company=company,
            error=str(exc),
        )
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    _log_request(
        'info',
        'backup password updated',
        request,
        company=company,
        has_existing_password=settings_obj.has_password,
    )
    return Response({'has_password': True})


# Là gì: `backup_verify_password` là endpoint REST của nhóm tạo, theo dõi, tải xuống, khôi phục và xóa bản sao lưu công ty; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xác minh tính hợp lệ hoặc tính toàn vẹn của dữ liệu; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được màn hình quản lý backup của công ty sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_admin_context`, `ensure_settings`, `strip` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def backup_verify_password(request):
    company, err = _admin_context(request)
    if err:
        return err
    settings_obj = ensure_settings(company)
    raw = (request.data.get('password') or '').strip()
    if not settings_obj.has_password:
        _log_request(
            'info',
            'backup verify password requested without configured password',
            request,
            company=company,
        )
        return Response({'valid': False, 'has_password': False})
    valid = verify_backup_password(settings_obj, raw)
    _log_request(
        'info',
        'backup verify password completed',
        request,
        company=company,
        valid=valid,
        password=password_log_value(raw),
    )
    return Response({'valid': valid, 'has_password': True})


# Là gì: `backup_components` là endpoint REST của nhóm tạo, theo dõi, tải xuống, khôi phục và xóa bản sao lưu công ty; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xử lý phần việc `backup components` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được màn hình quản lý backup của công ty sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_admin_context`, `_log_request`, `COMPONENT_LABELS.get` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def backup_components(request):
    company, err = _admin_context(request)
    if err:
        return err
    _log_request(
        'info',
        'backup components requested',
        request,
        company=company,
        component_count=len(ALL_COMPONENTS),
    )
    return Response({
        'components': [
            {'key': key, 'label': COMPONENT_LABELS.get(key, key)}
            for key in ALL_COMPONENTS
        ],
    })

import contextlib
import json
import logging
import shutil
import tempfile
import zipfile
from pathlib import Path

from django.conf import settings
from django.core import serializers
from django.db import transaction
from django.utils import timezone

from company_backups.logging_utils import (
    format_log_message,
    password_log_value,
)
from company_backups.services.components import (
    delete_order,
    filter_queryset_for_company,
    import_order,
)
from company_backups.services.crypto import (
    decrypt_file_stream,
    looks_like_encrypted,
    resolve_master_key_for_meta,
)

logger = logging.getLogger(__name__)


# class RestoreError là ngoại lệ chung cho lỗi khôi phục backup (file thiếu, manifest sai, path traversal, decrypt lỗi...).
# vd: file backup không tồn tại trên disk -> RestoreError.
class RestoreError(Exception):
    pass


# class BackupVerificationError (con của RestoreError) báo chữ ký số của backup không khớp -> từ chối khôi phục để tránh phục hồi dữ liệu đã bị giả mạo.
# vd: zip bị sửa sau khi ký -> BackupVerificationError, không restore.
class BackupVerificationError(RestoreError):
    """Raise khi chu ky so cua backup khong khop - tu choi restore."""


# def _safe_extract_path tính đường dẫn giải nén an toàn, chặn path traversal (file trong zip cố thoát ra ngoài MEDIA_ROOT).
# vd: member '../../etc/passwd' -> RestoreError('Path traversal').
def _safe_extract_path(media_root: Path, zip_member: str) -> Path:
    target = (media_root / zip_member).resolve()
    if not str(target).startswith(str(media_root.resolve())):
        raise RestoreError(f'Path traversal detected for {zip_member}')
    return target


# def _open_backup_zip_for_restore (context manager) chuẩn bị zip để restore: xác minh chữ ký -> giải mã nếu cần (theo password/master key) -> yield đường dẫn zip plaintext; tự dọn file tạm khi thoát; chặn nếu metadata mã hóa không nhất quán.
# vd: gói mã hóa + đã ký -> giải mã ra tmp, verify chữ ký rồi mới cho restore.
@contextlib.contextmanager
def _open_backup_zip_for_restore(
    backup,
    *,
    password: str | None = None,
    verify_public_keys: list[bytes] | None = None,
):
    """Verify signature -> decrypt (neu can) -> yield path toi plaintext ZIP.

    Cleanup tmp file sau khi context thoat.
    """
    media_root = Path(getattr(settings, 'MEDIA_ROOT', '') or '.').resolve()
    zip_path = media_root / backup.file_path
    logger.info(format_log_message(
        'restore source open requested',
        backup_id=backup.pk,
        company_id=backup.company_id,
        file_path=str(zip_path),
        is_encrypted=backup.is_encrypted,
        signature_status=backup.signature_status,
        password=password_log_value(password),
    ))
    if not zip_path.exists() or not zip_path.is_file():
        logger.warning(format_log_message(
            'restore source file missing',
            backup_id=backup.pk,
            company_id=backup.company_id,
            file_path=str(zip_path),
        ))
        raise RestoreError('File backup khong ton tai tren disk.')

    public_keys = list(verify_public_keys or [])
    if not public_keys:
        env_key = getattr(settings, 'BACKUP_SIGNER_PUBLIC_KEY_PEM', None)
        if env_key:
            public_keys.append(
                env_key.encode('utf-8') if isinstance(env_key, str) else env_key,
            )

    # def _verify_or_raise xác minh chữ ký file với danh sách public key; không có key -> bỏ qua (log); không key nào khớp -> BackupVerificationError.
    # vd: chữ ký khớp 1 trong các public key -> qua; không khớp -> chặn restore.
    def _verify_or_raise(file_path: Path, message: str) -> None:
        if not public_keys:
            logger.info(format_log_message(
                'restore signature verification skipped',
                backup_id=backup.pk,
                company_id=backup.company_id,
                reason='no_public_key',
            ))
            return
        from signing.services import verify_generic_file

        for index, key in enumerate(public_keys, start=1):
            try:
                if verify_generic_file(str(file_path), backup.signature_path, key):
                    logger.info(format_log_message(
                        'restore signature verification passed',
                        backup_id=backup.pk,
                        company_id=backup.company_id,
                        verified_path=str(file_path),
                        public_key_index=index,
                    ))
                    return
            except Exception as exc:
                logger.warning(format_log_message(
                    'restore signature verification key failed',
                    backup_id=backup.pk,
                    company_id=backup.company_id,
                    verified_path=str(file_path),
                    public_key_index=index,
                    error=str(exc),
                ))
        raise BackupVerificationError(message)

    if backup.signature_path and backup.signature_status == 'signed' and not backup.is_encrypted:
        _verify_or_raise(
            zip_path,
            'Backup nay co dau hieu bi thay doi (chu ky khong hop le). Khong the khoi phuc.',
        )

    if backup.is_encrypted:
        env_master_key = getattr(settings, 'BACKUP_ENCRYPTION_MASTER_KEY', None)
        try:
            master_key = resolve_master_key_for_meta(
                backup.encryption_meta or {},
                env_master_key,
                password,
            )
        except ValueError as exc:
            logger.warning(format_log_message(
                'restore decrypt key resolution failed',
                backup_id=backup.pk,
                company_id=backup.company_id,
                error=str(exc),
            ))
            raise RestoreError(str(exc))
        tmp_dir = Path(tempfile.mkdtemp(prefix='cbk_restore_'))
        plain_path = tmp_dir / 'plaintext.zip'
        try:
            try:
                logger.info(format_log_message(
                    'restore decrypt started',
                    backup_id=backup.pk,
                    company_id=backup.company_id,
                    ciphertext_path=str(zip_path),
                    plaintext_path=str(plain_path),
                ))
                decrypt_file_stream(
                    str(zip_path),
                    str(plain_path),
                    master_key,
                    backup.encryption_meta or {},
                    company_id=backup.company_id,
                )
                logger.info(format_log_message(
                    'restore decrypt completed',
                    backup_id=backup.pk,
                    company_id=backup.company_id,
                    plaintext_path=str(plain_path),
                ))
            except Exception as exc:
                logger.warning(format_log_message(
                    'restore decrypt failed',
                    backup_id=backup.pk,
                    company_id=backup.company_id,
                    error=str(exc),
                ))
                raise RestoreError(f'Decrypt loi: {exc}')

            if backup.signature_path and backup.signature_status == 'signed':
                _verify_or_raise(
                    plain_path,
                    'Backup nay co dau hieu bi thay doi (chu ky khong hop le sau khi giai ma).',
                )

            yield plain_path
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
    else:
        if backup.encryption_meta is None and looks_like_encrypted(str(zip_path)):
            logger.warning(format_log_message(
                'restore blocked by inconsistent encryption metadata',
                backup_id=backup.pk,
                company_id=backup.company_id,
                file_path=str(zip_path),
            ))
            raise RestoreError(
                'File backup co header ma hoa nhung record khong co encryption_meta.'
            )
        yield zip_path


# def restore_company_zip khôi phục một backup vào CHÍNH công ty sở hữu (chế độ replace): kiểm tra backup thuộc công ty + manifest khớp; xóa dữ liệu cũ theo delete_order rồi nạp lại theo import_order trong 1 transaction; giải nén media (chỉ trong thư mục công ty, chống traversal); cập nhật trạng thái. Lỗi verify chữ ký -> đánh dấu signature invalid và dừng.
# vd: restore backup #5 của công ty A -> xóa data cũ của A, nạp lại từ backup, status='restored'.
def restore_company_zip(
    *,
    company,
    backup,
    user,
    password: str | None = None,
    verify_public_keys: list[bytes] | None = None,
):
    """
    Restore mot ban backup vao chinh company so huu (replace mode).
    Yeu cau backup.company == company. Manifest.company.id phai khop.
    """
    from company_backups.models import (
        STATUS_FAILED,
        STATUS_READY,
        STATUS_RESTORED,
        STATUS_RESTORING,
        SIGNATURE_STATUS_INVALID,
    )

    if backup.company_id != company.pk:
        raise RestoreError('Backup khong thuoc cong ty hien tai.')

    media_root = Path(getattr(settings, 'MEDIA_ROOT', '') or '.').resolve()
    logger.info(format_log_message(
        'restore started',
        backup_id=backup.pk,
        company_id=company.pk,
        user_id=getattr(user, 'pk', None),
        status_before=backup.status,
        is_encrypted=backup.is_encrypted,
        signature_status=backup.signature_status,
        password=password_log_value(password),
    ))
    backup.status = STATUS_RESTORING
    backup.save(update_fields=['status'])

    try:
        with _open_backup_zip_for_restore(
            backup,
            password=password,
            verify_public_keys=verify_public_keys,
        ) as zip_path:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                try:
                    manifest = json.loads(zf.read('manifest.json').decode('utf-8'))
                except (KeyError, json.JSONDecodeError) as exc:
                    raise RestoreError(f'Manifest khong hop le: {exc}')

                manifest_company = manifest.get('company') or {}
                if int(manifest_company.get('id') or 0) != int(company.pk):
                    raise RestoreError('Manifest cong ty khong khop. Backup thuoc cong ty khac.')

                components = manifest.get('components') or []
                if not components:
                    raise RestoreError('Manifest khong co components.')

                logger.info(format_log_message(
                    'restore manifest loaded',
                    backup_id=backup.pk,
                    company_id=company.pk,
                    manifest_company=manifest_company,
                    components=components,
                    record_counts=manifest.get('record_counts', {}),
                    file_count=manifest.get('file_count'),
                ))

                deleted_counts: dict[str, int] = {}
                imported_counts: dict[str, int] = {}
                extracted_media_files = 0

                with transaction.atomic():
                    for label, model in delete_order(components):
                        queryset = filter_queryset_for_company(label, company)
                        delete_count = queryset.count()
                        deleted_counts[label] = delete_count
                        queryset.delete()

                    if 'data/auth__User.json' in zf.namelist():
                        raw = zf.read('data/auth__User.json').decode('utf-8')
                        user_count = 0
                        for deserialized in serializers.deserialize('json', raw):
                            deserialized.save()
                            user_count += 1
                        imported_counts['auth.User'] = user_count

                    for label, model in import_order(components):
                        member = f'data/{label.replace(".", "__")}.json'
                        if member not in zf.namelist():
                            continue
                        raw = zf.read(member).decode('utf-8')
                        import_count = 0
                        for deserialized in serializers.deserialize('json', raw):
                            deserialized.save()
                            import_count += 1
                        imported_counts[label] = import_count

                    from accounts.storage_paths import company_storage_slug

                    slug = company_storage_slug(company)
                    allowed_prefix = f'media/companies/{slug}/'
                    for name in zf.namelist():
                        if not name.startswith('media/'):
                            continue
                        if not name.startswith(allowed_prefix):
                            continue
                        if name.endswith('/'):
                            continue
                        relative = name[len('media/'):]
                        target = _safe_extract_path(media_root, relative)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(name) as src, open(target, 'wb') as dst:
                            dst.write(src.read())
                        extracted_media_files += 1

                logger.info(format_log_message(
                    'restore data phases completed',
                    backup_id=backup.pk,
                    company_id=company.pk,
                    deleted_counts=deleted_counts,
                    imported_counts=imported_counts,
                    extracted_media_files=extracted_media_files,
                ))

        backup.status = STATUS_RESTORED
        backup.restored_at = timezone.now()
        backup.restored_by = user
        backup.error_message = ''
        backup.save(update_fields=['status', 'restored_at', 'restored_by', 'error_message'])
        logger.info(format_log_message(
            'restore completed',
            backup_id=backup.pk,
            company_id=company.pk,
            restored_by=getattr(user, 'pk', None),
            status=backup.status,
        ))
        return True

    except BackupVerificationError as exc:
        backup.status = STATUS_READY
        backup.signature_status = SIGNATURE_STATUS_INVALID
        backup.error_message = f'Verification failed: {exc}'[:2000]
        backup.save(update_fields=['status', 'signature_status', 'error_message'])
        logger.warning(format_log_message(
            'restore blocked by verification failure',
            backup_id=backup.pk,
            company_id=company.pk,
            error=str(exc),
        ))
        raise
    except Exception as exc:
        media_root_local = Path(getattr(settings, 'MEDIA_ROOT', '') or '.').resolve()
        original_zip = media_root_local / backup.file_path
        backup.status = STATUS_READY if original_zip.exists() else STATUS_FAILED
        backup.error_message = f'Restore error: {exc}'[:2000]
        backup.save(update_fields=['status', 'error_message'])
        logger.exception(format_log_message(
            'restore failed',
            backup_id=backup.pk,
            company_id=company.pk,
            resulting_status=backup.status,
            error=str(exc),
        ))
        raise

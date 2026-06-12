import logging
import shutil
import tempfile
import threading
from pathlib import Path

from django.conf import settings as dj_settings
from django.db import close_old_connections
from django.utils import timezone

from company_backups.logging_utils import (
    format_log_message,
    password_log_value,
)
from company_backups.models import (
    CompanyBackup,
    KIND_AUTO,
    STATUS_CREATING,
    STATUS_FAILED,
    STATUS_READY,
    SIGNATURE_STATUS_SIGNED,
    SIGNATURE_STATUS_UNSIGNED,
)
from company_backups.services.crypto import encrypt_file_stream
from company_backups.services.zip_io import (
    build_company_zip,
    company_backup_dir,
    generate_backup_filename,
)

logger = logging.getLogger(__name__)
_PROGRESS_LOG_LOCK = threading.Lock()
_PROGRESS_LOG_STATE: dict[int, tuple[int, str, str]] = {}


# def _remember_progress_snapshot lưu mốc tiến độ gần nhất (làm tròn 10%) trong bộ nhớ để chỉ ghi log khi tiến độ thực sự đổi (giảm spam log).
# vd: 71% rồi 79% (cùng nhóm 70) -> không log lại.
def _remember_progress_snapshot(record_id: int, percent: int, stage: str, detail: str) -> bool:
    snapshot = (
        max(0, min(100, int(percent))) // 10,
        str(stage or '')[:64],
        str(detail or '')[:255],
    )
    with _PROGRESS_LOG_LOCK:
        previous = _PROGRESS_LOG_STATE.get(record_id)
        _PROGRESS_LOG_STATE[record_id] = snapshot
    return previous != snapshot


# def _clear_progress_snapshot xóa mốc tiến độ in-memory của 1 backup khi build kết thúc.
# vd: gọi ở finally sau khi build xong hoặc lỗi.
def _clear_progress_snapshot(record_id: int) -> None:
    with _PROGRESS_LOG_LOCK:
        _PROGRESS_LOG_STATE.pop(record_id, None)


# def _user_signing_key_pem lấy private key PEM của user (nếu có UserSigningCredential active) để ký file backup; lỗi/không có -> None.
# vd: admin có chứng thư active -> trả PEM để ký gói backup.
def _user_signing_key_pem(user) -> bytes | None:
    """Tra ve PEM private key (bytes) cua user neu user co UserSigningCredential active."""
    if user is None:
        return None
    try:
        from signing.internal_pki import get_private_key_pem_for_credential
        from signing.services import _active_credential_for_user

        credential = _active_credential_for_user(user)
        if credential is None:
            return None
        pem_str = get_private_key_pem_for_credential(credential)
        if not pem_str:
            return None
        return pem_str.encode('utf-8') if isinstance(pem_str, str) else pem_str
    except Exception:
        logger.exception('[company_backups] resolve user signing key failed')
        return None


# def _sign_if_possible ký file plaintext: ưu tiên chữ ký của signer_user, fallback env BACKUP_SIGNER_PRIVATE_KEY_PEM; trả (đường dẫn .sig, trạng thái 'signed'/'unsigned'); lỗi -> unsigned.
# vd: có khóa ký -> sinh plaintext.zip.sig, status='signed'.
def _sign_if_possible(plain_path: Path, signer_user=None) -> tuple[Path | None, str]:
    """Ky file plaintext.

    Uu tien chu ky cua signer_user (UserSigningCredential active). Neu khong co,
    fall back sang env `BACKUP_SIGNER_PRIVATE_KEY_PEM`.
    """
    key_pem = _user_signing_key_pem(signer_user)
    if key_pem is None:
        env_key = getattr(dj_settings, 'BACKUP_SIGNER_PRIVATE_KEY_PEM', None)
        if env_key:
            key_pem = env_key.encode('utf-8') if isinstance(env_key, str) else env_key
    if not key_pem:
        return None, SIGNATURE_STATUS_UNSIGNED
    try:
        from signing.services import sign_generic_file

        sig_path = plain_path.with_suffix(plain_path.suffix + '.sig')
        sign_generic_file(str(plain_path), key_pem, str(sig_path))
        return sig_path, SIGNATURE_STATUS_SIGNED
    except Exception:
        logger.exception('[company_backups] sign_generic_file failed; skipping signature')
        return None, SIGNATURE_STATUS_UNSIGNED


# def _save_progress cập nhật % + bước + chi tiết vào CompanyBackup trong DB (gọi từ background thread); chỉ ghi log khi mốc tiến độ đổi.
# vd: _save_progress(id, 80, 'Ma hoa', '...') -> cập nhật progress trong DB.
def _save_progress(record_id: int, percent: int, stage: str, detail: str) -> None:
    """Cap nhat tien trinh vao DB. Goi tu background thread -> can dong DB conn."""
    try:
        CompanyBackup.objects.filter(pk=record_id).update(
            progress_percent=int(percent),
            progress_stage=str(stage or '')[:64],
            progress_detail=str(detail or '')[:255],
        )
        if _remember_progress_snapshot(record_id, percent, stage, detail):
            logger.info(format_log_message(
                'backup build progress',
                backup_id=record_id,
                progress_percent=int(percent),
                progress_stage=str(stage or '')[:64],
                progress_detail=str(detail or '')[:255],
            ))
    except Exception:
        logger.exception('[company_backups] update progress failed')


# def _build_pipeline pipeline cốt lõi tạo backup: dựng zip plaintext -> ký -> mã hóa (password admin / env master key / hoặc giữ plaintext legacy nếu không có khóa) -> dọn file tạm; trả (size, manifest, encryption_meta, signature_path, signature_status).
# vd: có password -> file cuối là ciphertext AES-GCM kèm .sig.
def _build_pipeline(
    *,
    company,
    components,
    user,
    final_path: Path,
    on_progress,
    password: str | None = None,
    signer_user=None,
) -> tuple[int, dict, dict | None, str, str]:
    """Pipeline cot loi: plaintext -> sign -> encrypt -> cleanup tmp.

    Bao mat:
    - `password` (admin) -> ma hoa Scrypt-derived AES key (bat buoc cho manual).
    - `signer_user` -> ky bang UserSigningCredential cua admin neu co.

    Returns: (size_bytes_final, manifest, encryption_meta_or_None, signature_path_str, signature_status)
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix='cbk_pipeline_'))
    plain_path = tmp_dir / 'plaintext.zip'
    sig_path_final = ''
    encryption_meta: dict | None = None
    signature_status = SIGNATURE_STATUS_UNSIGNED
    try:
        logger.info(format_log_message(
            'backup build pipeline started',
            company_id=company.pk,
            user_id=getattr(user, 'pk', None),
            signer_user_id=getattr(signer_user, 'pk', None),
            components=components,
            final_path=str(final_path),
            password=password_log_value(password),
        ))
        on_progress(5, 'Khoi tao', 'Chuan bi pipeline')
        size_plain, manifest = build_company_zip(
            company=company,
            components=components,
            output_path=plain_path,
            created_by=user,
            on_progress=lambda p, s, d: on_progress(min(5 + int(p * 0.7), 75), s, d),
        )

        env_master_key = getattr(dj_settings, 'BACKUP_ENCRYPTION_MASTER_KEY', None)
        effective_signer = signer_user or user
        sig_tmp, signature_status = _sign_if_possible(plain_path, signer_user=effective_signer)
        logger.info(format_log_message(
            'backup build signature step completed',
            company_id=company.pk,
            signature_status=signature_status,
            signature_path=str(sig_tmp) if sig_tmp else '',
        ))

        if password:
            on_progress(80, 'Ma hoa', 'AES-256-GCM voi mat khau admin')
            encryption_meta = encrypt_file_stream(
                str(plain_path),
                str(final_path),
                company_id=company.pk,
                password=password,
            )
            logger.info(format_log_message(
                'backup build encryption completed',
                company_id=company.pk,
                encryption_mode='password',
                chunk_count=(encryption_meta or {}).get('chunk_count'),
            ))
        elif env_master_key:
            on_progress(80, 'Ma hoa', 'AES-256-GCM voi master key he thong')
            encryption_meta = encrypt_file_stream(
                str(plain_path),
                str(final_path),
                env_master_key,
                company_id=company.pk,
            )
            logger.info(format_log_message(
                'backup build encryption completed',
                company_id=company.pk,
                encryption_mode='env_master_key',
                chunk_count=(encryption_meta or {}).get('chunk_count'),
            ))
        else:
            on_progress(80, 'Sao chep', 'Khong co password/master key, luu plaintext (legacy mode)')
            shutil.copy2(str(plain_path), str(final_path))
            logger.info(format_log_message(
                'backup build stored plaintext backup',
                company_id=company.pk,
                encryption_mode='plaintext_legacy',
            ))

        if sig_tmp is not None and Path(sig_tmp).exists():
            final_sig = final_path.with_suffix('.zip.sig')
            shutil.copy2(str(sig_tmp), str(final_sig))
            sig_path_final = str(final_sig)

        size_final = final_path.stat().st_size
        on_progress(95, 'Don dep', 'Xoa file tam plaintext')
        logger.info(format_log_message(
            'backup build pipeline finished',
            company_id=company.pk,
            size_plain=size_plain,
            size_bytes=size_final,
            manifest_components=(manifest or {}).get('components', []),
            record_counts=(manifest or {}).get('record_counts', {}),
            file_count=(manifest or {}).get('file_count'),
            is_encrypted=bool(encryption_meta),
            signature_status=signature_status,
        ))
        return size_final, manifest, encryption_meta, sig_path_final, signature_status
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# def _build_in_thread chạy _build_pipeline trong background thread cho 1 record: cập nhật status ready + manifest/encryption/signature khi xong; lỗi -> status failed và xóa file dở; luôn đóng DB conn cũ.
# vd: tạo backup async -> thread này chạy nền, frontend poll tiến độ.
def _build_in_thread(
    record_id: int,
    company_pk: int,
    components: list,
    user_id,
    password: str | None = None,
    signer_user_id=None,
):
    from accounts.models import Company
    from django.contrib.auth.models import User

    try:
        logger.info(format_log_message(
            'backup build thread started',
            backup_id=record_id,
            company_id=company_pk,
            user_id=user_id,
            signer_user_id=signer_user_id,
            components=components,
            password=password_log_value(password),
        ))
        company = Company.objects.get(pk=company_pk)
        user = User.objects.filter(pk=user_id).first() if user_id else None
        signer_user = User.objects.filter(pk=signer_user_id).first() if signer_user_id else user
        record = CompanyBackup.objects.get(pk=record_id)
        media_root = Path(getattr(dj_settings, 'MEDIA_ROOT', '') or '.').resolve()
        full_path = media_root / record.file_path

        # def _cb để cb (service nghiệp vụ).
        # vd: nhận đầu vào -> trả kết quả đã xử lý.
        def _cb(percent, stage, detail):
            _save_progress(record_id, percent, stage, detail)

        size, manifest, enc_meta, sig_path, sig_status = _build_pipeline(
            company=company,
            components=components,
            user=user,
            final_path=full_path,
            on_progress=_cb,
            password=password,
            signer_user=signer_user,
        )
        CompanyBackup.objects.filter(pk=record_id).update(
            size_bytes=size,
            manifest=manifest,
            encryption_meta=enc_meta,
            signature_path=sig_path or '',
            signature_status=sig_status,
            status=STATUS_READY,
            completed_at=timezone.now(),
            progress_percent=100,
            progress_stage='Hoan tat',
            progress_detail='',
            error_message='',
        )
        logger.info(format_log_message(
            'backup build thread completed',
            backup_id=record_id,
            company_id=company_pk,
            size_bytes=size,
            is_encrypted=bool(enc_meta),
            signature_status=sig_status,
            signature_path=sig_path,
        ))
    except Exception as exc:
        logger.exception(format_log_message(
            'backup build thread failed',
            backup_id=record_id,
            company_id=company_pk,
            user_id=user_id,
            error=str(exc),
        ))
        try:
            CompanyBackup.objects.filter(pk=record_id).update(
                status=STATUS_FAILED,
                error_message=f'Build error: {exc}'[:2000],
                progress_detail=f'Loi: {exc}'[:255],
            )
            record = CompanyBackup.objects.filter(pk=record_id).first()
            if record and record.file_path:
                media_root = Path(getattr(dj_settings, 'MEDIA_ROOT', '') or '.').resolve()
                full = media_root / record.file_path
                if full.exists():
                    try:
                        full.unlink()
                    except Exception:
                        pass
                sig = full.with_suffix('.zip.sig')
                if sig.exists():
                    try:
                        sig.unlink()
                    except Exception:
                        pass
        except Exception:
            pass
    finally:
        _clear_progress_snapshot(record_id)
        close_old_connections()


# def create_backup tạo 1 bản backup: tạo record (status creating) rồi build — mặc định async (trả record ngay, build chạy nền) hoặc sync (chờ xong, dùng cho auto-backup/test). password -> mã hóa gói; signer_user -> ký gói.
# vd: create_backup(company=A, components=[...], kind='manual', password='x') -> record creating, build nền tạo gói mã hóa.
def create_backup(
    *,
    company,
    components,
    kind: str,
    user=None,
    async_run: bool = True,
    password: str | None = None,
    signer_user=None,
) -> CompanyBackup:
    """
    Tao 1 ban backup. Mac dinh async_run=True -> tra ve record ngay,
    build chay trong background thread voi progress update.
    async_run=False -> block sync (cho auto-backup + tests).

    `password`: neu co (vd password admin nhap khi tao manual) -> ma hoa AES-GCM
        bang khoa Scrypt-derived. Khi download phai dua lai cung password.
    `signer_user`: neu co -> ky file plaintext bang UserSigningCredential active
        cua user nay (fall back env BACKUP_SIGNER_PRIVATE_KEY_PEM).
    """
    components = list(components) or []
    filename = generate_backup_filename(company)
    backup_dir = company_backup_dir(company)
    full_path = backup_dir / filename
    media_root = Path(getattr(dj_settings, 'MEDIA_ROOT', '') or '.').resolve()
    try:
        relative_path = str(full_path.resolve().relative_to(media_root)).replace('\\', '/')
    except ValueError:
        relative_path = str(full_path).replace('\\', '/')

    record = CompanyBackup.objects.create(
        company=company,
        name=filename,
        kind=kind,
        components=components,
        file_path=relative_path,
        status=STATUS_CREATING,
        created_by=user,
        progress_percent=0,
        progress_stage='Khoi tao',
    )
    logger.info(format_log_message(
        'create_backup record created',
        backup_id=record.pk,
        company_id=company.pk,
        user_id=getattr(user, 'pk', None),
        signer_user_id=getattr(signer_user, 'pk', None),
        kind=kind,
        async_run=async_run,
        components=components,
        file_path=relative_path,
        password=password_log_value(password),
    ))

    if async_run:
        thread = threading.Thread(
            target=_build_in_thread,
            args=(record.pk, company.pk, components, user.pk if user else None),
            kwargs={
                'password': password,
                'signer_user_id': signer_user.pk if signer_user else None,
            },
            daemon=True,
            name=f'company_backup_{record.pk}',
        )
        thread.start()
        logger.info(format_log_message(
            'create_backup background thread launched',
            backup_id=record.pk,
            company_id=company.pk,
            thread_name=thread.name,
        ))
        return record

    try:
        logger.info(format_log_message(
            'create_backup sync build started',
            backup_id=record.pk,
            company_id=company.pk,
        ))
        size, manifest, enc_meta, sig_path, sig_status = _build_pipeline(
            company=company,
            components=components,
            user=user,
            final_path=full_path,
            on_progress=lambda p, s, d: _save_progress(record.pk, p, s, d),
            password=password,
            signer_user=signer_user or user,
        )
        CompanyBackup.objects.filter(pk=record.pk).update(
            size_bytes=size,
            manifest=manifest,
            encryption_meta=enc_meta,
            signature_path=sig_path or '',
            signature_status=sig_status,
            status=STATUS_READY,
            completed_at=timezone.now(),
            progress_percent=100,
            progress_stage='Hoan tat',
            progress_detail='',
        )
        record.refresh_from_db()
        logger.info(format_log_message(
            'create_backup sync build completed',
            backup_id=record.pk,
            company_id=company.pk,
            size_bytes=size,
            is_encrypted=bool(enc_meta),
            signature_status=sig_status,
            signature_path=sig_path,
        ))
        return record
    except Exception as exc:
        CompanyBackup.objects.filter(pk=record.pk).update(
            status=STATUS_FAILED,
            error_message=f'Build error: {exc}'[:2000],
        )
        if full_path.exists():
            try:
                full_path.unlink()
            except Exception:
                pass
        sig = full_path.with_suffix('.zip.sig')
        if sig.exists():
            try:
                sig.unlink()
            except Exception:
                pass
        logger.exception(format_log_message(
            'create_backup sync build failed',
            backup_id=record.pk,
            company_id=company.pk,
            error=str(exc),
        ))
        raise
    finally:
        _clear_progress_snapshot(record.pk)


# def delete_backup_file xóa file zip + file chữ ký (.sig) của 1 backup khỏi disk (dùng khi xóa backup hoặc dọn retention).
# vd: xóa backup #5 -> xóa cả file .zip lẫn .zip.sig.
def delete_backup_file(record: CompanyBackup) -> None:
    media_root = Path(getattr(dj_settings, 'MEDIA_ROOT', '') or '.')
    if record.file_path:
        full = media_root / record.file_path
        if full.exists() and full.is_file():
            try:
                full.unlink()
                logger.info(format_log_message(
                    'backup file deleted from disk',
                    backup_id=record.pk,
                    company_id=record.company_id,
                    file_path=str(full),
                ))
            except Exception:
                pass
    if record.signature_path:
        sig = Path(record.signature_path)
        if sig.exists() and sig.is_file():
            try:
                sig.unlink()
                logger.info(format_log_message(
                    'backup signature file deleted from disk',
                    backup_id=record.pk,
                    company_id=record.company_id,
                    signature_path=str(sig),
                ))
            except Exception:
                pass


# def enforce_retention xóa các backup auto cũ vượt số lượng giữ lại (retention_count), chỉ giữ N bản mới nhất; trả số bản đã xóa.
# vd: retention=12, có 15 bản auto -> xóa 3 bản cũ nhất.
def enforce_retention(company, retention_count: int, kind: str = KIND_AUTO) -> int:
    """Xoa cac ban backup auto cu vuot retention. Tra ve so ban da xoa."""
    if not retention_count or retention_count <= 0:
        return 0
    qs = CompanyBackup.objects.filter(
        company=company,
        kind=kind,
        status__in=[STATUS_READY],
    ).order_by('-created_at')
    survivors = list(qs.values_list('pk', flat=True)[:retention_count])
    obsolete = CompanyBackup.objects.filter(
        company=company,
        kind=kind,
    ).exclude(pk__in=survivors)
    deleted = 0
    for record in obsolete:
        delete_backup_file(record)
        record.delete()
        deleted += 1
    logger.info(format_log_message(
        'backup retention enforced',
        company_id=company.pk,
        kind=kind,
        retention_count=retention_count,
        deleted=deleted,
        survivors=len(survivors),
    ))
    return deleted

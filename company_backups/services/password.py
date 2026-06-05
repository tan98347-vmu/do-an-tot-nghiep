from django.contrib.auth.hashers import check_password, make_password


def set_backup_password(settings_obj, raw: str) -> None:
    raw = (raw or '').strip()
    if len(raw) < 6:
        raise ValueError('Mat khau backup phai it nhat 6 ky tu.')
    settings_obj.backup_password_hash = make_password(raw)
    settings_obj.save(update_fields=['backup_password_hash', 'updated_at'])


def verify_backup_password(settings_obj, raw: str) -> bool:
    if not settings_obj or not settings_obj.backup_password_hash:
        return False
    return check_password((raw or '').strip(), settings_obj.backup_password_hash)


def ensure_settings(company):
    from company_backups.models import CompanyBackupSettings
    obj, _ = CompanyBackupSettings.objects.get_or_create(company=company)
    return obj

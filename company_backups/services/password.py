from django.contrib.auth.hashers import check_password, make_password


# def set_backup_password đặt mật khẩu sao lưu cho công ty (hash bằng make_password, tối thiểu 6 ký tự) để dùng cho mã hóa gói backup; raw quá ngắn -> ValueError.
# vd: set_backup_password(settings, 'matkhau123') -> lưu hash, không lưu mật khẩu thô.
def set_backup_password(settings_obj, raw: str) -> None:
    raw = (raw or '').strip()
    if len(raw) < 6:
        raise ValueError('Mat khau backup phai it nhat 6 ky tu.')
    settings_obj.backup_password_hash = make_password(raw)
    settings_obj.save(update_fields=['backup_password_hash', 'updated_at'])


# def verify_backup_password kiểm tra mật khẩu người dùng nhập có khớp hash đã lưu không (để giải mã/khôi phục); công ty chưa đặt mật khẩu -> False.
# vd: nhập đúng mật khẩu -> True; sai -> False.
def verify_backup_password(settings_obj, raw: str) -> bool:
    if not settings_obj or not settings_obj.backup_password_hash:
        return False
    return check_password((raw or '').strip(), settings_obj.backup_password_hash)


# def ensure_settings lấy (hoặc tạo mới nếu chưa có) bản ghi CompanyBackupSettings cho công ty.
# vd: công ty chưa có settings -> tạo bản mặc định rồi trả về.
def ensure_settings(company):
    from company_backups.models import CompanyBackupSettings
    obj, _ = CompanyBackupSettings.objects.get_or_create(company=company)
    return obj

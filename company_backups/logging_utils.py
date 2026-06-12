import json


# def _stringify_log_value đổi giá trị field log thành chuỗi gọn (list/dict -> JSON, còn lại -> str) cho dòng log có cấu trúc.
# vd: [1,2] -> '[1, 2]'; {'a':1} -> '{\"a\": 1}'.
def _stringify_log_value(value) -> str:
    if isinstance(value, (list, tuple, set)):
        return json.dumps(list(value), ensure_ascii=False)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


# def format_log_message dựng 1 dòng log có tiền tố '[company_backups] <event>' kèm các field key=value (bỏ field None/rỗng).
# vd: format_log_message('backup_done', company='A', size=1024) -> '[company_backups] backup_done | company=A size=1024'.
def format_log_message(event: str, **fields) -> str:
    parts = [f'[company_backups] {event}']
    rendered_fields: list[str] = []
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, str) and not value:
            continue
        rendered_fields.append(f'{key}={_stringify_log_value(value)}')
    if rendered_fields:
        parts.append(' | ')
        parts.append(' '.join(rendered_fields))
    return ''.join(parts)


# def password_log_value trả nhãn an toàn cho log về mật khẩu (KHÔNG log mật khẩu thật): 'provided' nếu có, 'missing' nếu không.
# vd: có mật khẩu -> 'provided'.
def password_log_value(raw_password: str | None) -> str:
    return 'provided' if raw_password else 'missing'

import json


def _stringify_log_value(value) -> str:
    if isinstance(value, (list, tuple, set)):
        return json.dumps(list(value), ensure_ascii=False)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


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


def password_log_value(raw_password: str | None) -> str:
    return 'provided' if raw_password else 'missing'

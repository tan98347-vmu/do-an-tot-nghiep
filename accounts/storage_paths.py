import os


def company_storage_slug(company):
    if company is None:
        return 'default-company'
    slug = getattr(company, 'slug', '') or getattr(company, 'code', '') or getattr(company, 'name', '')
    slug = str(slug or '').strip().replace('\\', '-').replace('/', '-')
    return slug or 'default-company'


def safe_storage_filename(filename):
    raw_name = os.path.basename(str(filename or '').strip())
    if not raw_name:
        return 'file.bin'
    return raw_name.replace('\\', '_').replace('/', '_')


def company_media_path(*, company, section, filename, parts=None):
    safe_name = safe_storage_filename(filename)
    base_parts = ['companies', company_storage_slug(company)]
    if section:
        base_parts.append(str(section).strip('/'))
    for part in parts or []:
        if part in (None, ''):
            continue
        base_parts.append(str(part).strip('/'))
    base_parts.append(safe_name)
    return '/'.join(base_parts)

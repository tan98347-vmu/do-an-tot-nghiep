import io
import json
import unicodedata
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional, Tuple

from django.conf import settings
from django.core import serializers
from django.db.models import FileField
from django.utils import timezone

from company_backups.services.components import (
    ALL_COMPONENTS,
    COMPONENT_MODELS,
    filter_queryset_for_company,
    models_for_components,
)


# def _ascii_slug đổi chuỗi (vd tên công ty có dấu) thành slug ASCII an toàn để đặt tên file.
# vd: 'Công ty A' -> 'Cong_ty_A'.
def _ascii_slug(value: str) -> str:
    if not value:
        return ''
    normalized = unicodedata.normalize('NFKD', value)
    ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
    cleaned = re.sub(r'[^A-Za-z0-9]+', '_', ascii_text).strip('_')
    return cleaned or 'company'


# def generate_backup_filename sinh tên file zip backup gồm slug tên + mã công ty + timestamp.
# vd: -> 'Cong_ty_A_VNNET_20260611_093000.zip'.
def generate_backup_filename(company, when: Optional[datetime] = None) -> str:
    when = when or timezone.localtime()
    ts = when.strftime('%Y%m%d_%H%M%S')
    name_slug = _ascii_slug(company.name)[:80]
    code_slug = _ascii_slug(company.code)[:40]
    return f'{name_slug}_{code_slug}_{ts}.zip'


# def company_backup_root trả thư mục gốc chứa backup (MEDIA_ROOT/company_backups).
# vd: -> <MEDIA_ROOT>/company_backups.
def company_backup_root() -> Path:
    media_root = Path(getattr(settings, 'MEDIA_ROOT', '') or '.')
    return media_root / 'company_backups'


# def company_backup_dir trả (và tạo nếu chưa có) thư mục backup riêng của 1 công ty theo slug.
# vd: -> <MEDIA_ROOT>/company_backups/<slug-cong-ty>/.
def company_backup_dir(company) -> Path:
    from accounts.storage_paths import company_storage_slug
    base = company_backup_root() / company_storage_slug(company)
    base.mkdir(parents=True, exist_ok=True)
    return base


# def _collect_file_paths thu thập đường dẫn các file media (FileField) của một queryset để copy vào zip.
# vd: queryset Document -> tập đường dẫn output_file của các văn bản.
def _collect_file_paths(queryset) -> set[str]:
    paths: set[str] = set()
    model = queryset.model
    file_fields = [f for f in model._meta.fields if isinstance(f, FileField)]
    if not file_fields:
        return paths
    for obj in queryset.iterator(chunk_size=200):
        for f in file_fields:
            value = getattr(obj, f.name, None)
            name = getattr(value, 'name', None) if value else None
            if name:
                paths.add(name)
    return paths


# def _serialize_qs_to_json serialize queryset thành JSON (Django serializers) và đếm số bản ghi; trả (bytes, count).
# vd: 10 bản ghi -> (json bytes, 10).
def _serialize_qs_to_json(queryset) -> Tuple[bytes, int]:
    buf = io.StringIO()
    serializers.serialize('json', queryset.iterator(chunk_size=200), stream=buf)
    raw = buf.getvalue() or '[]'
    try:
        count = len(json.loads(raw)) if raw else 0
    except json.JSONDecodeError:
        count = 0
    return raw.encode('utf-8'), count


# def build_company_zip dựng file ZIP backup của công ty gồm data/<model>.json + media/<...> + manifest.json, lọc đúng phạm vi công ty; báo tiến độ theo 3 phase (xuất data 5–70%, copy media 70–95%, manifest 95–100%). Trả (size_bytes, manifest).
# vd: components=['documents'] -> zip chứa data/documents__Document.json + file đính kèm + manifest.
def build_company_zip(
    *,
    company,
    components: Iterable[str],
    output_path: Path,
    created_by=None,
    on_progress=None,
) -> Tuple[int, dict]:
    """
    Build ZIP file at output_path containing data/<label>.json + media/<...> + manifest.json.
    Return (size_bytes, manifest_dict).

    on_progress(percent: int, stage: str, detail: str) duoc goi sau moi phase.
    """
    components = list(components) or list(ALL_COMPONENTS)
    media_root = Path(getattr(settings, 'MEDIA_ROOT', '') or '.')

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # def _emit gọi callback báo tiến độ (kẹp 0–100), nuốt lỗi để không làm hỏng quá trình build zip.
    # vd: _emit(70, 'Xuat du lieu', '...') -> cập nhật progress 70%.
    def _emit(percent: int, stage: str, detail: str = ''):
        if on_progress is None:
            return
        try:
            on_progress(min(100, max(0, percent)), stage, detail)
        except Exception:
            pass

    record_counts: dict[str, int] = {}
    file_paths: set[str] = set()

    _emit(2, 'Khoi tao', 'Tao file ZIP')

    model_list = models_for_components(components)
    total_models = max(len(model_list), 1)
    # Phase 1: data JSON 5..70%
    DATA_BAND = (5, 70)

    with zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
        if 'accounts' in components:
            from django.contrib.auth.models import User
            from accounts.models import CompanyUserMembership
            _emit(4, 'Xuat du lieu', 'Tai khoan nguoi dung')
            membership_qs = CompanyUserMembership.objects.filter(company=company)
            user_ids = list(membership_qs.values_list('user_id', flat=True))
            if user_ids:
                user_qs = User.objects.filter(pk__in=user_ids)
                raw, count = _serialize_qs_to_json(user_qs)
                zf.writestr('data/auth__User.json', raw)
                record_counts['auth.User'] = count

        from accounts.models import Company
        company_qs = Company.objects.filter(pk=company.pk)
        raw, count = _serialize_qs_to_json(company_qs)
        zf.writestr('data/accounts__Company.json', raw)
        record_counts['accounts.Company'] = count

        for idx, (label, model) in enumerate(model_list, start=1):
            short = label.split('.')[-1]
            percent = DATA_BAND[0] + int((DATA_BAND[1] - DATA_BAND[0]) * (idx / total_models))
            _emit(percent, 'Xuat du lieu', f'{idx}/{total_models} - {short}')
            queryset = filter_queryset_for_company(label, company)
            if not queryset.exists():
                continue
            raw, count = _serialize_qs_to_json(queryset)
            safe_name = label.replace('.', '__')
            zf.writestr(f'data/{safe_name}.json', raw)
            record_counts[label] = count
            file_paths |= _collect_file_paths(queryset)

        # Phase 2: copy media 70..95%
        total_files = max(len(file_paths), 1)
        sorted_paths = sorted(file_paths)
        _emit(72, 'Sao chep tep media', f'{len(file_paths)} tep')
        copied_files = 0
        FILE_BAND = (72, 95)
        for fidx, relative_path in enumerate(sorted_paths, start=1):
            source = media_root / relative_path
            if not source.exists() or not source.is_file():
                continue
            try:
                zf.write(source, arcname=f'media/{relative_path.replace(chr(92), "/")}')
                copied_files += 1
            except Exception:
                continue
            if fidx % 20 == 0 or fidx == total_files:
                percent = FILE_BAND[0] + int((FILE_BAND[1] - FILE_BAND[0]) * (fidx / total_files))
                _emit(percent, 'Sao chep tep media', f'{fidx}/{total_files}')

        # Phase 3: manifest + finalize 95..100%
        _emit(97, 'Ghi manifest', '')
        manifest = {
            'version': 1,
            'created_at': timezone.now().isoformat(),
            'created_by_id': created_by.pk if created_by else None,
            'created_by_username': created_by.username if created_by else '',
            'company': {
                'id': company.pk,
                'code': company.code,
                'slug': getattr(company, 'slug', ''),
                'name': company.name,
            },
            'components': components,
            'record_counts': record_counts,
            'file_count': copied_files,
        }
        zf.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))

    size_bytes = output_path.stat().st_size
    _emit(100, 'Hoan tat', f'{size_bytes // 1024} KB')
    return size_bytes, manifest

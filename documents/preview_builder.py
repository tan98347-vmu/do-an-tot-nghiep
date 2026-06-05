import hashlib
import logging
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import fitz
from django.conf import settings
from accounts.runtime_guard import CompanyRuntimeGuard
from accounts.storage_paths import company_storage_slug


PREVIEW_LOGGER = logging.getLogger('documents.preview_pdf')


class DocumentPreviewUnavailable(Exception):
    def __init__(self, detail, code='preview_unavailable', status_code=503):
        super().__init__(detail)
        self.detail = detail
        self.code = code
        self.status_code = status_code


def _preview_cache_dir(namespace='documents'):
    cache_dir = Path(settings.MEDIA_ROOT) / 'preview_cache' / namespace
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _company_preview_namespace(base_namespace, company):
    return f'{base_namespace}/{company_storage_slug(company)}'


def _preview_signature(document):
    try:
        output_path = Path(document.output_file.path)
        stat = output_path.stat()
        file_meta = f'{stat.st_size}:{int(stat.st_mtime)}'
    except (FileNotFoundError, ValueError, OSError):
        file_meta = 'missing'
    return '|'.join(
        [
            str(document.pk),
            str(document.version_number),
            getattr(document, 'updated_at', None).isoformat() if getattr(document, 'updated_at', None) else '',
            getattr(document.output_file, 'name', '') or '',
            file_meta,
        ]
    )


def _template_signature_from_file(template, docx_file, source_path):
    try:
        stat = source_path.stat()
        file_meta = f'{stat.st_size}:{int(stat.st_mtime)}'
    except OSError:
        file_meta = 'missing'
    return '|'.join(
        [
            str(template.pk),
            getattr(template, 'version', '') or '',
            getattr(template, 'updated_at', None).isoformat() if getattr(template, 'updated_at', None) else '',
            getattr(docx_file, 'name', '') or '',
            file_meta,
        ]
    )


def _template_signature_from_content(template, content, docx_bytes):
    return '|'.join(
        [
            str(template.pk),
            getattr(template, 'version', '') or '',
            getattr(template, 'updated_at', None).isoformat() if getattr(template, 'updated_at', None) else '',
            str(len(content)),
            hashlib.sha256(docx_bytes).hexdigest()[:16],
        ]
    )


def _preview_pdf_path(namespace, prefix, object_id, signature):
    digest = hashlib.sha256(signature.encode('utf-8')).hexdigest()[:16]
    return _preview_cache_dir(namespace) / f'{prefix}_{object_id}_{digest}.pdf'


def _cleanup_stale_previews(namespace, prefix, object_id, keep_path):
    file_prefix = f'{prefix}_{object_id}_'
    for candidate in _preview_cache_dir(namespace).glob(f'{file_prefix}*.pdf'):
        if candidate == keep_path:
            continue
        try:
            candidate.unlink()
        except OSError:
            PREVIEW_LOGGER.debug('preview cleanup skipped | path=%s', candidate)


def invalidate_template_preview_cache(template):
    """Xoa toan bo PDF preview da cache cua mot mau van ban.

    Goi sau khi noi dung/file mau thay doi (vi du khoi phuc phien ban) de lan
    xem truoc tiep theo bat buoc render lai thay vi tra ve ban cu trong cache.
    """
    if template is None or getattr(template, 'pk', None) is None:
        return
    namespace = _company_preview_namespace('templates', getattr(template, 'company', None))
    _cleanup_stale_previews(namespace, 'template', template.pk, keep_path=None)


def invalidate_document_preview_cache(document):
    """Xoa toan bo PDF preview da cache cua mot van ban (va cac phien ban).

    Goi sau khi noi dung file DOCX cua van ban thay doi (vi du sau khi chinh sua
    thu cong) de trinh xem truoc khong tra ve ban PDF cu.
    """
    if document is None or getattr(document, 'pk', None) is None:
        return
    company = getattr(document, 'company', None)
    _cleanup_stale_previews(
        _company_preview_namespace('documents', company), 'document', document.pk, keep_path=None
    )


def _cached_preview_is_valid(pdf_path):
    try:
        with fitz.open(str(pdf_path)) as preview_doc:
            return preview_doc.page_count > 0
    except Exception as exc:
        PREVIEW_LOGGER.warning('preview cache invalid | path=%s | error=%s', pdf_path, exc)
        return False


def _libreoffice_command():
    configured = (getattr(settings, 'LIBREOFFICE_BIN', '') or '').strip()
    return configured or 'soffice'


def _preview_timeout_seconds():
    value = getattr(settings, 'DOC_PREVIEW_TIMEOUT_SECONDS', 45)
    try:
        return max(int(value), 10)
    except (TypeError, ValueError):
        return 45


def _run_libreoffice_convert(command, timeout_seconds):
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )


def _cleanup_work_dir(path):
    work_dir = Path(path)
    for attempt in range(4):
        try:
            shutil.rmtree(work_dir)
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            if attempt == 3:
                PREVIEW_LOGGER.warning('preview temp cleanup skipped | path=%s | error=%s', work_dir, exc)
                return
            time.sleep(0.4 * (attempt + 1))


def _convert_source_to_pdf(source_path, *, namespace, prefix, object_id, signature):
    target_path = _preview_pdf_path(namespace, prefix, object_id, signature)
    if target_path.exists():
        if _cached_preview_is_valid(target_path):
            PREVIEW_LOGGER.debug(
                'preview cache hit | namespace=%s | object_id=%s | pdf=%s',
                namespace,
                object_id,
                target_path,
            )
            return target_path
        try:
            target_path.unlink()
        except OSError:
            fallback_target = target_path.with_name(
                f'{target_path.stem}_rebuild_{uuid.uuid4().hex[:8]}{target_path.suffix}'
            )
            PREVIEW_LOGGER.warning(
                'preview cache invalid but unlink failed | path=%s | fallback=%s',
                target_path,
                fallback_target,
            )
            target_path = fallback_target
        else:
            PREVIEW_LOGGER.info(
                'preview cache invalidated | namespace=%s | object_id=%s | pdf=%s',
                namespace,
                object_id,
                target_path,
            )

    _cleanup_stale_previews(namespace, prefix, object_id, target_path)

    soffice_cmd = _libreoffice_command()
    timeout_seconds = _preview_timeout_seconds()
    PREVIEW_LOGGER.info(
        'preview convert start | namespace=%s | object_id=%s | source=%s | target=%s | soffice=%s | timeout=%ss',
        namespace,
        object_id,
        source_path,
        target_path,
        soffice_cmd,
        timeout_seconds,
    )

    work_dir_path = _preview_cache_dir(namespace) / f'doc-preview-{uuid.uuid4().hex}'
    work_dir_path.mkdir(parents=True, exist_ok=False)
    try:
        input_copy = work_dir_path / source_path.name
        profile_dir = work_dir_path / 'lo-profile'
        profile_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, input_copy)
        command = [
            soffice_cmd,
            f'-env:UserInstallation={profile_dir.as_uri()}',
            '--headless',
            '--convert-to',
            'pdf',
            '--outdir',
            str(work_dir_path),
            str(input_copy),
        ]
        fallback_command = [
            soffice_cmd,
            '--headless',
            '--convert-to',
            'pdf',
            '--outdir',
            str(work_dir_path),
            str(input_copy),
        ]
        try:
            completed = _run_libreoffice_convert(command, timeout_seconds)
        except FileNotFoundError as exc:
            raise DocumentPreviewUnavailable(
                'Khong tim thay LibreOffice. Hay cai LibreOffice va cau hinh LIBREOFFICE_BIN.',
                code='converter_not_found',
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise DocumentPreviewUnavailable(
                f'Chuyen DOCX sang PDF bi timeout sau {timeout_seconds} giay.',
                code='preview_timeout',
            ) from exc

        stdout = (completed.stdout or '').strip()
        stderr = (completed.stderr or '').strip()
        generated_pdf = work_dir_path / f'{input_copy.stem}.pdf'
        PREVIEW_LOGGER.debug(
            'preview convert done | namespace=%s | object_id=%s | returncode=%s | stdout=%s | stderr=%s',
            namespace,
            object_id,
            completed.returncode,
            stdout,
            stderr,
        )
        if completed.returncode != 0 or not generated_pdf.exists():
            PREVIEW_LOGGER.warning(
                'preview convert retry without isolated profile | namespace=%s | object_id=%s',
                namespace,
                object_id,
            )
            try:
                completed = _run_libreoffice_convert(fallback_command, timeout_seconds)
            except subprocess.TimeoutExpired as exc:
                raise DocumentPreviewUnavailable(
                    f'Chuyen DOCX sang PDF bi timeout sau {timeout_seconds} giay.',
                    code='preview_timeout',
                ) from exc
            stdout = (completed.stdout or '').strip()
            stderr = (completed.stderr or '').strip()
            PREVIEW_LOGGER.debug(
                'preview convert fallback done | namespace=%s | object_id=%s | returncode=%s | stdout=%s | stderr=%s',
                namespace,
                object_id,
                completed.returncode,
                stdout,
                stderr,
            )
            if completed.returncode != 0:
                detail = 'LibreOffice khong tao duoc PDF preview.'
                if stdout or stderr:
                    detail = f'{detail} stdout={stdout or "-"} stderr={stderr or "-"}'
                raise DocumentPreviewUnavailable(detail, code='converter_failed')
            if not generated_pdf.exists():
                detail = 'LibreOffice da chay nhung khong tao ra file PDF.'
                if stdout or stderr:
                    detail = f'{detail} stdout={stdout or "-"} stderr={stderr or "-"}'
                raise DocumentPreviewUnavailable(detail, code='preview_missing')

        os.replace(generated_pdf, target_path)
    finally:
        _cleanup_work_dir(work_dir_path)

    try:
        pdf_size = target_path.stat().st_size
    except OSError:
        pdf_size = -1
    PREVIEW_LOGGER.info(
        'preview convert success | namespace=%s | object_id=%s | pdf=%s | pdf_size=%s',
        namespace,
        object_id,
        target_path,
        pdf_size,
    )
    return target_path


def _build_preview_pdf_from_bytes(docx_bytes, *, filename, namespace, prefix, object_id, signature):
    work_dir_path = _preview_cache_dir(namespace) / f'preview-source-{uuid.uuid4().hex}'
    work_dir_path.mkdir(parents=True, exist_ok=False)
    try:
        source_path = work_dir_path / filename
        source_path.write_bytes(docx_bytes)
        return _convert_source_to_pdf(
            source_path,
            namespace=namespace,
            prefix=prefix,
            object_id=object_id,
            signature=signature,
        )
    finally:
        _cleanup_work_dir(work_dir_path)


def build_document_preview_pdf(document):
    if not getattr(document, 'output_file', None):
        raise DocumentPreviewUnavailable(
            'Khong co file DOCX de tao ban xem PDF.',
            code='no_output_file',
            status_code=404,
        )
    CompanyRuntimeGuard.assert_file_field(
        document.output_file,
        target=document,
        detail='File DOCX cua van ban dang tro sang cong ty khac.',
    )

    try:
        source_path = Path(document.output_file.path)
    except (ValueError, NotImplementedError) as exc:
        raise DocumentPreviewUnavailable(
            f'Khong doc duoc duong dan file DOCX: {exc}',
            code='invalid_output_file',
        ) from exc

    if not source_path.exists():
        raise DocumentPreviewUnavailable(
            'File DOCX goc khong ton tai tren may chu.',
            code='source_missing',
            status_code=404,
        )

    pdf_path = _convert_source_to_pdf(
        source_path,
        namespace=_company_preview_namespace('documents', getattr(document, 'company', None)),
        prefix='document',
        object_id=document.pk,
        signature=_preview_signature(document),
    )
    CompanyRuntimeGuard.assert_preview_path(
        pdf_path,
        target=document,
        namespace='documents',
        detail='Preview PDF cua van ban dang tro sang cong ty khac.',
    )
    return pdf_path


def _document_version_signature(version):
    try:
        output_path = Path(version.output_file.path)
        stat = output_path.stat()
        file_meta = f'{stat.st_size}:{int(stat.st_mtime)}'
    except (FileNotFoundError, ValueError, OSError):
        file_meta = 'missing'
    return '|'.join(
        [
            str(version.document_id),
            str(version.pk),
            str(version.version_number),
            getattr(version.output_file, 'name', '') or '',
            file_meta,
        ]
    )


def build_document_version_preview_pdf(version):
    """Convert DOCX cua mot DocumentVersion sang PDF (co cache).

    Reuse cung pipeline LibreOffice voi `build_document_preview_pdf`, chi khac
    namespace + signature de cache moi version doc lap.
    """
    if not getattr(version, 'output_file', None):
        raise DocumentPreviewUnavailable(
            'Phien ban van ban khong co file DOCX de tai PDF.',
            code='no_output_file',
            status_code=404,
        )
    parent_document = getattr(version, 'document', None)
    if parent_document is not None:
        CompanyRuntimeGuard.assert_file_field(
            version.output_file,
            target=parent_document,
            detail='File DOCX cua phien ban dang tro sang cong ty khac.',
        )
    try:
        source_path = Path(version.output_file.path)
    except (ValueError, NotImplementedError) as exc:
        raise DocumentPreviewUnavailable(
            f'Khong doc duoc duong dan file DOCX cua phien ban: {exc}',
            code='invalid_output_file',
        ) from exc
    if not source_path.exists():
        raise DocumentPreviewUnavailable(
            'File DOCX cua phien ban khong ton tai tren may chu.',
            code='source_missing',
            status_code=404,
        )
    pdf_path = _convert_source_to_pdf(
        source_path,
        namespace=_company_preview_namespace(
            'document_versions',
            getattr(parent_document, 'company', None) if parent_document else None,
        ),
        prefix='version',
        object_id=f'{getattr(parent_document, "pk", "x")}_{version.pk}',
        signature=_document_version_signature(version),
    )
    if parent_document is not None:
        CompanyRuntimeGuard.assert_preview_path(
            pdf_path,
            target=parent_document,
            namespace='document_versions',
            detail='PDF cua phien ban dang tro sang cong ty khac.',
        )
    return pdf_path


def build_template_preview_pdf(template):
    docx_file = getattr(template, 'docx_file', None)
    source_type = getattr(template, 'source_type', None)
    content = str(getattr(template, 'content', '') or '').strip()

    if source_type == getattr(template, 'SOURCE_DOCX', 'docx') and not docx_file:
        raise DocumentPreviewUnavailable(
            'Mau van ban nay khong co file DOCX de tao ban xem PDF.',
            code='no_docx_source',
            status_code=409,
        )

    if source_type == getattr(template, 'SOURCE_DOCX', 'docx') and docx_file:
        CompanyRuntimeGuard.assert_file_field(
            docx_file,
            target=template,
            detail='File DOCX cua mau dang tro sang cong ty khac.',
        )
        try:
            source_path = Path(docx_file.path)
        except (ValueError, NotImplementedError) as exc:
            raise DocumentPreviewUnavailable(
                f'Khong doc duoc duong dan file DOCX cua mau: {exc}',
                code='invalid_template_file',
            ) from exc

        if source_path.exists():
            pdf_path = _convert_source_to_pdf(
                source_path,
                namespace=_company_preview_namespace('templates', getattr(template, 'company', None)),
                prefix='template',
                object_id=template.pk,
                signature=_template_signature_from_file(template, docx_file, source_path),
            )
            CompanyRuntimeGuard.assert_preview_path(
                pdf_path,
                target=template,
                namespace='templates',
                detail='Preview PDF cua mau dang tro sang cong ty khac.',
            )
            return pdf_path

        raise DocumentPreviewUnavailable(
            'File DOCX goc cua mau van ban khong ton tai tren may chu.',
            code='template_source_missing',
            status_code=404,
        )

    if content:
        try:
            docx_buffer = template.render_as_docx({}, allow_content_fallback=True)
            docx_bytes = docx_buffer.getvalue() if hasattr(docx_buffer, 'getvalue') else docx_buffer.read()
        except Exception as exc:
            raise DocumentPreviewUnavailable(
                f'Khong tao duoc DOCX preview tu noi dung hien tai cua mau: {exc}',
                code='template_render_failed',
            ) from exc

        if not docx_bytes:
            raise DocumentPreviewUnavailable(
                'Mau van ban khong co noi dung de tao ban xem PDF.',
                code='template_empty_content',
                status_code=404,
            )

        pdf_path = _build_preview_pdf_from_bytes(
            docx_bytes,
            filename=f'template_{template.pk}.docx',
            namespace=_company_preview_namespace('templates', getattr(template, 'company', None)),
            prefix='template',
            object_id=template.pk,
            signature=_template_signature_from_content(template, content, docx_bytes),
        )
        CompanyRuntimeGuard.assert_preview_path(
            pdf_path,
            target=template,
            namespace='templates',
            detail='Preview PDF cua mau dang tro sang cong ty khac.',
        )
        return pdf_path

    raise DocumentPreviewUnavailable(
        'Mau van ban nay khong co file DOCX de tao ban xem PDF.',
        code='no_docx_source',
        status_code=409,
    )

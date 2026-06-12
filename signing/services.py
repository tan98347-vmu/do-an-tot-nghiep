"""
Sau khi ký, service không lưu ngay mà gọi:

  verify_report = validate_pdf_signatures(signed_working_copy)

  Tại signing/services.py:1117.

  Chỉ khi chữ ký vừa tạo có trạng thái safe và fingerprint certificate đúng với credential của user thì mới:

  - Thay working_pdf.
  - Đánh dấu task là signed.
  - Tạo PdfSignatureRecord.
  - Mở bước ký tiếp theo.


  - services.py: điều phối toàn bộ nghiệp vụ ký và kiểm tra.
  - pki.py: thực hiện kỹ thuật mật mã, gồm cả tạo chữ ký bằng private key và xác minh bằng public key.

  ## services.py

  signing/services.py quyết định:

  - User có quyền ký không.
  - Mật khẩu xác nhận có đúng không.
  - Task đã đến lượt ký chưa.
  - Lấy credential nào của user.
  - Gọi pki.py để ký.
  - Gọi pki.py để kiểm tra chữ ký vừa tạo.
  - Cập nhật trạng thái SigningTask.
  - Chuyển sang người ký tiếp theo.
  - Hoàn tất packet.
  - Tạo SignedPdfDocument.
  - Lưu kết quả kiểm tra vào database.

"""

import logging
import shutil
import tempfile
from pathlib import Path

import fitz
from django.conf import settings
from django.core.files.base import File
from django.db import transaction
from django.utils import timezone

from accounts.tenancy import get_user_company, targets_share_company
from documents.models import DOC_STATUS_FINAL, SHARE_ACTIVE
from documents.pdf_preview import DocumentPreviewUnavailable, build_document_preview_pdf
from .models import (
    CREDENTIAL_PROVIDER_INTERNAL_PKI,
    CREDENTIAL_STATUS_ACTIVE,
    PACKET_ACTIVE,
    PACKET_COMPLETED,
    PACKET_INVALIDATED,
    PACKET_REJECTED,
    PROPOSAL_APPROVED,
    PROPOSAL_INVALIDATED,
    PROPOSAL_PENDING_HR_REVIEW,
    PROPOSAL_REJECTED,
    SIGNATURE_MODE_INTERNAL_APPROVAL,
    SIGNATURE_MODE_PDF_PKCS7,
    TASK_AVAILABLE,
    TASK_BLOCKED,
    TASK_CANCELLED,
    TASK_REJECTED,
    TASK_SIGNED,
    VERIFY_STATUS_INTERNAL_APPROVAL,
    VERIFY_STATUS_SAFE,
    VERIFY_STATUS_TAMPERED,
    VERIFY_STATUS_UNKNOWN,
    is_internal_approval_mode,
    PdfSignatureRecord,
    SignedPdfDocument,
    SigningPacket,
    SigningProposal,
    SigningProposalSigner,
    SigningTask,
    UserSigningCredential,
)
from .internal_pki import ensure_user_signing_credential
from .pki import (
    PkiDependencyError,
    PreparedSignatureField,
    RemoteHsmError,
    RemoteHsmSigner,
    certificate_metadata_from_pem,
    prepare_pdf_signature_fields,
    sign_pdf_incremental,
    validate_pdf_signatures,
)

logger = logging.getLogger('signing')

class SigningFlowError(Exception):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `SigningFlowError` gom mot loai loi backend co chu dich de service hoac endpoint trong file `signing/services.py` co the phan nhanh ro rang.
    Vai tro cua no trong frontend: Frontend khong nhin thay lop loi nay truc tiep; no chi nhan HTTP status, toast hoac thong diep da duoc endpoint quy doi tu loi do.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi module hien tai.
    Tac dung: Tach rieng loi `SigningFlowError` de luong xu ly khong phai dung exception chung chung kho chan doan.
    """
    pass


def _ensure_same_company_targets(*targets):
    if targets_share_company(*targets):
        return
    raise SigningFlowError('Moi thanh phan trong quy trinh ky phai thuoc cung mot cong ty.')

def _file_sha256(path):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_file_sha256` la helper noi bo trong file `signing/services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `latest_safe_signed_pdf`, `create_signing_proposal`, `start_signing_flow` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    import hashlib

    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def _safe_filename(value):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_safe_filename` la helper noi bo trong file `signing/services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `latest_safe_signed_pdf`, `create_signing_proposal`, `start_signing_flow` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in (value or '').strip()) or 'file'

def _current_source_version(document):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_current_source_version` la helper noi bo trong file `signing/services.py`, chiu trach nhiem quan ly du lieu phien ban trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can quan ly du lieu phien ban roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `latest_safe_signed_pdf`, `create_signing_proposal`, `start_signing_flow` goi lai.
    Tac dung: Don buoc quan ly du lieu phien ban xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return document.versions.filter(version_number=document.version_number).first()

def _current_docx_sha256(document):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_current_docx_sha256` la helper noi bo trong file `signing/services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `latest_safe_signed_pdf`, `create_signing_proposal`, `start_signing_flow` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if not getattr(document, 'output_file', None):
        raise SigningFlowError('Van ban khong co file DOCX de khoi tao quy trinh ky.')
    return _file_sha256(document.output_file.path)

def _validate_document_can_enter_signing(document):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_validate_document_can_enter_signing` la helper noi bo trong file `signing/services.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi van ban trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly du lieu hoac thao tac lien quan toi van ban roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `latest_safe_signed_pdf`, `create_signing_proposal`, `start_signing_flow` goi lai.
    Tac dung: Don buoc xu ly du lieu hoac thao tac lien quan toi van ban xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if document.status != DOC_STATUS_FINAL:
        raise SigningFlowError('Chi van ban da chuyen sang Chinh thuc moi duoc de xuat ky.')
    if document.is_archived:
        raise SigningFlowError('Khong the ky van ban da luu tru.')
    if document.share_status != SHARE_ACTIVE:
        raise SigningFlowError('Van ban phai hoan tat luong phe duyet/chia se truoc khi ky.')
    if not document.output_file:
        raise SigningFlowError('Van ban chua co file DOCX de chuyen sang PDF ky.')

def _default_signature_mode():
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_default_signature_mode` la helper noi bo trong file `signing/services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `latest_safe_signed_pdf`, `create_signing_proposal`, `start_signing_flow` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    configured = getattr(settings, 'SIGNING_DEFAULT_SIGNATURE_MODE', SIGNATURE_MODE_PDF_PKCS7)
    if configured in {SIGNATURE_MODE_INTERNAL_APPROVAL, SIGNATURE_MODE_PDF_PKCS7}:
        return configured
    return SIGNATURE_MODE_PDF_PKCS7

def _invalidate_open_flows(document, reason):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_invalidate_open_flows` la helper noi bo trong file `signing/services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `latest_safe_signed_pdf`, `create_signing_proposal`, `start_signing_flow` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    now = timezone.now()
    open_proposals = SigningProposal.objects.filter(
        document=document,
        status__in=[PROPOSAL_PENDING_HR_REVIEW, PROPOSAL_APPROVED],
    )
    for proposal in open_proposals.select_related('packet'):
        proposal.status = PROPOSAL_INVALIDATED
        proposal.invalidated_reason = reason
        proposal.save(update_fields=['status', 'invalidated_reason', 'updated_at'])
        packet = getattr(proposal, 'packet', None)
        if packet and packet.status == PACKET_ACTIVE:
            packet.status = PACKET_INVALIDATED
            packet.invalidated_at = now
            packet.rejection_reason = reason
            packet.save(update_fields=['status', 'invalidated_at', 'rejection_reason', 'updated_at'])
            packet.tasks.filter(status__in=[TASK_BLOCKED, TASK_AVAILABLE]).update(status=TASK_CANCELLED)

def latest_safe_signed_pdf(document, signer=None):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `latest_safe_signed_pdf` la ham nghiep vu chinh trong file `signing/services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_file_sha256`, `_safe_filename`, `_current_source_version` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    qs = SignedPdfDocument.objects.filter(
        source_document=document,
        source_version_number=document.version_number,
    ).select_related('packet')
    if getattr(document, 'company_id', None):
        qs = qs.filter(company=document.company)
    if signer is not None:
        qs = qs.filter(packet__tasks__signer_user=signer)
    for signed_doc in qs.distinct().order_by('-created_at'):
        report = get_signed_pdf_integrity_report(signed_doc)
        if report.get('is_safe'):
            return signed_doc, report
    return None, None

def create_signing_proposal(document, proposed_by, signers, proposal_note='', allow_non_owner=False):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `create_signing_proposal` la ham nghiep vu chinh trong file `signing/services.py`, chiu trach nhiem tao moi ban ghi hoac khoi tao mot luong xu ly trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tao moi ban ghi hoac khoi tao mot luong xu ly roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_file_sha256`, `_safe_filename`, `_current_source_version` trong module nay.
    Tac dung: Don buoc tao moi ban ghi hoac khoi tao mot luong xu ly xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    _validate_document_can_enter_signing(document)
    if not allow_non_owner and document.owner_id != proposed_by.id:
        raise SigningFlowError('Chi chu so huu van ban moi duoc de xuat quy trinh ky.')
    if not signers:
        raise SigningFlowError('Can it nhat mot nguoi ky.')
    _ensure_same_company_targets(document, proposed_by, *(item.get('user') for item in signers))

    source_version = _current_source_version(document)
    source_hash = _current_docx_sha256(document)
    dedupe = set()
    cleaned_signers = []

    for index, signer in enumerate(signers, start=1):
        signer_user = signer['user']
        display_role = str(signer.get('display_role') or '').strip()
        if not display_role:
            raise SigningFlowError('Moi nguoi ky phai co vai tro hien thi.')
        step_no = max(int(signer.get('step_no') or 1), 1)
        required = bool(signer.get('required', True))
        group_context = str(signer.get('group_context') or '').strip()
        key = (signer_user.id, display_role.lower(), step_no)
        if key in dedupe:
            raise SigningFlowError('Danh sach nguoi ky dang bi trung lap.')
        dedupe.add(key)
        cleaned_signers.append({
            'user': signer_user,
            'display_role': display_role,
            'step_no': step_no,
            'required': required,
            'group_context': group_context,
            'sort_order': index,
        })

    with transaction.atomic():
        _invalidate_open_flows(document, 'Da co de xuat ky moi thay the quy trinh truoc do.')
        proposal = SigningProposal.objects.create(
            document=document,
            company=document.company,
            source_version=source_version,
            source_version_number=document.version_number,
            source_docx_sha256=source_hash,
            proposed_by=proposed_by,
            proposal_note=proposal_note,
        )
        SigningProposalSigner.objects.bulk_create([
            SigningProposalSigner(
                proposal=proposal,
                signer_user=item['user'],
                display_role=item['display_role'],
                group_context=item['group_context'],
                step_no=item['step_no'],
                required=item['required'],
                sort_order=item['sort_order'],
            )
            for item in cleaned_signers
        ])
    logger.info(
        'proposal created | proposal_id=%s | document_id=%s | signers=%s',
        proposal.pk,
        document.pk,
        len(cleaned_signers),
    )
    return proposal

def start_signing_flow(document, proposed_by, signers, proposal_note='', allow_non_owner=False):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `start_signing_flow` la ham nghiep vu chinh trong file `signing/services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_file_sha256`, `_safe_filename`, `_current_source_version` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    proposal = create_signing_proposal(
        document,
        proposed_by,
        signers,
        proposal_note=proposal_note,
        allow_non_owner=allow_non_owner,
    )
    try:
        packet = approve_signing_proposal(
            proposal,
            proposed_by,
            review_note='Direct signing flow activated immediately by the document owner.',
        )
    except Exception:
        try:
            proposal.status = PROPOSAL_INVALIDATED
            proposal.invalidated_reason = 'Khoi tao quy trinh ky truc tiep that bai.'
            proposal.save(update_fields=['status', 'invalidated_reason', 'updated_at'])
        except Exception:
            pass
        raise
    proposal.refresh_from_db()
    return proposal, packet

def ensure_signing_task_for_user(
    document,
    actor,
    *,
    display_role='Nguoi xu ly hom thu',
    group_context='',
    proposal_note='',
):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `ensure_signing_task_for_user` la ham nghiep vu chinh trong file `signing/services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_file_sha256`, `_safe_filename`, `_current_source_version` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    actor_company = get_user_company(actor)
    existing_active_qs = SigningTask.objects.filter(
        packet__document=document,
        packet__source_version_number=document.version_number,
        packet__status=PACKET_ACTIVE,
        signer_user=actor,
    )
    if actor_company is not None:
        existing_active_qs = existing_active_qs.filter(company=actor_company)
    existing_active = (
        existing_active_qs.select_related('packet', 'packet__proposal')
        .order_by('packet__activated_at', 'id')
        .first()
    )
    if actor_company is not None and existing_active is not None and existing_active.company_id not in (None, actor_company.id):
        existing_active = None
    if existing_active is not None:
        return {
            'proposal': existing_active.packet.proposal,
            'packet': existing_active.packet,
            'task': existing_active,
            'created': False,
            'already_signed': False,
            'signed_pdf': None,
        }

    signed_doc, _ = latest_safe_signed_pdf(document, signer=actor)
    if signed_doc is not None:
        signed_task = (
            signed_doc.packet.tasks.filter(signer_user=actor)
            .select_related('packet', 'packet__proposal')
            .order_by('-signed_at', '-id')
            .first()
        )
        if signed_task is not None:
            return {
                'proposal': signed_task.packet.proposal,
                'packet': signed_task.packet,
                'task': signed_task,
                'created': False,
                'already_signed': True,
                'signed_pdf': signed_doc,
            }

    proposal, packet = start_signing_flow(
        document,
        actor,
        [
            {
                'user': actor,
                'display_role': display_role,
                'step_no': 1,
                'required': True,
                'group_context': group_context,
            },
        ],
        proposal_note=proposal_note,
        allow_non_owner=True,
    )
    task = packet.tasks.select_related('packet', 'packet__proposal').get(signer_user=actor)
    return {
        'proposal': proposal,
        'packet': packet,
        'task': task,
        'created': True,
        'already_signed': False,
        'signed_pdf': None,
    }

def _copy_path_to_field(field, source_path, filename):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_copy_path_to_field` la helper noi bo trong file `signing/services.py`, chiu trach nhiem chuan bi hoac dong bo truong du lieu lien quan trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can chuan bi hoac dong bo truong du lieu lien quan roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `latest_safe_signed_pdf`, `create_signing_proposal`, `start_signing_flow` goi lai.
    Tac dung: Don buoc chuan bi hoac dong bo truong du lieu lien quan xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    with Path(source_path).open('rb') as source_handle:
        field.save(filename, File(source_handle), save=False)

def _ensure_proposal_still_current(proposal):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_ensure_proposal_still_current` la helper noi bo trong file `signing/services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `latest_safe_signed_pdf`, `create_signing_proposal`, `start_signing_flow` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    document = proposal.document
    _validate_document_can_enter_signing(document)
    current_hash = _current_docx_sha256(document)
    if document.version_number != proposal.source_version_number or current_hash != proposal.source_docx_sha256:
        proposal.status = PROPOSAL_INVALIDATED
        proposal.invalidated_reason = 'Van ban da thay doi sau khi de xuat danh sach nguoi ky.'
        proposal.save(update_fields=['status', 'invalidated_reason', 'updated_at'])
        raise SigningFlowError('Van ban da thay doi. Hay tao lai de xuat danh sach nguoi ky moi.')

def _signature_field_name_for_signer(proposal_signer):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_signature_field_name_for_signer` la helper noi bo trong file `signing/services.py`, chiu trach nhiem chuan bi hoac dong bo truong du lieu lien quan trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can chuan bi hoac dong bo truong du lieu lien quan roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `latest_safe_signed_pdf`, `create_signing_proposal`, `start_signing_flow` goi lai.
    Tac dung: Don buoc chuan bi hoac dong bo truong du lieu lien quan xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return f'sig_proposal_{proposal_signer.proposal_id}_slot_{proposal_signer.pk}'

def _prepare_pdf_for_packet(preview_pdf_path, ordered_signers, signature_mode):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_prepare_pdf_for_packet` la helper noi bo trong file `signing/services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `latest_safe_signed_pdf`, `create_signing_proposal`, `start_signing_flow` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if signature_mode != SIGNATURE_MODE_PDF_PKCS7:
        return preview_pdf_path, {}

    temp_dir = Path(tempfile.mkdtemp(prefix='signing-pki-prepare-'))
    prepared_pdf_path = temp_dir / 'prepared_snapshot.pdf'
    field_map = {}
    prepared_fields = []
    for signer in ordered_signers:
        field_name = _signature_field_name_for_signer(signer)
        field_map[signer.pk] = field_name
        signer_name = signer.signer_user.get_full_name() or signer.signer_user.username
        prepared_fields.append(
            PreparedSignatureField(
                field_name=field_name,
                signer_name=signer_name,
                display_role=signer.display_role,
                step_no=signer.step_no,
            )
        )
    try:
        prepare_pdf_signature_fields(preview_pdf_path, prepared_pdf_path, prepared_fields)
    except PkiDependencyError as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise SigningFlowError(
            'May chu chua san sang cho ky PDF PKI. Thieu thu vien pyHanko/pyhanko-certvalidator/asn1crypto. '
            'Hay cai dependency PKI roi thu duyet lai.'
        ) from exc
    except RemoteHsmError as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise SigningFlowError(
            f'Cau hinh ky PDF PKI chua san sang: {exc}'
        ) from exc
    except OSError as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise SigningFlowError(
            f'Khong the chuan bi PDF cho quy trinh ky PKI: {exc}'
        ) from exc
    return prepared_pdf_path, field_map

def approve_signing_proposal(proposal, reviewer, review_note=''):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `approve_signing_proposal` la ham nghiep vu chinh trong file `signing/services.py`, chiu trach nhiem duyet mot yeu cau nghiep vu trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can duyet mot yeu cau nghiep vu roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_file_sha256`, `_safe_filename`, `_current_source_version` trong module nay.
    Tac dung: Don buoc duyet mot yeu cau nghiep vu xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if proposal.status != PROPOSAL_PENDING_HR_REVIEW:
        raise SigningFlowError('De xuat nay khong con o trang thai cho duyet.')

    _ensure_proposal_still_current(proposal)

    try:
        preview_pdf_path = build_document_preview_pdf(proposal.document)
    except DocumentPreviewUnavailable as exc:
        raise SigningFlowError(exc.detail) from exc

    signature_mode = _default_signature_mode()
    ordered_signers = list(proposal.signers.select_related('signer_user').order_by('step_no', 'sort_order', 'id'))
    prepared_pdf_path = preview_pdf_path
    field_map = {}
    cleanup_dir = None
    if signature_mode == SIGNATURE_MODE_PDF_PKCS7:
        prepared_pdf_path, field_map = _prepare_pdf_for_packet(preview_pdf_path, ordered_signers, signature_mode)
        cleanup_dir = prepared_pdf_path.parent

    snapshot_name = f'{_safe_filename(proposal.document.title)}_snapshot_v{proposal.source_version_number}.pdf'
    working_name = f'{_safe_filename(proposal.document.title)}_working_v{proposal.source_version_number}.pdf'

    try:
        with transaction.atomic():
            packet = SigningPacket(
                proposal=proposal,
                company=proposal.company,
                document=proposal.document,
                source_version=proposal.source_version,
                source_version_number=proposal.source_version_number,
                source_docx_sha256=proposal.source_docx_sha256,
                status=PACKET_ACTIVE,
                signature_mode=signature_mode,
            )
            _copy_path_to_field(packet.pdf_snapshot, prepared_pdf_path, snapshot_name)
            _copy_path_to_field(packet.working_pdf, prepared_pdf_path, working_name)
            packet.save()
            packet.pdf_hash = _file_sha256(packet.working_pdf.path)
            first_step = ordered_signers[0].step_no if ordered_signers else 1
            packet.current_step = first_step
            packet.save(update_fields=['pdf_hash', 'current_step', 'updated_at'])

            now = timezone.now()
            task_records = []
            for signer in ordered_signers:
                task_records.append(SigningTask(
                    packet=packet,
                    company=packet.company,
                    proposal_signer=signer,
                    signer_user=signer.signer_user,
                    display_role=signer.display_role,
                    group_context=signer.group_context,
                    step_no=signer.step_no,
                    sort_order=signer.sort_order,
                    required=signer.required,
                    signature_field_name=field_map.get(signer.pk, ''),
                    status=TASK_AVAILABLE if signer.step_no == packet.current_step else TASK_BLOCKED,
                    notified_at=now,
                ))
            SigningTask.objects.bulk_create(task_records)

            proposal.status = PROPOSAL_APPROVED
            proposal.hr_reviewed_by = reviewer
            proposal.hr_reviewed_at = now
            proposal.review_note = review_note
            proposal.save(update_fields=['status', 'hr_reviewed_by', 'hr_reviewed_at', 'review_note', 'updated_at'])
    finally:
        if cleanup_dir is not None:
            shutil.rmtree(cleanup_dir, ignore_errors=True)

    logger.info(
        'proposal approved | proposal_id=%s | packet_id=%s | reviewer_id=%s | signature_mode=%s',
        proposal.pk,
        packet.pk,
        reviewer.id,
        signature_mode,
    )
    return packet

def reject_signing_proposal(proposal, reviewer, review_note=''):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `reject_signing_proposal` la ham nghiep vu chinh trong file `signing/services.py`, chiu trach nhiem tu choi mot yeu cau nghiep vu trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tu choi mot yeu cau nghiep vu roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_file_sha256`, `_safe_filename`, `_current_source_version` trong module nay.
    Tac dung: Don buoc tu choi mot yeu cau nghiep vu xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if proposal.status != PROPOSAL_PENDING_HR_REVIEW:
        raise SigningFlowError('De xuat nay khong con o trang thai cho duyet.')
    proposal.status = PROPOSAL_REJECTED
    proposal.hr_reviewed_by = reviewer
    proposal.hr_reviewed_at = timezone.now()
    proposal.review_note = review_note
    proposal.save(update_fields=['status', 'hr_reviewed_by', 'hr_reviewed_at', 'review_note', 'updated_at'])
    logger.info('proposal rejected | proposal_id=%s | reviewer_id=%s', proposal.pk, reviewer.id)
    return proposal

def _ensure_packet_current(packet):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_ensure_packet_current` la helper noi bo trong file `signing/services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `latest_safe_signed_pdf`, `create_signing_proposal`, `start_signing_flow` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    document = packet.document
    if packet.status != PACKET_ACTIVE:
        raise SigningFlowError('Phien ky nay khong con hoat dong.')
    current_hash = _current_docx_sha256(document)
    if document.version_number != packet.source_version_number or current_hash != packet.source_docx_sha256:
        packet.status = PACKET_INVALIDATED
        packet.invalidated_at = timezone.now()
        packet.rejection_reason = 'Van ban goc da thay doi trong qua trinh ky.'
        packet.save(update_fields=['status', 'invalidated_at', 'rejection_reason', 'updated_at'])
        packet.tasks.filter(status__in=[TASK_BLOCKED, TASK_AVAILABLE]).update(status=TASK_CANCELLED)
        raise SigningFlowError('Van ban goc da thay doi. Phien ky da bi vo hieu hoa.')

def _find_or_create_ledger_page(pdf_document, packet_id):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_find_or_create_ledger_page` la helper noi bo trong file `signing/services.py`, chiu trach nhiem tao moi ban ghi hoac khoi tao mot luong xu ly trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tao moi ban ghi hoac khoi tao mot luong xu ly roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `latest_safe_signed_pdf`, `create_signing_proposal`, `start_signing_flow` goi lai.
    Tac dung: Don buoc tao moi ban ghi hoac khoi tao mot luong xu ly xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    marker = f'AI DOC SIGN LEDGER {packet_id}'
    for page in pdf_document:
        if page.search_for(marker):
            return page
    page = pdf_document.new_page()
    page.insert_text(fitz.Point(36, 36), marker, fontsize=8, color=(0.5, 0.5, 0.5))
    page.insert_text(fitz.Point(36, 58), 'TRANG KY NOI BO', fontsize=16, color=(0.1, 0.2, 0.45))
    return page

def _append_signature_stamp(packet, task, signer):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_append_signature_stamp` la helper noi bo trong file `signing/services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `latest_safe_signed_pdf`, `create_signing_proposal`, `start_signing_flow` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    source_path = Path(packet.working_pdf.path)
    temp_dir = tempfile.mkdtemp(prefix='signing-stamp-')
    try:
        working_copy = Path(temp_dir) / source_path.name
        stamped_copy = Path(temp_dir) / f'stamped_{source_path.name}'
        shutil.copy2(source_path, working_copy)
        pdf_document = fitz.open(str(working_copy))
        signed_so_far = packet.tasks.filter(status=TASK_SIGNED).count()
        page = _find_or_create_ledger_page(pdf_document, packet.pk)
        top = 90 + (signed_so_far * 96)
        if top > page.rect.height - 120:
            page = pdf_document.new_page()
            page.insert_text(fitz.Point(36, 36), f'AI DOC SIGN LEDGER {packet.pk}', fontsize=8, color=(0.5, 0.5, 0.5))
            page.insert_text(fitz.Point(36, 58), 'TRANG KY NOI BO (TIEP)', fontsize=16, color=(0.1, 0.2, 0.45))
            top = 90

        rect = fitz.Rect(36, top, page.rect.width - 36, top + 78)
        page.draw_rect(rect, color=(0.15, 0.35, 0.75), width=1.1)
        signed_at = timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M:%S')
        label = signer.get_full_name() or signer.username
        text = '\n'.join([
            f'Nguoi ky: {label}',
            f'Vai tro hien thi: {task.display_role}',
            f'Buoc ky: {task.step_no}',
            f'Thoi gian ky: {signed_at}',
            f'Ma packet: {packet.pk}',
            f'Hash PDF truoc khi ky: {packet.pdf_hash[:16]}',
        ])
        page.insert_textbox(
            fitz.Rect(rect.x0 + 10, rect.y0 + 8, rect.x1 - 10, rect.y1 - 8),
            text,
            fontsize=10,
            color=(0.05, 0.1, 0.2),
            align=0,
        )
        pdf_document.save(str(stamped_copy), incremental=False, encryption=fitz.PDF_ENCRYPT_KEEP)
        pdf_document.close()
        shutil.copy2(stamped_copy, source_path)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def _complete_packet_if_possible(packet):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_complete_packet_if_possible` la helper noi bo trong file `signing/services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `latest_safe_signed_pdf`, `create_signing_proposal`, `start_signing_flow` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    required_pending = packet.tasks.filter(required=True, status__in=[TASK_AVAILABLE, TASK_BLOCKED])
    if required_pending.exists():
        return None

    packet.tasks.filter(required=False, status__in=[TASK_AVAILABLE, TASK_BLOCKED]).update(status=TASK_CANCELLED)
    packet.status = PACKET_COMPLETED
    packet.completed_at = timezone.now()
    packet.save(update_fields=['status', 'completed_at', 'updated_at'])

    signed_doc = SignedPdfDocument(
        packet=packet,
        title=packet.document.title,
        company=packet.company,
        owner=packet.document.owner,
        source_document=packet.document,
        source_version_number=packet.source_version_number,
        signature_mode=packet.signature_mode,
        verification_status=VERIFY_STATUS_INTERNAL_APPROVAL if is_internal_approval_mode(packet.signature_mode) else VERIFY_STATUS_UNKNOWN,
        signature_count=packet.tasks.filter(status=TASK_SIGNED).count(),
    )
    filename = f'{_safe_filename(packet.document.title)}_signed_v{packet.source_version_number}.pdf'
    with Path(packet.working_pdf.path).open('rb') as signed_handle:
        signed_doc.signed_pdf_file.save(filename, File(signed_handle), save=False)
    signed_doc.save()
    signed_doc.file_hash = _file_sha256(signed_doc.signed_pdf_file.path)
    if packet.signature_mode == SIGNATURE_MODE_PDF_PKCS7:
        signed_doc.verification_status = VERIFY_STATUS_UNKNOWN
    signed_doc.save(update_fields=['file_hash', 'verification_status', 'signature_count'])
    packet.signature_records.filter(signed_pdf__isnull=True).update(signed_pdf=signed_doc)
    logger.info(
        'packet completed | packet_id=%s | signed_pdf_id=%s | signature_mode=%s',
        packet.pk,
        signed_doc.pk,
        packet.signature_mode,
    )
    return signed_doc

def _active_credential_for_user(user):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_active_credential_for_user` la helper noi bo trong file `signing/services.py`, chiu trach nhiem xu ly chung thu, khoa hoac ngu canh ky so trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly chung thu, khoa hoac ngu canh ky so roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `latest_safe_signed_pdf`, `create_signing_proposal`, `start_signing_flow` goi lai.
    Tac dung: Don buoc xu ly chung thu, khoa hoac ngu canh ky so xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    now = timezone.now()
    credential = UserSigningCredential.objects.filter(
        user=user,
        status=CREDENTIAL_STATUS_ACTIVE,
        valid_from__lte=now,
        valid_to__gte=now,
    ).order_by('-updated_at').first()
    if credential is not None:
        return credential
    try:
        return ensure_user_signing_credential(user)
    except Exception:
        return None

def get_signature_context_for_task(task, actor):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `get_signature_context_for_task` la ham nghiep vu chinh trong file `signing/services.py`, chiu trach nhiem chuan bi ngu canh cho buoc xu ly phia sau trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can chuan bi ngu canh cho buoc xu ly phia sau roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_file_sha256`, `_safe_filename`, `_current_source_version` trong module nay.
    Tac dung: Don buoc chuan bi ngu canh cho buoc xu ly phia sau xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    context = {
        'task_id': task.id,
        'packet_id': task.packet_id,
        'signature_mode': task.packet.signature_mode,
        'available_now': task.status == TASK_AVAILABLE and task.packet.status == PACKET_ACTIVE,
        'credential_required': task.packet.signature_mode == SIGNATURE_MODE_PDF_PKCS7,
        'provider_ready': False,
        'provider_message': '',
        'credential_bound': False,
        'can_sign': False,
        'reason': '',
        'certificate': None,
    }
    if task.signer_user_id != actor.id:
        context['reason'] = 'Ban khong duoc phep ky yeu cau nay.'
        return context
    if task.packet.signature_mode != SIGNATURE_MODE_PDF_PKCS7:
        context['can_sign'] = context['available_now']
        context['reason'] = 'Che do xac nhan noi bo khong can credential HSM.'
        return context

    credential = _active_credential_for_user(actor)
    if credential is None:
        context['reason'] = 'User chua co credential PKI active hoac chung thu da het han.'
        return context

    try:
        cert_meta = certificate_metadata_from_pem(credential.certificate_pem)
    except Exception as exc:
        context['reason'] = f'Khong doc duoc chung thu cua user: {exc}'
        return context

    if str(credential.provider or '').strip().lower() == CREDENTIAL_PROVIDER_INTERNAL_PKI:
        provider_ready = True
        provider_message = 'Internal PKI credential is ready.'
    else:
        provider_ready, provider_message = RemoteHsmSigner().get_provider_readiness()
    context['provider_ready'] = provider_ready
    context['provider_message'] = provider_message
    context['credential_bound'] = True
    context['certificate'] = {
        'id': credential.id,
        'provider': credential.provider,
        'key_alias': credential.key_alias,
        'key_id': credential.key_id,
        'subject_dn': credential.subject_dn or cert_meta['subject_dn'],
        'issuer_dn': credential.issuer_dn or cert_meta['issuer_dn'],
        'serial_number': credential.serial_number or cert_meta['serial_number'],
        'valid_from': credential.valid_from.isoformat() if credential.valid_from else '',
        'valid_to': credential.valid_to.isoformat() if credential.valid_to else '',
        'status': credential.status,
        'fingerprint_sha256': cert_meta['fingerprint_sha256'],
    }
    context['can_sign'] = bool(context['available_now'] and provider_ready)
    if not context['can_sign']:
        context['reason'] = provider_message or 'Remote HSM chua san sang.'
    return context

def _internal_approval_signed_pdf_report(signed_doc):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_legacy_signed_pdf_report` la helper noi bo trong file `signing/services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `latest_safe_signed_pdf`, `create_signing_proposal`, `start_signing_flow` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    steps = []
    checked_at = timezone.now().isoformat()
    expected_hash = (signed_doc.file_hash or '').strip()
    actual_hash = ''

    if not getattr(signed_doc, 'signed_pdf_file', None):
        return {
            'status': VERIFY_STATUS_TAMPERED,
            'is_safe': False,
            'is_access_allowed': False,
            'summary': 'Van ban khong an toan. Tep PDF da ky khong ton tai.',
            'checked_at': checked_at,
            'signature_mode': SIGNATURE_MODE_INTERNAL_APPROVAL,
            'expected_hash': expected_hash,
            'actual_hash': actual_hash,
            'signature_count': signed_doc.signature_count or 0,
            'signer_reports': [],
            'steps': [
                {
                    'code': 'file_reference',
                    'label': 'Kiem tra tep PDF da ky',
                    'status': 'failed',
                    'detail': 'Ban ghi PDF da ky khong co tep du lieu.',
                },
            ],
        }

    try:
        actual_hash = _file_sha256(signed_doc.signed_pdf_file.path)
    except (FileNotFoundError, OSError):
        return {
            'status': VERIFY_STATUS_TAMPERED,
            'is_safe': False,
            'is_access_allowed': False,
            'summary': 'Van ban khong an toan. Tep PDF da ky da bi mat hoac bi thay doi.',
            'checked_at': checked_at,
            'signature_mode': SIGNATURE_MODE_INTERNAL_APPROVAL,
            'expected_hash': expected_hash,
            'actual_hash': actual_hash,
            'signature_count': signed_doc.signature_count or 0,
            'signer_reports': [],
            'steps': [
                {
                    'code': 'file_reference',
                    'label': 'Kiem tra tep PDF da ky',
                    'status': 'failed',
                    'detail': 'Khong tim thay tep PDF da ky tren he thong luu tru.',
                },
            ],
        }

    steps.append({
        'code': 'file_reference',
        'label': 'Kiem tra tep PDF da ky',
        'status': 'passed',
        'detail': 'Da tim thay tep PDF da ky tren he thong luu tru.',
    })

    if not expected_hash:
        expected_hash = actual_hash
        signed_doc.file_hash = actual_hash
        signed_doc.save(update_fields=['file_hash'])
        steps.append({
            'code': 'expected_hash',
            'label': 'Doc hash doi chieu da luu',
            'status': 'passed',
            'detail': 'Chua co hash goc, he thong da bo sung hash doi chieu hien tai.',
        })
    else:
        steps.append({
            'code': 'expected_hash',
            'label': 'Doc hash doi chieu da luu',
            'status': 'passed',
            'detail': 'Da doc duoc hash doi chieu cua PDF khi hoan tat ky.',
        })

    steps.append({
        'code': 'actual_hash',
        'label': 'Tinh hash hien tai cua tep PDF',
        'status': 'passed',
        'detail': f'SHA-256 hien tai bat dau bang {actual_hash[:16]}.',
    })

    if actual_hash != expected_hash:
        steps.append({
            'code': 'compare_hash',
            'label': 'Doi chieu hash',
            'status': 'failed',
            'detail': 'Hash hien tai khong trung khop voi hash da luu khi hoan tat ky.',
        })
        return {
            'status': VERIFY_STATUS_TAMPERED,
            'is_safe': False,
            'is_access_allowed': False,
            'summary': 'Van ban co dau hieu bi thay doi sau khi hoan tat ky.',
            'checked_at': checked_at,
            'signature_mode': SIGNATURE_MODE_INTERNAL_APPROVAL,
            'expected_hash': expected_hash,
            'actual_hash': actual_hash,
            'signature_count': signed_doc.signature_count or 0,
            'signer_reports': [],
            'steps': steps,
        }

    steps.append({
        'code': 'compare_hash',
        'label': 'Doi chieu hash',
        'status': 'passed',
        'detail': 'Hash hien tai trung khop voi hash da luu khi hoan tat ky.',
    })
    return {
        'status': VERIFY_STATUS_INTERNAL_APPROVAL,
        'is_safe': False,
        'is_access_allowed': True,
        'summary': 'Ban ghi nay su dung che do xac nhan noi bo. Hash tep hien van trung khop, nhung day khong phai chu ky so PDF nhung.',
        'checked_at': checked_at,
        'signature_mode': SIGNATURE_MODE_INTERNAL_APPROVAL,
        'expected_hash': expected_hash,
        'actual_hash': actual_hash,
        'signature_count': signed_doc.signature_count or 0,
        'signer_reports': [],
        'steps': steps,
    }

def _packet_task_map(packet):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_packet_task_map` la helper noi bo trong file `signing/services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `latest_safe_signed_pdf`, `create_signing_proposal`, `start_signing_flow` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    tasks = list(packet.tasks.select_related('signer_user').order_by('step_no', 'sort_order', 'id'))
    return {task.signature_field_name: task for task in tasks if task.signature_field_name}

def refresh_signed_pdf_verification(signed_doc):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `refresh_signed_pdf_verification` la ham nghiep vu chinh trong file `signing/services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_file_sha256`, `_safe_filename`, `_current_source_version` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if is_internal_approval_mode(signed_doc.signature_mode):
        report = _internal_approval_signed_pdf_report(signed_doc)
        signed_doc.verification_status = report['status']
        signed_doc.verification_checked_at = timezone.now()
        signed_doc.signature_count = signed_doc.signature_count or signed_doc.packet.tasks.filter(status=TASK_SIGNED).count()
        signed_doc.save(update_fields=['verification_status', 'verification_checked_at', 'signature_count'])
        return report

    try:
        report = validate_pdf_signatures(
            signed_doc.signed_pdf_file.path,
            task_by_field_name=_packet_task_map(signed_doc.packet),
        )
    except (PkiDependencyError, RemoteHsmError, OSError) as exc:
        raise SigningFlowError(str(exc)) from exc

    signed_doc.verification_status = report['status']
    signed_doc.verification_checked_at = timezone.now()
    signed_doc.signature_count = report.get('signature_count') or signed_doc.signature_count
    signed_doc.save(update_fields=['verification_status', 'verification_checked_at', 'signature_count'])

    reports_by_field = {item['field_name']: item for item in report.get('signer_reports', [])}
    for signature_record in signed_doc.signature_records.select_related('task').all():
        per_sig_report = reports_by_field.get(signature_record.signature_field_name, {})
        signature_record.verification_status = per_sig_report.get('status') or signature_record.verification_status
        signature_record.verification_report = per_sig_report
        signature_record.save(update_fields=['verification_status', 'verification_report'])
    return report

def get_signed_pdf_integrity_report(signed_doc):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `get_signed_pdf_integrity_report` la ham nghiep vu chinh trong file `signing/services.py`, chiu trach nhiem xac minh tinh hop le hoac toan ven trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xac minh tinh hop le hoac toan ven roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_file_sha256`, `_safe_filename`, `_current_source_version` trong module nay.
    Tac dung: Don buoc xac minh tinh hop le hoac toan ven xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return refresh_signed_pdf_verification(signed_doc)

def ensure_signed_pdf_integrity(signed_doc):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `ensure_signed_pdf_integrity` la ham nghiep vu chinh trong file `signing/services.py`, chiu trach nhiem xac minh tinh hop le hoac toan ven trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xac minh tinh hop le hoac toan ven roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_file_sha256`, `_safe_filename`, `_current_source_version` trong module nay.
    Tac dung: Don buoc xac minh tinh hop le hoac toan ven xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    report = get_signed_pdf_integrity_report(signed_doc)
    if not report.get('is_access_allowed', report.get('is_safe', False)):
        raise SigningFlowError(report['summary'])
    return report

def _advance_packet_if_needed(packet):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_advance_packet_if_needed` la helper noi bo trong file `signing/services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `latest_safe_signed_pdf`, `create_signing_proposal`, `start_signing_flow` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    current_step = packet.current_step
    step_tasks = packet.tasks.filter(step_no=current_step)
    if step_tasks.filter(required=True, status__in=[TASK_AVAILABLE, TASK_BLOCKED]).exists():
        return None

    step_tasks.filter(required=False, status__in=[TASK_AVAILABLE, TASK_BLOCKED]).update(status=TASK_CANCELLED)
    next_task = packet.tasks.filter(status=TASK_BLOCKED).order_by('step_no', 'sort_order', 'id').first()
    if not next_task:
        return _complete_packet_if_possible(packet)

    packet.current_step = next_task.step_no
    packet.save(update_fields=['current_step', 'updated_at'])
    packet.tasks.filter(packet=packet, step_no=next_task.step_no, status=TASK_BLOCKED).update(status=TASK_AVAILABLE)
    return None

def _sign_task_legacy(task, actor):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_sign_task_legacy` la helper noi bo trong file `signing/services.py`, chiu trach nhiem thuc hien buoc ky so hoac ghi nhan chu ky trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien buoc ky so hoac ghi nhan chu ky roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `latest_safe_signed_pdf`, `create_signing_proposal`, `start_signing_flow` goi lai.
    Tac dung: Don buoc thuc hien buoc ky so hoac ghi nhan chu ky xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    packet = task.packet
    _ensure_packet_current(packet)

    with transaction.atomic():
        task = SigningTask.objects.select_for_update().select_related('packet', 'signer_user').get(pk=task.pk)
        packet = SigningPacket.objects.select_for_update().get(pk=packet.pk)
        if task.status != TASK_AVAILABLE:
            raise SigningFlowError('Yeu cau ky nay da duoc cap nhat boi nguoi khac.')

        _append_signature_stamp(packet, task, actor)
        packet.pdf_hash = _file_sha256(packet.working_pdf.path)
        packet.save(update_fields=['pdf_hash', 'updated_at'])

        task.status = TASK_SIGNED
        task.signed_at = timezone.now()
        task.rejection_reason = ''
        task.save(update_fields=['status', 'signed_at', 'rejection_reason'])

        signed_doc = _advance_packet_if_needed(packet)
        if signed_doc:
            verification_report = refresh_signed_pdf_verification(signed_doc)
        else:
            verification_report = None
        return {
            'signed_pdf': signed_doc,
            'verification_report': verification_report,
            'signature_record': None,
        }

def _sign_task_pdf_pkcs7(task, actor):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_sign_task_pdf_pkcs7` la helper noi bo trong file `signing/services.py`, chiu trach nhiem thuc hien buoc ky so hoac ghi nhan chu ky trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien buoc ky so hoac ghi nhan chu ky roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `latest_safe_signed_pdf`, `create_signing_proposal`, `start_signing_flow` goi lai.
    Tac dung: Don buoc thuc hien buoc ky so hoac ghi nhan chu ky xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    packet = task.packet
    _ensure_packet_current(packet)
    if not task.signature_field_name:
        raise SigningFlowError('Task PKI signing is missing its PDF signature field binding.')

    credential = _active_credential_for_user(actor)
    if credential is None:
        raise SigningFlowError('Ban chua duoc cap credential PKI active hoac chung thu da het han.')

    if str(credential.provider or '').strip().lower() == CREDENTIAL_PROVIDER_INTERNAL_PKI:
        provider_ready = True
        provider_message = 'Internal PKI credential is ready.'
    else:
        provider_ready, provider_message = RemoteHsmSigner().get_provider_readiness()
        if not provider_ready:
            raise SigningFlowError(provider_message or 'Remote HSM chua san sang.')

    try:
        certificate_meta = certificate_metadata_from_pem(credential.certificate_pem)
    except Exception as exc:
        raise SigningFlowError(f'Khong doc duoc chung thu PKI cua ban: {exc}') from exc

    temp_dir = Path(tempfile.mkdtemp(prefix='signing-pdf-pkcs7-'))
    try:
        signed_working_copy = temp_dir / 'signed_working.pdf'
        with transaction.atomic():
            task = SigningTask.objects.select_for_update().select_related('packet', 'signer_user').get(pk=task.pk)
            packet = SigningPacket.objects.select_for_update().get(pk=packet.pk)
            if task.status != TASK_AVAILABLE:
                raise SigningFlowError('Yeu cau ky nay da duoc cap nhat boi nguoi khac.')

            try:
                sign_meta = sign_pdf_incremental(
                    packet.working_pdf.path,
                    signed_working_copy,
                    task.signature_field_name,
                    credential,
                    actor.get_full_name() or actor.username,
                    task.display_role,
                )
                verify_report = validate_pdf_signatures(
                    signed_working_copy,
                    task_by_field_name=_packet_task_map(packet),
                )
            except (PkiDependencyError, RemoteHsmError, OSError) as exc:
                raise SigningFlowError(str(exc)) from exc

            signature_report = None
            for item in verify_report.get('signer_reports', []):
                if item.get('field_name') == task.signature_field_name:
                    signature_report = item
                    break
            if signature_report is None:
                raise SigningFlowError('Khong tim thay chu ky vua duoc nhung trong PDF de doi chieu.')
            if signature_report.get('status') != VERIFY_STATUS_SAFE:
                raise SigningFlowError(signature_report.get('detail') or verify_report.get('summary') or 'Chu ky PDF vua tao khong hop le.')
            if signature_report.get('certificate_fingerprint') != certificate_meta['fingerprint_sha256']:
                raise SigningFlowError('Credential binding mismatch: chung thu trong PDF khong trung voi credential cua user.')

            shutil.copy2(signed_working_copy, packet.working_pdf.path)
            packet.pdf_hash = _file_sha256(packet.working_pdf.path)
            packet.save(update_fields=['pdf_hash', 'updated_at'])

            task.status = TASK_SIGNED
            task.signed_at = timezone.now()
            task.rejection_reason = ''
            task.save(update_fields=['status', 'signed_at', 'rejection_reason'])

            signature_record, _ = PdfSignatureRecord.objects.update_or_create(
                task=task,
                defaults={
                    'signed_pdf': None,
                    'packet': packet,
                    'signer_user': actor,
                    'signature_field_name': task.signature_field_name,
                    'certificate_fingerprint': sign_meta['certificate_fingerprint'],
                    'certificate_subject_dn': sign_meta['certificate_subject_dn'],
                    'certificate_serial_number': sign_meta['certificate_serial_number'],
                    'certificate_issuer_dn': sign_meta['certificate_issuer_dn'],
                    'signature_algorithm': sign_meta['signature_algorithm'],
                    'digest_algorithm': sign_meta['digest_algorithm'],
                    'provider_transaction_id': sign_meta['provider_transaction_id'],
                    'signed_at': task.signed_at,
                    'verification_status': signature_report.get('status', VERIFY_STATUS_SAFE),
                    'verification_report': signature_report,
                },
            )

            signed_doc = _advance_packet_if_needed(packet)
            if signed_doc:
                verify_report = refresh_signed_pdf_verification(signed_doc)

            logger.info(
                'pdf pkcs7 sign audit | user_id=%s | task_id=%s | packet_id=%s | cert_fp=%s | provider_tx_id=%s | verify_result=%s',
                actor.id,
                task.id,
                packet.id,
                sign_meta['certificate_fingerprint'],
                sign_meta['provider_transaction_id'],
                verify_report.get('status'),
            )
            return {
                'signed_pdf': signed_doc,
                'verification_report': verify_report,
                'signature_record': signature_record,
            }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def sign_task(task, actor, password):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `sign_task` la ham nghiep vu chinh trong file `signing/services.py`, chiu trach nhiem thuc hien buoc ky so hoac ghi nhan chu ky trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien buoc ky so hoac ghi nhan chu ky roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_file_sha256`, `_safe_filename`, `_current_source_version` trong module nay.
    Tac dung: Don buoc thuc hien buoc ky so hoac ghi nhan chu ky xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if task.signer_user_id != actor.id:
        raise SigningFlowError('Ban khong duoc phep ky yeu cau nay.')
    if not actor.check_password(password or ''):
        raise SigningFlowError('Mat khau xac nhan khong dung.')
    if task.status != TASK_AVAILABLE:
        raise SigningFlowError('Yeu cau ky nay chua san sang de ky.')

    if is_internal_approval_mode(task.packet.signature_mode):
        return _sign_task_legacy(task, actor)
    return _sign_task_pdf_pkcs7(task, actor)

def reject_task(task, actor, reason=''):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `reject_task` la ham nghiep vu chinh trong file `signing/services.py`, chiu trach nhiem tu choi mot yeu cau nghiep vu trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tu choi mot yeu cau nghiep vu roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_file_sha256`, `_safe_filename`, `_current_source_version` trong module nay.
    Tac dung: Don buoc tu choi mot yeu cau nghiep vu xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if task.signer_user_id != actor.id:
        raise SigningFlowError('Ban khong duoc phep tu choi yeu cau nay.')
    if task.status not in [TASK_AVAILABLE, TASK_BLOCKED]:
        raise SigningFlowError('Yeu cau ky nay khong con o trang thai xu ly.')

    packet = task.packet
    _ensure_packet_current(packet)
    now = timezone.now()
    with transaction.atomic():
        task = SigningTask.objects.select_for_update().select_related('packet').get(pk=task.pk)
        packet = SigningPacket.objects.select_for_update().get(pk=packet.pk)
        task.status = TASK_REJECTED
        task.rejected_at = now
        task.rejection_reason = reason or ''
        task.save(update_fields=['status', 'rejected_at', 'rejection_reason'])

        packet.status = PACKET_REJECTED
        packet.rejection_reason = reason or ''
        packet.save(update_fields=['status', 'rejection_reason', 'updated_at'])
        packet.tasks.filter(status__in=[TASK_AVAILABLE, TASK_BLOCKED]).exclude(pk=task.pk).update(status=TASK_CANCELLED)
    logger.info('task rejected | task_id=%s | packet_id=%s', task.pk, packet.pk)
    return packet


# === BEGIN R5: generic file signing ===
def sign_generic_file(file_path, private_key_pem, sig_path):
    """Ky so 1 file bat ky (khong rieng PDF) bang RSA-PSS SHA-256.

    Args:
        file_path: duong dan file plaintext can ky.
        private_key_pem: PEM bytes cua RSA private key (load qua serialization.load_pem_private_key).
        sig_path: duong dan output cho signature.

    Returns: str duong dan sig_path. Raise OSError neu khong ghi duoc.
    """
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, utils

    key = serialization.load_pem_private_key(private_key_pem, password=None)
    digest = _file_sha256(file_path)
    digest_bytes = bytes.fromhex(digest)
    signature = key.sign(
        digest_bytes,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH),
        utils.Prehashed(hashes.SHA256()),
    )
    Path(sig_path).write_bytes(signature)
    return str(sig_path)


def verify_generic_file(file_path, sig_path, public_key_pem):
    """Xac minh chu ky generic. Tra True/False, KHONG raise voi invalid signature."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, utils

    try:
        pub = serialization.load_pem_public_key(public_key_pem)
        digest_bytes = bytes.fromhex(_file_sha256(file_path))
        signature = Path(sig_path).read_bytes()
        pub.verify(
            signature,
            digest_bytes,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH),
            utils.Prehashed(hashes.SHA256()),
        )
        return True
    except (InvalidSignature, ValueError, OSError):
        return False
# === END R5 ===

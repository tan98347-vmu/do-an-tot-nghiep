"""
Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
Vai tro backend: File `documents/mailbox_services.py` giu hoac ho tro luong backend cho danh sach van ban, chi tiet van ban, version, chia se, luu tru, preview PDF, hom thu va xoa mem.
Vai tro cua no trong frontend: Cac man `/documents`, `/mailbox`, `/trash` va badge phe duyet doc ket qua do file nay cung cap hoac gian tiep lam thay doi.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`.
Tac dung: Bao dam vong doi van ban tu luc tao, chia se, xu ly hom thu toi luc phuc hoi hoac xoa vinh vien khong bi lech trang thai.
"""

from pathlib import Path

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from accounts.tenancy import targets_share_company
from documents.models import (
    Document,
    DocumentMailboxEntry,
    DocumentMailboxThread,
    MAILBOX_STATUS_COMPLETED,
    MAILBOX_STATUS_FORWARDED,
    MAILBOX_STATUS_REJECTED,
    MAILBOX_STATUS_VIEW,
)
from signing.services import (
    ensure_signing_task_for_user,
    get_signed_pdf_integrity_report,
    latest_safe_signed_pdf,
)

# class MailboxFlowError là kiểu ngoại lệ riêng để phân nhánh xử lý lỗi rõ ràng.
# vd: raise lớp này khi gặp lỗi đặc thù để nơi gọi bắt riêng.
class MailboxFlowError(Exception):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Lop `MailboxFlowError` gom mot loai loi backend co chu dich de service hoac endpoint trong file `documents/mailbox_services.py` co the phan nhanh ro rang.
    Vai tro cua no trong frontend: Frontend khong nhin thay lop loi nay truc tiep; no chi nhan HTTP status, toast hoac thong diep da duoc endpoint quy doi tu loi do.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi module hien tai.
    Tac dung: Tach rieng loi `MailboxFlowError` de luong xu ly khong phai dung exception chung chung kho chan doan.
    """
    pass

# def _file_sha256 để file sha256 (service nghiệp vụ).
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def _file_sha256(path):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_file_sha256` la helper noi bo trong file `documents/mailbox_services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Thuong duoc cac ham public nhu `forward_document`, `complete_mailbox_entry`, `reject_mailbox_entry` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    import hashlib

    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

# def _current_docx_sha256 để current docx sha256 (service nghiệp vụ).
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def _current_docx_sha256(document):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_current_docx_sha256` la helper noi bo trong file `documents/mailbox_services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Thuong duoc cac ham public nhu `forward_document`, `complete_mailbox_entry`, `reject_mailbox_entry` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if not getattr(document, 'output_file', None):
        raise MailboxFlowError('Van ban khong co file DOCX de tao luong hòm thu.')
    return _file_sha256(document.output_file.path)

# def _display_name để display name (service nghiệp vụ).
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def _display_name(user):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_display_name` la helper noi bo trong file `documents/mailbox_services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Thuong duoc cac ham public nhu `forward_document`, `complete_mailbox_entry`, `reject_mailbox_entry` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return user.get_full_name() or user.username

# def _latest_forwardable_signed_pdf để latest forwardable signed pdf (service nghiệp vụ).
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def _latest_forwardable_signed_pdf(document, actor=None):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_latest_forwardable_signed_pdf` la helper noi bo trong file `documents/mailbox_services.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Thuong duoc cac ham public nhu `forward_document`, `complete_mailbox_entry`, `reject_mailbox_entry` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return latest_safe_signed_pdf(document, signer=actor)

# def _ensure_actor_can_forward_document để đảm bảo actor can forward document (service nghiệp vụ).
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def _ensure_actor_can_forward_document(document, actor=None):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_ensure_actor_can_forward_document` la helper noi bo trong file `documents/mailbox_services.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi van ban trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly du lieu hoac thao tac lien quan toi van ban roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Thuong duoc cac ham public nhu `forward_document`, `complete_mailbox_entry`, `reject_mailbox_entry` goi lai.
    Tac dung: Don buoc xu ly du lieu hoac thao tac lien quan toi van ban xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    signed_doc, report = _latest_forwardable_signed_pdf(document, actor)
    if signed_doc is None:
        if actor is None:
            raise MailboxFlowError(
                'Van ban phai co mot PDF da ky an toan cho phien ban hien tai thi moi duoc forward.'
            )
        raise MailboxFlowError(
            'Ban phai co mot PDF da ky an toan do chinh ban ky tren phien ban hien tai cua van ban thi moi duoc forward tiep.'
        )
    return signed_doc, report

# def _update_thread_status để cập nhật thread status (service nghiệp vụ).
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def _update_thread_status(thread, *, actor, status_code, reason, summary):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `_update_thread_status` la helper noi bo trong file `documents/mailbox_services.py`, chiu trach nhiem cap nhat du lieu hien co trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can cap nhat du lieu hien co roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Thuong duoc cac ham public nhu `forward_document`, `complete_mailbox_entry`, `reject_mailbox_entry` goi lai.
    Tac dung: Don buoc cap nhat du lieu hien co xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    thread.status = status_code
    thread.last_action_by = actor
    thread.last_action_at = timezone.now()
    thread.last_action_reason = reason or ''
    thread.last_action_summary = summary
    thread.save(
        update_fields=[
            'status',
            'last_action_by',
            'last_action_at',
            'last_action_reason',
            'last_action_summary',
            'updated_at',
        ]
    )
    return thread

# def forward_document để forward document (service nghiệp vụ).
# vd: nhận đầu vào -> trả kết quả đã xử lý.
@transaction.atomic
def forward_document(
    document,
    actor,
    recipients,
    note='',
    parent_entry=None,
    signed_pdf_override=None,
):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `forward_document` la ham nghiep vu chinh trong file `documents/mailbox_services.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi van ban trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly du lieu hoac thao tac lien quan toi van ban roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_file_sha256`, `_current_docx_sha256`, `_display_name` trong module nay.
    Tac dung: Don buoc xu ly du lieu hoac thao tac lien quan toi van ban xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if not recipients:
        raise MailboxFlowError('Can it nhat mot nguoi nhan de forward van ban.')
    if not isinstance(document, Document):
        raise MailboxFlowError('Van ban khong hop le.')
    recipient_ids = set()
    cleaned_recipients = []
    for recipient in recipients:
        if not isinstance(recipient, User) or not recipient.is_active:
            raise MailboxFlowError('Danh sach nguoi nhan co tai khoan khong hop le hoac da bi khoa.')
        if recipient.id == actor.id:
            raise MailboxFlowError('Khong the forward van ban cho chinh minh.')
        if recipient.id in recipient_ids:
            continue
        recipient_ids.add(recipient.id)
        cleaned_recipients.append(recipient)

    if not cleaned_recipients:
        raise MailboxFlowError('Khong con nguoi nhan hop le de forward van ban.')
    if not targets_share_company(document, actor, parent_entry, *cleaned_recipients):
        raise MailboxFlowError('Chi co the forward van ban cho nguoi dung thuoc cung cong ty.')

    now = timezone.now()
    if parent_entry is None:
        if signed_pdf_override is not None:
            signed_doc = signed_pdf_override
            if signed_doc.source_document_id != document.id or signed_doc.source_version_number != document.version_number:
                raise MailboxFlowError('PDF da ky duoc chon khong khop voi phien ban van ban hien tai.')
            if not targets_share_company(document, actor, signed_doc):
                raise MailboxFlowError('PDF da ky duoc chon khong thuoc cung cong ty.')
            report = get_signed_pdf_integrity_report(signed_doc)
            if not report.get('is_access_allowed', report.get('is_safe', False)):
                raise MailboxFlowError('PDF da ky duoc chon khong an toan de forward.')
        else:
            signed_doc, _ = _ensure_actor_can_forward_document(document, None)
        thread = DocumentMailboxThread.objects.create(
            document=document,
            company=document.company,
            created_by=actor,
            source_version_number=document.version_number,
            source_docx_sha256=_current_docx_sha256(document),
            source_signed_pdf=signed_doc,
            status=MAILBOX_STATUS_FORWARDED,
            last_action_by=actor,
            last_action_at=now,
            last_action_summary=(
                f'Van ban dang duoc forward boi user {_display_name(actor)} den {len(cleaned_recipients)} nguoi.'
            ),
        )
    else:
        signed_doc, _ = _ensure_actor_can_forward_document(document, actor)
        thread = parent_entry.thread
        if parent_entry.forwarded_to_id != actor.id:
            raise MailboxFlowError('Chi nguoi duoc forward moi co the forward tiep entry nay.')
        parent_entry.status = MAILBOX_STATUS_FORWARDED
        parent_entry.actioned_by = actor
        parent_entry.actioned_at = now
        parent_entry.action_reason = note or ''
        parent_entry.save(
            update_fields=['status', 'actioned_by', 'actioned_at', 'action_reason', 'updated_at']
        )
        thread.source_signed_pdf = signed_doc
        thread.source_version_number = document.version_number
        thread.source_docx_sha256 = _current_docx_sha256(document)
        thread.save(update_fields=['source_signed_pdf', 'source_version_number', 'source_docx_sha256', 'updated_at'])
        _update_thread_status(
            thread,
            actor=actor,
            status_code=MAILBOX_STATUS_FORWARDED,
            reason=note,
            summary=f'Van ban dang duoc forward boi user {_display_name(actor)} den {len(cleaned_recipients)} nguoi.',
        )

    entries = []
    for recipient in cleaned_recipients:
        entries.append(
            DocumentMailboxEntry(
                thread=thread,
                company=thread.company,
                parent_entry=parent_entry,
                forwarded_by=actor,
                forwarded_to=recipient,
                signed_pdf=signed_doc,
                status=MAILBOX_STATUS_VIEW,
                note=note or '',
            )
        )
    DocumentMailboxEntry.objects.bulk_create(entries)

    # Phase 2 sharing: forward mailbox tu dong cap grant view cho recipient
    _ensure_mailbox_view_grants(document, cleaned_recipients, actor)
    return thread


# def _ensure_mailbox_view_grants để đảm bảo mailbox view grants (service nghiệp vụ).
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def _ensure_mailbox_view_grants(document, recipients, actor):
    """Tao ShareGrant scope=colleagues, permission=view, status=active cho recipient mailbox forward.

    Grant duoc xem la auto-approved boi vi forward mailbox la nghiep vu tin cay (signer/leader).
    Khong tao trung grant - dung update_or_create cua sharing.services.
    """
    if not recipients:
        return
    try:
        from sharing import services as sharing_services
        from sharing.constants import (
            PERMISSION_VIEW,
            SCOPE_COLLEAGUES,
        )
    except Exception:
        return

    for recipient in recipients:
        if recipient is None or recipient.pk == getattr(document, 'owner_id', None):
            continue
        try:
            grant = sharing_services.create_grant(
                resource=document,
                scope=SCOPE_COLLEAGUES,
                permission_level=PERMISSION_VIEW,
                target_user=recipient,
                actor=actor,
                auto_submit=True,
            )
            # Forward mailbox la luong tin cay - tu dong active.
            from sharing.constants import APPROVAL_ACTIVE

            if grant.approval_status != APPROVAL_ACTIVE:
                from django.utils import timezone

                grant.approval_status = APPROVAL_ACTIVE
                grant.approved_at = timezone.now()
                grant.approved_by = actor
                grant.save(update_fields=['approval_status', 'approved_at', 'approved_by', 'updated_at'])
        except Exception:
            # Khong fail mailbox flow neu grant tao loi - chi log
            import logging

            logging.getLogger(__name__).warning(
                'mailbox: khong tao duoc grant view cho doc_id=%s recipient_id=%s',
                document.pk, recipient.pk,
            )

# def complete_mailbox_entry để complete mailbox entry (service nghiệp vụ).
# vd: nhận đầu vào -> trả kết quả đã xử lý.
@transaction.atomic
def complete_mailbox_entry(entry, actor, reason):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `complete_mailbox_entry` la ham nghiep vu chinh trong file `documents/mailbox_services.py`, chiu trach nhiem xu ly luong hom thu hoac diem chuyen tiep tai lieu trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly luong hom thu hoac diem chuyen tiep tai lieu roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_file_sha256`, `_current_docx_sha256`, `_display_name` trong module nay.
    Tac dung: Don buoc xu ly luong hom thu hoac diem chuyen tiep tai lieu xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if entry.forwarded_to_id != actor.id:
        raise MailboxFlowError('Chi nguoi duoc giao entry moi co the hoan thanh.')
    if not reason.strip():
        raise MailboxFlowError('Can ghi ro ly do hoan thanh.')
    now = timezone.now()
    entry.status = MAILBOX_STATUS_COMPLETED
    entry.action_reason = reason.strip()
    entry.actioned_by = actor
    entry.actioned_at = now
    entry.save(update_fields=['status', 'action_reason', 'actioned_by', 'actioned_at', 'updated_at'])
    _update_thread_status(
        entry.thread,
        actor=actor,
        status_code=MAILBOX_STATUS_COMPLETED,
        reason=reason.strip(),
        summary=f'Da hoan thanh boi user {_display_name(actor)}, voi ly do: {reason.strip()}',
    )
    return entry

# def reject_mailbox_entry để từ chối mailbox entry (service nghiệp vụ).
# vd: nhận đầu vào -> trả kết quả đã xử lý.
@transaction.atomic
def reject_mailbox_entry(entry, actor, reason):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `reject_mailbox_entry` la ham nghiep vu chinh trong file `documents/mailbox_services.py`, chiu trach nhiem tu choi mot yeu cau nghiep vu trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tu choi mot yeu cau nghiep vu roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_file_sha256`, `_current_docx_sha256`, `_display_name` trong module nay.
    Tac dung: Don buoc tu choi mot yeu cau nghiep vu xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if entry.forwarded_to_id != actor.id:
        raise MailboxFlowError('Chi nguoi duoc giao entry moi co the tu choi xu ly.')
    if not reason.strip():
        raise MailboxFlowError('Can ghi ro ly do tu choi xu ly.')
    now = timezone.now()
    entry.status = MAILBOX_STATUS_REJECTED
    entry.action_reason = reason.strip()
    entry.actioned_by = actor
    entry.actioned_at = now
    entry.save(update_fields=['status', 'action_reason', 'actioned_by', 'actioned_at', 'updated_at'])
    _update_thread_status(
        entry.thread,
        actor=actor,
        status_code=MAILBOX_STATUS_REJECTED,
        reason=reason.strip(),
        summary=f'Da bi tu choi boi user {_display_name(actor)}, voi ly do: {reason.strip()}',
    )
    return entry

# def ensure_mailbox_entry_signing_task để đảm bảo mailbox entry signing task (service nghiệp vụ).
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def ensure_mailbox_entry_signing_task(entry, actor):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `ensure_mailbox_entry_signing_task` la ham nghiep vu chinh trong file `documents/mailbox_services.py`, chiu trach nhiem xu ly luong hom thu hoac diem chuyen tiep tai lieu trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly luong hom thu hoac diem chuyen tiep tai lieu roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_file_sha256`, `_current_docx_sha256`, `_display_name` trong module nay.
    Tac dung: Don buoc xu ly luong hom thu hoac diem chuyen tiep tai lieu xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if entry.forwarded_to_id != actor.id:
        raise MailboxFlowError('Chi nguoi duoc forward moi co the khoi tao tac vu ky cho entry nay.')
    return ensure_signing_task_for_user(
        entry.thread.document,
        actor,
        display_role='Nguoi xu ly hom thu',
        group_context='mailbox',
        proposal_note=f'Khoi tao tac vu ky tu mailbox entry {entry.id}.',
    )

# def mailbox_integrity_report để mailbox integrity report (service nghiệp vụ).
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def mailbox_integrity_report(entry):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `mailbox_integrity_report` la ham nghiep vu chinh trong file `documents/mailbox_services.py`, chiu trach nhiem xac minh tinh hop le hoac toan ven trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xac minh tinh hop le hoac toan ven roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_file_sha256`, `_current_docx_sha256`, `_display_name` trong module nay.
    Tac dung: Don buoc xac minh tinh hop le hoac toan ven xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if entry.signed_pdf_id is None:
        raise MailboxFlowError('Entry hòm thu nay khong co PDF da ky de doi chieu.')
    if not targets_share_company(entry, entry.thread, entry.signed_pdf):
        raise MailboxFlowError('Entry hom thu nay dang tro toi PDF khac cong ty.')
    report = get_signed_pdf_integrity_report(entry.signed_pdf)
    return {
        **report,
        'thread_id': entry.thread_id,
        'entry_id': entry.id,
        'document_id': entry.thread.document_id,
        'document_title': entry.thread.document.title,
    }

# def mailbox_thread_integrity_report để mailbox thread integrity report (service nghiệp vụ).
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def mailbox_thread_integrity_report(thread):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `mailbox_thread_integrity_report` la ham nghiep vu chinh trong file `documents/mailbox_services.py`, chiu trach nhiem xac minh tinh hop le hoac toan ven trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xac minh tinh hop le hoac toan ven roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `_file_sha256`, `_current_docx_sha256`, `_display_name` trong module nay.
    Tac dung: Don buoc xac minh tinh hop le hoac toan ven xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if thread.source_signed_pdf_id is None:
        raise MailboxFlowError('Luong hÃ²m thu nay khong co PDF da ky de doi chieu.')
    if not targets_share_company(thread, thread.source_signed_pdf):
        raise MailboxFlowError('Luong hom thu nay dang tro toi PDF khac cong ty.')
    report = get_signed_pdf_integrity_report(thread.source_signed_pdf)
    return {
        **report,
        'thread_id': thread.id,
        'entry_id': None,
        'document_id': thread.document_id,
        'document_title': thread.document.title,
    }

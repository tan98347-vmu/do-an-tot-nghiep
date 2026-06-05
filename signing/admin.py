# Chức năng web liên quan: Yêu cầu ký, PDF đã ký, Hòm thư và Ủy quyền ký số.
# Vai trò backend trong luồng: Tệp này giữ phần logic backend dùng chung cho đề xuất ký, nhiệm vụ ký, PDF đã ký, xác minh chữ ký và ủy quyền ký số, để các flow ở màn Yêu cầu ký, chi tiết ký, PDF đã ký, dialog đề xuất ký, dialog chọn người ký và màn Ủy quyền ký số không phải lặp lại cùng một rule ở nhiều nơi.
# Đầu vào/đầu ra chính: Giữ các helper, cấu hình và rule backend dùng lại ở nhiều flow khác nhau.
# Người dùng sẽ thấy trên web: Người dùng sẽ thấy dữ liệu, badge trạng thái, quyền nút và thông báo trên các chức năng Yêu cầu ký, PDF đã ký, Hòm thư và Ủy quyền ký số thay đổi đúng theo kết quả nghiệp vụ.

from django.contrib import admin

from .models import (
    DepartmentDelegation,
    PdfSignatureRecord,
    SignedPdfDocument,
    SigningPacket,
    SigningProposal,
    SigningProposalSigner,
    SigningSystemConfig,
    SigningTask,
    UserSigningCredential,
)

# [Web] `SigningSystemConfigAdmin` gom một cụm xử lý backend dùng chung cho nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số.

@admin.register(SigningSystemConfig)
class SigningSystemConfigAdmin(admin.ModelAdmin):
    list_display = ('id', 'hr_department', 'accounting_department', 'updated_at')

# [Web] `DepartmentDelegationAdmin` gom một cụm xử lý backend dùng chung cho nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số.

@admin.register(DepartmentDelegation)
class DepartmentDelegationAdmin(admin.ModelAdmin):
    list_display = ('department', 'delegate_user', 'permission_type', 'is_active', 'created_at')
    list_filter = ('permission_type', 'is_active', 'department')
    search_fields = ('department__name', 'delegate_user__username', 'delegate_user__first_name', 'delegate_user__last_name')

# [Web] `SigningProposalSignerInline` gom một cụm xử lý backend dùng chung cho nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số.

class SigningProposalSignerInline(admin.TabularInline):
    model = SigningProposalSigner
    extra = 0

# [Web] `SigningProposalAdmin` gom một cụm xử lý backend dùng chung cho nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số.

@admin.register(SigningProposal)
class SigningProposalAdmin(admin.ModelAdmin):
    list_display = ('id', 'document', 'proposed_by', 'status', 'hr_reviewed_by', 'created_at')
    list_filter = ('status',)
    search_fields = ('document__title', 'proposed_by__username')
    inlines = [SigningProposalSignerInline]

# [Web] `SigningTaskInline` gom một cụm xử lý backend dùng chung cho nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số.

class SigningTaskInline(admin.TabularInline):
    model = SigningTask
    extra = 0

# [Web] `PdfSignatureRecordInline` gom một cụm xử lý backend dùng chung cho nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số.

class PdfSignatureRecordInline(admin.TabularInline):
    model = PdfSignatureRecord
    extra = 0
    readonly_fields = ('signed_at', 'verification_status', 'provider_transaction_id')

# [Web] `SigningPacketAdmin` gom một cụm xử lý backend dùng chung cho nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số.

@admin.register(SigningPacket)
class SigningPacketAdmin(admin.ModelAdmin):
    list_display = ('id', 'document', 'signature_mode', 'status', 'current_step', 'activated_at', 'completed_at')
    list_filter = ('signature_mode', 'status')
    search_fields = ('document__title',)
    inlines = [SigningTaskInline, PdfSignatureRecordInline]

# [Web] `SignedPdfDocumentAdmin` gom một cụm xử lý backend dùng chung cho nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số.

@admin.register(SignedPdfDocument)
class SignedPdfDocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'signature_mode', 'verification_status', 'signature_count', 'owner', 'source_document', 'created_at')
    search_fields = ('title', 'owner__username', 'source_document__title')

# [Web] `UserSigningCredentialAdmin` gom một cụm xử lý backend dùng chung cho nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số.

@admin.register(UserSigningCredential)
class UserSigningCredentialAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'provider', 'serial_number', 'status', 'valid_from', 'valid_to', 'updated_at')
    list_filter = ('provider', 'status')
    search_fields = ('user__username', 'subject_dn', 'serial_number', 'issuer_dn', 'key_alias', 'key_id')

# [Web] `PdfSignatureRecordAdmin` gom một cụm xử lý backend dùng chung cho nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số.

@admin.register(PdfSignatureRecord)
class PdfSignatureRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'packet', 'task', 'signer_user', 'verification_status', 'provider_transaction_id', 'signed_at')
    list_filter = ('verification_status',)
    search_fields = ('signer_user__username', 'certificate_fingerprint', 'provider_transaction_id', 'signature_field_name')

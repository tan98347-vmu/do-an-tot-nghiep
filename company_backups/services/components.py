"""
Mapping component key -> (label hien thi, list model labels).
Cac model trong cung component se duoc backup/restore cung nhau.

DELETE_ORDER quan trong: phai xoa child truoc parent (theo FK) de tranh
ProtectedError / vi pham rang buoc khi restore replace.
"""

COMPONENT_ACCOUNTS = 'accounts'
COMPONENT_TEMPLATES = 'templates'
COMPONENT_DOCUMENTS = 'documents'
COMPONENT_PROMPTS = 'prompts'
COMPONENT_SIGNING = 'signing'
COMPONENT_AI_CONFIG = 'ai_config'
COMPONENT_LOGS = 'logs'

ALL_COMPONENTS = [
    COMPONENT_ACCOUNTS,
    COMPONENT_TEMPLATES,
    COMPONENT_DOCUMENTS,
    COMPONENT_PROMPTS,
    COMPONENT_SIGNING,
    COMPONENT_AI_CONFIG,
    COMPONENT_LOGS,
]

COMPONENT_LABELS = {
    COMPONENT_ACCOUNTS: 'Tai khoan, phong ban, nhom',
    COMPONENT_TEMPLATES: 'Mau van ban',
    COMPONENT_DOCUMENTS: 'Van ban',
    COMPONENT_PROMPTS: 'Prompt',
    COMPONENT_SIGNING: 'Ky so',
    COMPONENT_AI_CONFIG: 'Cau hinh AI + Knowledge Base',
    COMPONENT_LOGS: 'Log & lich su',
}

COMPONENT_MODELS = {
    COMPONENT_ACCOUNTS: [
        'accounts.UserAlias',
        'accounts.DepartmentMembership',
        'accounts.UserGroupMembership',
        'accounts.UserProfile',
        'accounts.CompanyUserMembership',
        'accounts.UserGroup',
        'accounts.CompanyPosition',
        'accounts.Department',
    ],
    COMPONENT_TEMPLATES: [
        'document_templates.TemplateFavorite',
        'document_templates.TemplateAudienceMember',
        'document_templates.TemplatePermission',
        'document_templates.PendingTemplateAssignment',
        'document_templates.TemplateApprovalLog',
        'document_templates.TemplateReviewNotification',
        'document_templates.TemplateManualEditSessionEvent',
        'document_templates.TemplateManualEditSession',
        'document_templates.TemplateVersion',
        'document_templates.DocumentTemplate',
        'document_templates.TemplateCategory',
    ],
    COMPONENT_DOCUMENTS: [
        'documents.DocumentFavorite',
        'documents.DocumentMailboxEntry',
        'documents.DocumentMailboxThread',
        'documents.DocumentManualEditSessionEvent',
        'documents.DocumentManualEditSession',
        'documents.DocumentVersion',
        'documents.Document',
        'documents.DocumentNumberConfig',
    ],
    COMPONENT_PROMPTS: [
        'prompts.PromptInjectionLog',
        'prompts.Prompt',
    ],
    COMPONENT_SIGNING: [
        'signing.PdfSignatureRecord',
        'signing.SigningProposalSigner',
        'signing.SignedPdfDocument',
        'signing.SigningTask',
        'signing.SigningPacket',
        'signing.SigningProposal',
        'signing.AssistantQuickSignPlan',
        'signing.DepartmentDelegation',
        'signing.SigningSystemConfig',
    ],
    COMPONENT_AI_CONFIG: [
        'ai_engine.ChatAudioAttachment',
        'ai_engine.ChatMessage',
        'ai_engine.ChatSession',
        'ai_engine.KnowledgeBase',
        'accounts.CompanyAIConfig',
    ],
    COMPONENT_LOGS: [
        'ai_engine.AIUsageLog',
        'word_ai.WordEditJobEvent',
        'word_ai.WordEditJob',
    ],
}


_CHILD_FILTERS = {
    'accounts.DepartmentMembership': ('department__company', 'department_id__in'),
    'accounts.UserGroupMembership': ('group__company', 'group_id__in'),
    'document_templates.TemplateVersion': ('template__company', 'template_id__in'),
    'document_templates.TemplatePermission': ('template__company', 'template_id__in'),
    'document_templates.TemplateAudienceMember': ('template__company', 'template_id__in'),
    'document_templates.PendingTemplateAssignment': ('document_template__company', 'document_template_id__in'),
    'document_templates.TemplateFavorite': ('template__company', 'template_id__in'),
    'document_templates.TemplateApprovalLog': ('template__company', 'template_id__in'),
    'document_templates.TemplateReviewNotification': ('template__company', 'template_id__in'),
    'document_templates.TemplateManualEditSessionEvent': ('session__company', 'session_id__in'),
    'documents.DocumentFavorite': ('document__company', 'document_id__in'),
    'documents.DocumentVersion': ('document__company', 'document_id__in'),
    'documents.DocumentManualEditSessionEvent': ('session__company', 'session_id__in'),
    'documents.DocumentNumberConfig': ('department__company', 'department_id__in'),
    'prompts.PromptInjectionLog': ('prompt__owner__company_membership__company', 'prompt_id__in'),
    'signing.SigningProposalSigner': ('proposal__company', 'proposal_id__in'),
    'signing.PdfSignatureRecord': ('signed_pdf__company', 'signed_pdf_id__in'),
    'ai_engine.ChatMessage': ('session__company', 'session_id__in'),
    'ai_engine.ChatAudioAttachment': ('session__company', 'session_id__in'),
    'word_ai.WordEditJobEvent': ('job__company', 'job_id__in'),
}


# def get_model_class lấy class model Django từ nhãn dạng 'app.Model'.
# vd: 'prompts.Prompt' -> class Prompt.
def get_model_class(label: str):
    from django.apps import apps
    app_label, model_name = label.split('.')
    return apps.get_model(app_label, model_name)


# def filter_queryset_for_company trả queryset của 1 model đã lọc đúng phạm vi 1 công ty: model có FK company trực tiếp -> filter(company=...); model con -> dùng mapping _CHILD_FILTERS (lookup lồng qua cha); vài model đặc biệt (AIUsageLog/Prompt/DepartmentDelegation) lọc gián tiếp qua user/department của công ty.
# vd: 'documents.DocumentVersion' -> lọc theo document__company = công ty.
def filter_queryset_for_company(model_label: str, company):
    """
    Tra ve queryset duoc filter dung company scope.
    Neu model co `company` FK truc tiep -> filter(company=company).
    Neu khong, dung mapping _CHILD_FILTERS de lookup nested.
    """
    model = get_model_class(model_label)
    if any(f.name == 'company' for f in model._meta.fields):
        return model._default_manager.filter(company=company)

    if model_label in _CHILD_FILTERS:
        nested_path, _ = _CHILD_FILTERS[model_label]
        return model._default_manager.filter(**{nested_path: company})

    if model_label == 'ai_engine.AIUsageLog':
        from accounts.models import CompanyUserMembership
        user_ids = CompanyUserMembership.objects.filter(company=company).values_list('user_id', flat=True)
        return model._default_manager.filter(user_id__in=list(user_ids))

    if model_label == 'prompts.Prompt':
        from accounts.models import CompanyUserMembership
        user_ids = CompanyUserMembership.objects.filter(company=company).values_list('user_id', flat=True)
        return model._default_manager.filter(owner_id__in=list(user_ids))

    if model_label == 'signing.DepartmentDelegation':
        from accounts.models import Department
        dept_ids = Department.objects.filter(company=company).values_list('id', flat=True)
        return model._default_manager.filter(department_id__in=list(dept_ids))

    return model._default_manager.none()


# def models_for_components trả danh sách (nhãn, class) các model thuộc các component được chọn, theo đúng thứ tự khai báo (con trước cha).
# vd: ['prompts'] -> [('prompts.PromptInjectionLog',...), ('prompts.Prompt',...)].
def models_for_components(components):
    """Tra ve danh sach (model_label, model_class) cho cac component duoc chon."""
    out = []
    for key in components:
        for label in COMPONENT_MODELS.get(key, []):
            out.append((label, get_model_class(label)))
    return out


# def delete_order trả thứ tự XÓA khi restore (replace): con trước cha để tránh vi phạm khóa ngoại (ProtectedError).
# vd: xóa TemplateVersion trước rồi mới xóa DocumentTemplate.
def delete_order(components):
    """Tra ve thu tu xoa: theo COMPONENT_MODELS (da sap xep child truoc parent)."""
    return models_for_components(components)


# def import_order trả thứ tự NHẬP khi restore: ngược với delete_order (cha trước con) để FK hợp lệ lúc tạo lại.
# vd: tạo DocumentTemplate trước rồi mới tạo TemplateVersion.
def import_order(components):
    """Thu tu import = nguoc lai delete_order (parent truoc child)."""
    return list(reversed(models_for_components(components)))

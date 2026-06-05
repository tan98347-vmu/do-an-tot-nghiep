from document_templates.models import DocumentTemplate, TemplateAudienceMember
from api.views.peer_audience_views import build_peer_views

_views = build_peer_views(
    model=DocumentTemplate,
    audience_model=TemplateAudienceMember,
    fk_name='template',
    entity_label='template',
)

audience = _views['audience']
list_audience = _views['list_audience']
update_audience = _views['update_audience']
submit = _views['submit']
approve = _views['approve']
reject = _views['reject']
pending = _views['pending']

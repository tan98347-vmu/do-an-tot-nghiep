from documents.models import Document, DocumentAudienceMember
from api.views.peer_audience_views import build_peer_views

_views = build_peer_views(
    model=Document,
    audience_model=DocumentAudienceMember,
    fk_name='document',
    entity_label='document',
)

audience = _views['audience']
list_audience = _views['list_audience']
update_audience = _views['update_audience']
submit = _views['submit']
approve = _views['approve']
reject = _views['reject']
pending = _views['pending']

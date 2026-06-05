"""Tests quy tac re-share: chi nguoi co quyen TOAN QUYEN (delete) moi duoc chia se tiep.

- Owner: chia se duoc (mac dinh).
- Nguoi nhan 'view' hoac 'edit': KHONG duoc tao grant moi (403).
- Nguoi nhan 'delete' (toan quyen): duoc tao grant moi (re-share) (201).
"""

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from prompts.models import Prompt
from sharing.constants import APPROVAL_ACTIVE, SCOPE_COLLEAGUES
from sharing.models import ShareGrant


class ResharePermissionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='rs_owner', password='x')
        self.viewer = User.objects.create_user(username='rs_viewer', password='x')
        self.editor = User.objects.create_user(username='rs_editor', password='x')
        self.full = User.objects.create_user(username='rs_full', password='x')
        self.target = User.objects.create_user(username='rs_target', password='x')
        self.prompt = Prompt.objects.create(owner=self.owner, title='P chia se')
        self.ct = ContentType.objects.get_for_model(Prompt)

    def _grant(self, user, level):
        return ShareGrant.objects.create(
            content_type=self.ct,
            object_id=self.prompt.id,
            scope=SCOPE_COLLEAGUES,
            permission_level=level,
            target_user=user,
            approval_status=APPROVAL_ACTIVE,
            created_by=self.owner,
        )

    def _try_reshare(self, actor):
        self.client.force_login(actor)
        return self.client.post(
            reverse('api:shares_list_create', args=['prompts', self.prompt.id]),
            data={
                'scope': SCOPE_COLLEAGUES,
                'permission_level': 'view',
                'target_user': self.target.id,
                'auto_submit': True,
            },
            content_type='application/json',
        )

    def test_owner_can_share(self):
        resp = self._try_reshare(self.owner)
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_viewer_cannot_reshare(self):
        self._grant(self.viewer, 'view')
        resp = self._try_reshare(self.viewer)
        self.assertEqual(resp.status_code, 403)

    def test_editor_cannot_reshare(self):
        self._grant(self.editor, 'edit')
        resp = self._try_reshare(self.editor)
        self.assertEqual(resp.status_code, 403)

    def test_full_permission_can_reshare(self):
        self._grant(self.full, 'delete')
        resp = self._try_reshare(self.full)
        self.assertEqual(resp.status_code, 201, resp.content)

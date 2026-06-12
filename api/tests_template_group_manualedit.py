"""Regression: template da chia se nhom (ShareGrant) van PATCH/mo manual edit duoc.

Tai hien bug cu: ShareGrant set visibility='group' nhung FK `group`=None, khien
TemplateWriteSerializer.validate van bat buoc FK group -> chan luu/mo trinh sua thu cong.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserGroup, UserGroupMembership
from document_templates.models import DocumentTemplate
from sharing import services


class TemplateGroupShareManualEditTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='tg_owner', password='x')
        self.leader = User.objects.create_user(username='tg_leader', password='x')
        self.group = UserGroup.objects.create(name='G-PM')
        UserGroupMembership.objects.create(group=self.group, user=self.owner, role=UserGroupMembership.ROLE_MEMBER)
        UserGroupMembership.objects.create(group=self.group, user=self.leader, role=UserGroupMembership.ROLE_LEADER)
        self.tmpl = DocumentTemplate.objects.create(
            owner=self.owner, title='T1', content='Noi dung {{x}} ABCDEF',
            source_type=DocumentTemplate.SOURCE_MANUAL,
            visibility=DocumentTemplate.VISIBILITY_PRIVATE,
        )

    def _share_to_group(self):
        services.create_grant(
            resource=self.tmpl, scope='group', permission_level='edit',
            target_group=self.group, actor=self.owner,
        )
        self.tmpl.refresh_from_db()

    def test_visibility_becomes_group_but_group_fk_none(self):
        self._share_to_group()
        self.assertEqual(self.tmpl.visibility, DocumentTemplate.VISIBILITY_GROUP)
        self.assertIsNone(self.tmpl.group_id)  # ShareGrant khong set FK legacy

    def test_owner_can_patch_group_shared_template(self):
        """Truoc fix: PATCH tra 400 {'group': [...]}. Sau fix: 200."""
        self._share_to_group()
        self.client.force_login(self.owner)
        resp = self.client.patch(
            reverse('api:template_detail', args=[self.tmpl.id]),
            data={'title': 'T1 edited'},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_owner_can_open_manual_edit_on_group_shared_template(self):
        """Mo trinh sua thu cong (save-then-open): PATCH + session create deu OK."""
        self._share_to_group()
        self.client.force_login(self.owner)
        # buoc save-truoc-khi-mo cua form
        patch = self.client.patch(
            reverse('api:template_detail', args=[self.tmpl.id]),
            data={'title': 'T1', 'content': 'Noi dung moi {{x}} ABCDEF', 'visibility': 'group'},
            content_type='application/json',
        )
        self.assertEqual(patch.status_code, 200, patch.content)
        # buoc mo session manual edit: khong con bi chan boi loi 'group'.
        # (Moi truong test khong cau hinh Collabora nen co the dung o buoc provider,
        #  nhung dieu quan trong la KHONG con loi validate 'group'.)
        sess = self.client.post(
            reverse('api:template_manual_edit_session_create', args=[self.tmpl.id]),
            data={}, content_type='application/json',
        )
        body = sess.content.decode('utf-8', 'ignore')
        self.assertNotIn('chọn nhóm/phòng ban', body)
        self.assertIn(sess.status_code, (200, 201, 400), sess.content)
        if sess.status_code == 400:
            # chi chap nhan loi do provider chua cau hinh, khong phai loi 'group'
            self.assertIn('COLLABORA', body.upper())

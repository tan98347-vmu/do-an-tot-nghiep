"""Tai lieu chia se cho NHOM qua ShareGrant phai hien o tab 'Da chia se trong nhom'
(group='group') du KHONG set legacy Document.group FK."""

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import (
    Company,
    CompanyStatus,
    CompanyUserMembership,
    UserGroup,
    UserGroupMembership,
)
from documents.models import Document
from sharing.constants import APPROVAL_ACTIVE, SCOPE_GROUP
from sharing.models import ShareGrant


class GroupShareListingTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            code='grpshare', name='Group Share Co', status=CompanyStatus.ACTIVE,
        )
        self.owner = User.objects.create_user(username='gs_owner', password='x')
        self.member = User.objects.create_user(username='gs_member', password='x')
        for u in (self.owner, self.member):
            CompanyUserMembership.objects.create(
                company=self.company, user=u, local_username=u.username, is_active=True,
            )
        self.group = UserGroup.objects.create(company=self.company, name='Phong A')
        UserGroupMembership.objects.create(group=self.group, user=self.owner)
        UserGroupMembership.objects.create(group=self.group, user=self.member)

        # Tai lieu rieng tu, KHONG set Document.group FK; chia se cho nhom qua ShareGrant.
        self.doc = Document.objects.create(
            company=self.company, owner=self.owner, title='Tai lieu nhom',
            visibility='private',
        )
        ShareGrant.objects.create(
            content_type=ContentType.objects.get_for_model(Document),
            object_id=self.doc.id,
            scope=SCOPE_GROUP,
            target_group=self.group,
            permission_level='view',
            approval_status=APPROVAL_ACTIVE,
            created_by=self.owner,
        )

    def _ids(self, user):
        client = APIClient()
        client.force_authenticate(user)
        resp = client.get(reverse('api:document_list') + '?group=group')
        self.assertEqual(resp.status_code, 200, resp.content)
        return {item['id'] for item in resp.json()}

    def test_group_shared_doc_appears_in_group_tab_for_member(self):
        self.assertIn(self.doc.id, self._ids(self.member))

    def test_group_shared_doc_appears_in_group_tab_for_owner(self):
        self.assertIn(self.doc.id, self._ids(self.owner))

    def test_non_member_does_not_see_group_doc(self):
        outsider = User.objects.create_user(username='gs_outsider', password='x')
        CompanyUserMembership.objects.create(
            company=self.company, user=outsider, local_username='gs_outsider', is_active=True,
        )
        self.assertNotIn(self.doc.id, self._ids(outsider))

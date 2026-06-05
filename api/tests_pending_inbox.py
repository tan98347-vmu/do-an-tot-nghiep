"""Man 'Chia se cho duyet' (shares/pending/): sap xep theo thoi gian + loc + tim kiem."""

import time

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
from prompts.models import Prompt
from sharing.constants import APPROVAL_PENDING_LEADER, SCOPE_GROUP
from sharing.models import ShareGrant


class PendingInboxTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            code='pinbox', name='Pending Inbox Co', status=CompanyStatus.ACTIVE,
        )
        self.leader = User.objects.create_user(username='pi_leader', password='x')
        self.owner = User.objects.create_user(username='pi_owner', password='x')
        for u in (self.leader, self.owner):
            CompanyUserMembership.objects.create(
                company=self.company, user=u, local_username=u.username, is_active=True,
            )
        self.group = UserGroup.objects.create(company=self.company, name='Phong A')
        UserGroupMembership.objects.create(
            group=self.group, user=self.leader, role=UserGroupMembership.ROLE_LEADER)
        UserGroupMembership.objects.create(
            group=self.group, user=self.owner, role=UserGroupMembership.ROLE_MEMBER)

        # 2 grant pending_leader (doc cu + prompt moi) -> leader duyet
        self.doc = Document.objects.create(
            company=self.company, owner=self.owner, title='Alpha doc', visibility='private')
        self._grant(self.doc, Document)
        time.sleep(0.01)
        self.prompt = Prompt.objects.create(owner=self.owner, title='Beta prompt')
        self._grant(self.prompt, Prompt)

        self.client = APIClient()
        self.client.force_authenticate(self.leader)

    def _grant(self, resource, model):
        return ShareGrant.objects.create(
            content_type=ContentType.objects.get_for_model(model),
            object_id=resource.id,
            scope=SCOPE_GROUP,
            target_group=self.group,
            permission_level='view',
            approval_status=APPROVAL_PENDING_LEADER,
            created_by=self.owner,
        )

    def _get(self, **params):
        resp = self.client.get(reverse('api:shares_pending_inbox'), params)
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json()['pending']

    def test_sorted_newest_first_by_default(self):
        items = self._get()
        self.assertEqual(len(items), 2)
        # prompt tao sau -> newest first
        self.assertEqual(items[0]['entity_title'], 'Beta prompt')
        self.assertEqual(items[1]['entity_title'], 'Alpha doc')
        # co truong thoi gian + chu so huu
        self.assertTrue(items[0]['submitted_at'])
        self.assertEqual(items[0]['owner_name'], 'pi_owner')

    def test_sorted_oldest_first(self):
        items = self._get(sort='oldest')
        self.assertEqual(items[0]['entity_title'], 'Alpha doc')

    def test_filter_by_entity_type(self):
        items = self._get(entity_type='prompts')
        self.assertEqual([i['entity_title'] for i in items], ['Beta prompt'])

    def test_search_by_title(self):
        items = self._get(q='alpha')
        self.assertEqual([i['entity_title'] for i in items], ['Alpha doc'])

    def test_filter_by_scope(self):
        self.assertEqual(len(self._get(scope='group')), 2)
        self.assertEqual(len(self._get(scope='everyone')), 0)

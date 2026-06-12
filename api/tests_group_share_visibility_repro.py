"""Repro: truong nhom chia se template cho nhom minh -> thanh vien KHONG thay.

Tai hien dung qua endpoint that:
  - leader POST templates/<id>/shares/ (scope=group) -> grant active (leader auto-active)
  - member GET templates/?group=team -> KY VONG thay template, THUC TE khong thay.
"""

from django.contrib.auth.models import User
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
from document_templates.models import (
    STATUS_APPROVED,
    STATUS_PENDING_LEADER,
    DocumentTemplate,
)
from sharing import services
from sharing.constants import APPROVAL_ACTIVE, SCOPE_GROUP


class GroupShareVisibilityReproTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            code='ktco', name='Cong ty KT', status=CompanyStatus.ACTIVE,
        )
        self.leader = User.objects.create_user(username='kt_leader', password='x')
        self.member = User.objects.create_user(username='kt_member', password='x')
        for u in (self.leader, self.member):
            CompanyUserMembership.objects.create(
                company=self.company, user=u, local_username=u.username, role='member',
            )
        self.group = UserGroup.objects.create(name='Phong ky thuat', company=self.company)
        UserGroupMembership.objects.create(
            group=self.group, user=self.leader, role=UserGroupMembership.ROLE_LEADER,
        )
        UserGroupMembership.objects.create(
            group=self.group, user=self.member, role=UserGroupMembership.ROLE_MEMBER,
        )
        # Leader so huu mot template
        self.tmpl = DocumentTemplate.objects.create(
            owner=self.leader, company=self.company, title='Mau KT',
            content='Noi dung {{x}}', source_type=DocumentTemplate.SOURCE_MANUAL,
            visibility=DocumentTemplate.VISIBILITY_GROUP,
            status=STATUS_PENDING_LEADER,  # dieu kien loi: chua approved
        )

    def test_leader_share_to_group_member_sees_in_team_tab(self):
        # Leader chia se cho nhom qua endpoint that (giong unified share sheet)
        client = APIClient()
        client.force_authenticate(self.leader)
        resp = client.post(
            reverse('api:shares_list_create', args=['templates', self.tmpl.id]),
            {'scope': 'group', 'permission_level': 'edit', 'target_group': self.group.id},
            format='json',
        )
        self.assertEqual(resp.status_code, 201, resp.content)

        self.tmpl.refresh_from_db()
        # Grant phai active (leader auto-active)
        from sharing.models import ShareGrant
        grant = ShareGrant.objects.for_resource(self.tmpl).first()
        self.assertIsNotNone(grant)
        self.assertEqual(grant.approval_status, APPROVAL_ACTIVE)
        self.assertEqual(grant.scope, SCOPE_GROUP)

        print('\n[REPRO] visibility =', self.tmpl.visibility, '| status =', self.tmpl.status)
        # Sau fix: status phai duoc PROMOTE len approved khi grant nhom active
        self.assertEqual(self.tmpl.status, STATUS_APPROVED)

        # Member co quyen xem theo sharing layer?
        self.assertTrue(
            services.can_view(self.member, self.tmpl),
            'Member phai co quyen xem theo ShareGrant active',
        )

        # Member mo tab "team" (Mau phong ban)
        mclient = APIClient()
        mclient.force_authenticate(self.member)
        list_resp = mclient.get(
            reverse('api:template_list'), {'group': 'team'},
        )
        self.assertEqual(list_resp.status_code, 200, list_resp.content)
        ids = [row['id'] for row in list_resp.data]
        print('[REPRO] team-tab ids member thay =', ids)
        self.assertIn(
            self.tmpl.id, ids,
            'BUG: member khong thay template da chia se nhom trong tab team',
        )

    def test_owner_share_then_leader_approves_grant_promotes_status(self):
        """Owner (khong phai leader) chia se -> pending_leader; leader duyet GRANT
        qua ShareGrant -> active -> status promote -> member thay."""
        owner = User.objects.create_user(username='kt_owner', password='x')
        CompanyUserMembership.objects.create(
            company=self.company, user=owner, local_username=owner.username, role='member',
        )
        UserGroupMembership.objects.create(
            group=self.group, user=owner, role=UserGroupMembership.ROLE_MEMBER,
        )
        tmpl = DocumentTemplate.objects.create(
            owner=owner, company=self.company, title='Mau KT2',
            content='abc {{y}}', source_type=DocumentTemplate.SOURCE_MANUAL,
            visibility=DocumentTemplate.VISIBILITY_PRIVATE, status=STATUS_APPROVED,
        )
        grant = services.create_grant(
            resource=tmpl, scope='group', permission_level='view',
            target_group=self.group, actor=owner,
        )
        self.assertNotEqual(grant.approval_status, APPROVAL_ACTIVE)  # cho leader duyet
        # Member chua thay (grant chua active)
        self.assertFalse(services.can_view(self.member, tmpl))
        # Leader duyet grant
        services.approve_grant(grant, approver=self.leader)
        tmpl.refresh_from_db()
        self.assertEqual(tmpl.status, STATUS_APPROVED)
        self.assertTrue(services.can_view(self.member, tmpl))

    def test_member_normal_edit_does_not_reset_group_approval(self):
        """Sua THUONG (PATCH) boi thanh vien khong duoc reset status ve pending_leader."""
        services.create_grant(
            resource=self.tmpl, scope='group', permission_level='delete',
            target_group=self.group, actor=self.leader,
        )
        self.tmpl.refresh_from_db()
        self.assertEqual(self.tmpl.status, STATUS_APPROVED)

        mclient = APIClient()
        mclient.force_authenticate(self.member)
        resp = mclient.patch(
            reverse('api:template_detail', args=[self.tmpl.id]),
            {'content': 'Noi dung thanh vien sua thuong {{x}}'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.tmpl.refresh_from_db()
        self.assertEqual(
            self.tmpl.status, STATUS_APPROVED,
            'BUG: sua thuong khien mau bi reset ve cho-truong-nhom-duyet',
        )
        self.assertTrue(services.can_view(self.member, self.tmpl))

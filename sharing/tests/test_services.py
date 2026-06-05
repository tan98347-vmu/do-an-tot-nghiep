"""
Unit test cho sharing.services.

Bao phu:
  - Owner luon co full quyen (bo qua grants).
  - Superuser luon co full quyen.
  - Ladder permission: view < edit < delete.
  - Multi-scope OR: user duoc max permission tu nhieu grant.
  - Grant chua duoc duyet (pending/rejected/draft) khong cho quyen.
  - Scope private khong cap quyen cho user khac.
  - Scope group cap quyen cho thanh vien nhom.
  - Scope everyone cap quyen cho tat ca.
  - Approval workflow: submit -> approve / reject -> active / rejected.
"""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from accounts.models import (
    Company,
    CompanyRole,
    CompanyStatus,
    CompanyUserMembership,
    UserGroup,
    UserGroupMembership,
)
from prompts.models import Prompt

from sharing import services
from sharing.constants import (
    APPROVAL_ACTIVE,
    APPROVAL_DRAFT,
    APPROVAL_PENDING_ADMIN,
    APPROVAL_PENDING_LEADER,
    APPROVAL_REJECTED,
    PERMISSION_DELETE,
    PERMISSION_EDIT,
    PERMISSION_VIEW,
    SCOPE_COLLEAGUES,
    SCOPE_EVERYONE,
    SCOPE_GROUP,
    SCOPE_PRIVATE,
)
from sharing.models import ShareGrant


User = get_user_model()


class SharingServicesTestCase(TestCase):
    """
    Goi y test scenario co ban (yeu cau co PROMPT model va UserGroup san co).

    Vi codebase phu thuoc multi-app va du lieu seed, test nay dung Prompt vi tinh model don gian nhat,
    khong co side-effect tu DocumentVersion/signing_packets nhu Document.
    """

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username='owner', password='x')
        cls.member = User.objects.create_user(username='member', password='x')
        cls.outsider = User.objects.create_user(username='outsider', password='x')
        cls.leader = User.objects.create_user(username='leader', password='x')
        cls.company_admin = User.objects.create_user(username='company_admin', password='x')
        cls.admin = User.objects.create_superuser(username='admin', password='x')
        cls.other_owner = User.objects.create_user(username='other_owner', password='x')
        cls.other_member = User.objects.create_user(username='other_member', password='x')

        cls.company = Company.objects.create(
            code='company-a',
            name='Company A',
            status=CompanyStatus.ACTIVE,
        )
        cls.other_company = Company.objects.create(
            code='company-b',
            name='Company B',
            status=CompanyStatus.ACTIVE,
        )
        CompanyUserMembership.objects.create(
            company=cls.company,
            user=cls.owner,
            local_username='owner',
            role=CompanyRole.COMPANY_USER,
        )
        CompanyUserMembership.objects.create(
            company=cls.company,
            user=cls.member,
            local_username='member',
            role=CompanyRole.COMPANY_USER,
        )
        CompanyUserMembership.objects.create(
            company=cls.company,
            user=cls.outsider,
            local_username='outsider',
            role=CompanyRole.COMPANY_USER,
        )
        CompanyUserMembership.objects.create(
            company=cls.company,
            user=cls.leader,
            local_username='leader',
            role=CompanyRole.COMPANY_USER,
        )
        CompanyUserMembership.objects.create(
            company=cls.company,
            user=cls.company_admin,
            local_username='company_admin',
            role=CompanyRole.COMPANY_ADMIN,
        )
        CompanyUserMembership.objects.create(
            company=cls.other_company,
            user=cls.other_owner,
            local_username='other_owner',
            role=CompanyRole.COMPANY_USER,
        )
        CompanyUserMembership.objects.create(
            company=cls.other_company,
            user=cls.other_member,
            local_username='other_member',
            role=CompanyRole.COMPANY_USER,
        )

        cls.group = UserGroup.objects.create(name='NhomTest', company=cls.company)
        UserGroupMembership.objects.create(group=cls.group, user=cls.owner, role='member')
        UserGroupMembership.objects.create(group=cls.group, user=cls.member, role='member')
        UserGroupMembership.objects.create(group=cls.group, user=cls.leader, role='leader')

        cls.prompt = Prompt.objects.create(
            title='Prompt test',
            system_content='hello',
            owner=cls.owner,
            visibility='private',
            status='approved',
        )
        cls.other_prompt = Prompt.objects.create(
            title='Prompt company khac',
            system_content='hello',
            owner=cls.other_owner,
            visibility='private',
            status='approved',
        )

    # ----- Owner & admin bypass -----

    def test_owner_has_full_permission_without_grant(self):
        self.assertTrue(services.can(self.owner, self.prompt, PERMISSION_DELETE))
        self.assertTrue(services.can(self.owner, self.prompt, PERMISSION_EDIT))
        self.assertTrue(services.can(self.owner, self.prompt, PERMISSION_VIEW))
        self.assertEqual(services.user_permission_for(self.owner, self.prompt), PERMISSION_DELETE)

    def test_admin_has_full_permission_without_grant(self):
        self.assertTrue(services.can(self.admin, self.prompt, PERMISSION_DELETE))

    def test_outsider_has_no_permission_when_private(self):
        self.assertIsNone(services.user_permission_for(self.outsider, self.prompt))
        self.assertFalse(services.can(self.outsider, self.prompt, PERMISSION_VIEW))

    # ----- Scope group -----

    def test_group_member_gets_view_when_group_grant_active(self):
        ct = ContentType.objects.get_for_model(Prompt)
        ShareGrant.objects.create(
            content_type=ct,
            object_id=self.prompt.pk,
            scope=SCOPE_GROUP,
            target_group=self.group,
            permission_level=PERMISSION_VIEW,
            approval_status=APPROVAL_ACTIVE,
            created_by=self.owner,
        )
        self.assertTrue(services.can(self.member, self.prompt, PERMISSION_VIEW))
        self.assertFalse(services.can(self.member, self.prompt, PERMISSION_EDIT))
        self.assertFalse(services.can(self.outsider, self.prompt, PERMISSION_VIEW))

    def test_pending_grant_does_not_grant_permission(self):
        ct = ContentType.objects.get_for_model(Prompt)
        ShareGrant.objects.create(
            content_type=ct,
            object_id=self.prompt.pk,
            scope=SCOPE_GROUP,
            target_group=self.group,
            permission_level=PERMISSION_VIEW,
            approval_status=APPROVAL_PENDING_LEADER,
            created_by=self.owner,
        )
        self.assertFalse(services.can(self.member, self.prompt, PERMISSION_VIEW))
        self.prompt.refresh_from_db()
        self.assertEqual(self.prompt.visibility, 'group')

    # ----- Scope colleagues -----

    def test_colleague_specific_grant(self):
        ct = ContentType.objects.get_for_model(Prompt)
        ShareGrant.objects.create(
            content_type=ct,
            object_id=self.prompt.pk,
            scope=SCOPE_COLLEAGUES,
            target_user=self.outsider,
            permission_level=PERMISSION_EDIT,
            approval_status=APPROVAL_ACTIVE,
            created_by=self.owner,
        )
        self.assertTrue(services.can(self.outsider, self.prompt, PERMISSION_EDIT))
        self.assertTrue(services.can(self.outsider, self.prompt, PERMISSION_VIEW))
        self.assertFalse(services.can(self.outsider, self.prompt, PERMISSION_DELETE))

    # ----- Multi-scope OR -----

    def test_max_permission_across_multiple_grants(self):
        ct = ContentType.objects.get_for_model(Prompt)
        # Group view + colleague edit -> ket qua nen la edit
        ShareGrant.objects.create(
            content_type=ct, object_id=self.prompt.pk,
            scope=SCOPE_GROUP, target_group=self.group,
            permission_level=PERMISSION_VIEW, approval_status=APPROVAL_ACTIVE,
            created_by=self.owner,
        )
        ShareGrant.objects.create(
            content_type=ct, object_id=self.prompt.pk,
            scope=SCOPE_COLLEAGUES, target_user=self.member,
            permission_level=PERMISSION_EDIT, approval_status=APPROVAL_ACTIVE,
            created_by=self.owner,
        )
        self.assertEqual(services.user_permission_for(self.member, self.prompt), PERMISSION_EDIT)

    def test_everyone_scope_grants_all_users(self):
        ct = ContentType.objects.get_for_model(Prompt)
        ShareGrant.objects.create(
            content_type=ct, object_id=self.prompt.pk,
            scope=SCOPE_EVERYONE,
            permission_level=PERMISSION_VIEW, approval_status=APPROVAL_ACTIVE,
            created_by=self.owner,
        )
        self.assertTrue(services.can(self.outsider, self.prompt, PERMISSION_VIEW))
        self.assertTrue(services.can(self.member, self.prompt, PERMISSION_VIEW))

    # ----- Approval workflow -----

    def test_create_grant_group_pending_then_approve_active(self):
        grant = services.create_grant(
            resource=self.prompt,
            scope=SCOPE_GROUP,
            permission_level=PERMISSION_VIEW,
            target_group=self.group,
            actor=self.owner,
        )
        # Owner KHONG la leader => phai pending_leader
        self.assertEqual(grant.approval_status, APPROVAL_PENDING_LEADER)
        self.assertFalse(services.can(self.member, self.prompt, PERMISSION_VIEW))
        self.prompt.refresh_from_db()
        self.assertEqual(self.prompt.visibility, 'group')

        services.approve_grant(grant, approver=self.leader, note='ok')
        grant.refresh_from_db()
        self.prompt.refresh_from_db()
        self.assertEqual(grant.approval_status, APPROVAL_ACTIVE)
        self.assertTrue(services.can(self.member, self.prompt, PERMISSION_VIEW))
        self.assertEqual(self.prompt.visibility, 'group')

    def test_owner_is_leader_of_group_auto_active(self):
        # Cho owner role leader
        UserGroupMembership.objects.filter(user=self.owner, group=self.group).update(role='leader')
        grant = services.create_grant(
            resource=self.prompt,
            scope=SCOPE_GROUP,
            permission_level=PERMISSION_VIEW,
            target_group=self.group,
            actor=self.owner,
        )
        self.assertEqual(grant.approval_status, APPROVAL_ACTIVE)

    def test_reject_does_not_grant_permission(self):
        grant = services.create_grant(
            resource=self.prompt,
            scope=SCOPE_COLLEAGUES,
            permission_level=PERMISSION_VIEW,
            target_user=self.outsider,
            actor=self.owner,
        )
        # outsider khong chung nhom voi owner -> theo nghiep vu phai do ADMIN duyet/tu choi.
        services.reject_grant(grant, approver=self.admin, note='no')
        grant.refresh_from_db()
        self.prompt.refresh_from_db()
        self.assertEqual(grant.approval_status, APPROVAL_REJECTED)
        self.assertFalse(services.can(self.outsider, self.prompt, PERMISSION_VIEW))

    def test_pending_everyone_grant_updates_visibility_cache_to_public(self):
        grant = services.create_grant(
            resource=self.prompt,
            scope=SCOPE_EVERYONE,
            permission_level=PERMISSION_VIEW,
            actor=self.owner,
        )
        self.prompt.refresh_from_db()

        self.assertEqual(grant.approval_status, APPROVAL_PENDING_ADMIN)
        self.assertEqual(self.prompt.visibility, 'public')

    def test_submit_draft_group_grant_updates_visibility_cache(self):
        grant = services.create_grant(
            resource=self.prompt,
            scope=SCOPE_GROUP,
            permission_level=PERMISSION_VIEW,
            target_group=self.group,
            actor=self.owner,
            auto_submit=False,
        )
        self.prompt.refresh_from_db()
        self.assertEqual(grant.approval_status, APPROVAL_DRAFT)
        self.assertEqual(self.prompt.visibility, 'private')

        services.submit_grant(grant, actor=self.owner)
        grant.refresh_from_db()
        self.prompt.refresh_from_db()

        self.assertEqual(grant.approval_status, APPROVAL_PENDING_LEADER)
        self.assertEqual(self.prompt.visibility, 'group')

    def test_reject_everyone_grant_resets_visibility_cache_to_private(self):
        grant = services.create_grant(
            resource=self.prompt,
            scope=SCOPE_EVERYONE,
            permission_level=PERMISSION_VIEW,
            actor=self.owner,
        )
        self.prompt.refresh_from_db()
        self.assertEqual(self.prompt.visibility, 'public')

        services.reject_grant(grant, approver=self.admin, note='no')
        grant.refresh_from_db()
        self.prompt.refresh_from_db()

        self.assertEqual(grant.approval_status, APPROVAL_REJECTED)
        self.assertEqual(self.prompt.visibility, 'private')

    def test_company_admin_can_approve_everyone_grant(self):
        grant = services.create_grant(
            resource=self.prompt,
            scope=SCOPE_EVERYONE,
            permission_level=PERMISSION_VIEW,
            actor=self.owner,
        )
        self.assertEqual(grant.approval_status, APPROVAL_PENDING_ADMIN)

        services.approve_grant(grant, approver=self.company_admin, note='ok')
        grant.refresh_from_db()

        self.assertEqual(grant.approval_status, APPROVAL_ACTIVE)
        self.assertTrue(services.can(self.member, self.prompt, PERMISSION_VIEW))

    def test_company_admin_owner_everyone_grant_auto_active(self):
        prompt = Prompt.objects.create(
            title='Prompt admin cong ty',
            system_content='hello',
            owner=self.company_admin,
            visibility='private',
            status='approved',
        )

        grant = services.create_grant(
            resource=prompt,
            scope=SCOPE_EVERYONE,
            permission_level=PERMISSION_VIEW,
            actor=self.company_admin,
        )

        self.assertEqual(grant.approval_status, APPROVAL_ACTIVE)
        self.assertTrue(services.can(self.member, prompt, PERMISSION_VIEW))

    def test_non_leader_cannot_approve(self):
        grant = services.create_grant(
            resource=self.prompt,
            scope=SCOPE_GROUP,
            permission_level=PERMISSION_VIEW,
            target_group=self.group,
            actor=self.owner,
        )
        with self.assertRaises(PermissionError):
            services.approve_grant(grant, approver=self.outsider)

    # ----- Queryset filters -----

    def test_get_accessible_qs_includes_owner_and_shared(self):
        ct = ContentType.objects.get_for_model(Prompt)
        ShareGrant.objects.create(
            content_type=ct, object_id=self.prompt.pk,
            scope=SCOPE_COLLEAGUES, target_user=self.outsider,
            permission_level=PERMISSION_VIEW, approval_status=APPROVAL_ACTIVE,
            created_by=self.owner,
        )
        # owner sees it (qua owner_field)
        self.assertIn(self.prompt, list(services.get_accessible_qs(self.owner, Prompt)))
        # outsider sees it (qua colleagues grant)
        self.assertIn(self.prompt, list(services.get_accessible_qs(self.outsider, Prompt)))
        # member khong thay (khong co grant cho member)
        self.assertNotIn(self.prompt, list(services.get_accessible_qs(self.member, Prompt)))

    def test_prompt_everyone_grant_does_not_leak_cross_company(self):
        ct = ContentType.objects.get_for_model(Prompt)
        ShareGrant.objects.create(
            content_type=ct,
            object_id=self.other_prompt.pk,
            scope=SCOPE_EVERYONE,
            permission_level=PERMISSION_VIEW,
            approval_status=APPROVAL_ACTIVE,
            created_by=self.other_owner,
        )

        self.assertNotIn(
            self.other_prompt,
            list(services.get_accessible_qs(self.member, Prompt)),
        )
        self.assertIn(
            self.other_prompt,
            list(services.get_accessible_qs(self.other_member, Prompt)),
        )

    def test_company_admin_reviewable_qs_scopes_pending_admin_to_same_company(self):
        services.create_grant(
            resource=self.other_prompt,
            scope=SCOPE_EVERYONE,
            permission_level=PERMISSION_VIEW,
            actor=self.other_owner,
        )

        reviewable = list(services.get_reviewable_qs(self.company_admin, Prompt))
        self.assertNotIn(self.other_prompt, reviewable)

    def test_revoke_removes_permission(self):
        grant = services.create_grant(
            resource=self.prompt,
            scope=SCOPE_COLLEAGUES,
            permission_level=PERMISSION_EDIT,
            target_user=self.outsider,
            actor=self.owner,
        )
        # outsider khong chung nhom voi owner -> theo nghiep vu phai do ADMIN duyet.
        services.approve_grant(grant, approver=self.admin)
        self.assertTrue(services.can(self.outsider, self.prompt, PERMISSION_EDIT))

        services.revoke_grant(grant, actor=self.owner)
        self.assertFalse(services.can(self.outsider, self.prompt, PERMISSION_EDIT))

"""Kiem tra nghiep vu phan quyen chia se (4 vung) theo dac ta.

- colleagues CHUNG NHOM owner -> cho TRUONG NHOM CHUNG duyet.
- colleagues KHAC NHOM owner -> cho ADMIN duyet.
- group -> cho truong nhom duyet; chi chia se toi nhom NGUOI CHIA SE LA THANH VIEN.
- everyone -> cho admin duyet.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserGroup, UserGroupMembership
from prompts.models import Prompt
from sharing import services
from sharing.constants import (
    APPROVAL_PENDING_ADMIN,
    APPROVAL_PENDING_LEADER,
    SCOPE_COLLEAGUES,
    SCOPE_EVERYONE,
    SCOPE_GROUP,
)


class SharingBusinessRulesTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='sb_owner', password='x')
        self.leader = User.objects.create_user(username='sb_leader', password='x')
        self.peer_common = User.objects.create_user(username='sb_peer_common', password='x')
        self.peer_nogroup = User.objects.create_user(username='sb_peer_nogroup', password='x')
        self.admin = User.objects.create_superuser(username='sb_admin', password='x', email='a@a.com')

        # Nhom chung G: owner + leader(leader) + peer_common deu la thanh vien
        self.group = UserGroup.objects.create(name='Group G')
        UserGroupMembership.objects.create(group=self.group, user=self.owner, role=UserGroupMembership.ROLE_MEMBER)
        UserGroupMembership.objects.create(group=self.group, user=self.leader, role=UserGroupMembership.ROLE_LEADER)
        UserGroupMembership.objects.create(group=self.group, user=self.peer_common, role=UserGroupMembership.ROLE_MEMBER)

        # Nhom X: owner KHONG phai thanh vien
        self.group_x = UserGroup.objects.create(name='Group X')
        UserGroupMembership.objects.create(group=self.group_x, user=self.peer_nogroup, role=UserGroupMembership.ROLE_MEMBER)

        self.prompt = Prompt.objects.create(owner=self.owner, title='P')

    # --- Colleagues ---
    def test_colleagues_common_group_pending_leader(self):
        grant = services.create_grant(
            resource=self.prompt, scope=SCOPE_COLLEAGUES, permission_level='view',
            target_user=self.peer_common, actor=self.owner,
        )
        self.assertEqual(grant.approval_status, APPROVAL_PENDING_LEADER)
        self.assertTrue(services.can_approve_grant(self.leader, grant))      # truong nhom chung
        self.assertFalse(services.can_approve_grant(self.peer_common, grant))  # khong phai leader
        self.assertTrue(services.can_approve_grant(self.admin, grant))       # admin luon duyet duoc

    def test_colleagues_no_common_group_pending_admin(self):
        grant = services.create_grant(
            resource=self.prompt, scope=SCOPE_COLLEAGUES, permission_level='edit',
            target_user=self.peer_nogroup, actor=self.owner,
        )
        self.assertEqual(grant.approval_status, APPROVAL_PENDING_ADMIN)
        self.assertTrue(services.can_approve_grant(self.admin, grant))       # khac nhom -> admin duyet
        self.assertFalse(services.can_approve_grant(self.leader, grant))     # leader khong duyet (khong chung nhom)

    # --- Group ---
    def test_group_share_to_member_group_pending_leader(self):
        grant = services.create_grant(
            resource=self.prompt, scope=SCOPE_GROUP, permission_level='view',
            target_group=self.group, actor=self.owner,
        )
        self.assertEqual(grant.approval_status, APPROVAL_PENDING_LEADER)
        self.assertTrue(services.can_approve_grant(self.leader, grant))

    def test_group_share_to_non_member_group_blocked(self):
        with self.assertRaises(ValueError):
            services.create_grant(
                resource=self.prompt, scope=SCOPE_GROUP, permission_level='view',
                target_group=self.group_x, actor=self.owner,
            )

    # --- Everyone ---
    def test_everyone_pending_admin(self):
        grant = services.create_grant(
            resource=self.prompt, scope=SCOPE_EVERYONE, permission_level='view',
            actor=self.owner,
        )
        self.assertEqual(grant.approval_status, APPROVAL_PENDING_ADMIN)
        self.assertTrue(services.can_approve_grant(self.admin, grant))
        self.assertFalse(services.can_approve_grant(self.leader, grant))

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Company, CompanyStatus, CompanyUserMembership
from accounts.permissions import can_delete_prompt, can_edit_prompt
from prompts.models import Prompt, PromptAudienceMember


class PromptPeerPermissionTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            code='peer-tests',
            name='Peer Tests Company',
            status=CompanyStatus.ACTIVE,
        )
        self.owner = User.objects.create_user(username='prompt-owner', password='secret')
        self.peer = User.objects.create_user(username='prompt-peer', password='secret')
        self.other = User.objects.create_user(username='prompt-other', password='secret')
        CompanyUserMembership.objects.create(
            company=self.company,
            user=self.owner,
            local_username='prompt-owner',
        )
        CompanyUserMembership.objects.create(
            company=self.company,
            user=self.peer,
            local_username='prompt-peer',
        )
        CompanyUserMembership.objects.create(
            company=self.company,
            user=self.other,
            local_username='prompt-other',
        )
        self.prompt = Prompt.objects.create(
            title='Peer Prompt',
            owner=self.owner,
            visibility=Prompt.VISIBILITY_PRIVATE,
            peer_share_status=Prompt.PEER_SHARE_ACTIVE,
        )
        self.owner_client = APIClient()
        self.owner_client.force_authenticate(self.owner)
        self.peer_client = APIClient()
        self.peer_client.force_authenticate(self.peer)

    def test_permission_levels_drive_edit_and_delete_helpers(self):
        PromptAudienceMember.objects.create(
            prompt=self.prompt,
            user=self.peer,
            added_by=self.owner,
            permission_level='view',
        )
        self.assertFalse(can_edit_prompt(self.peer, self.prompt))
        self.assertFalse(can_delete_prompt(self.peer, self.prompt))

        membership = self.prompt.audience_members.get(user=self.peer)
        membership.permission_level = 'edit'
        membership.save(update_fields=['permission_level'])
        self.assertTrue(can_edit_prompt(self.peer, self.prompt))
        self.assertFalse(can_delete_prompt(self.peer, self.prompt))

        membership.permission_level = 'delete'
        membership.save(update_fields=['permission_level'])
        self.assertTrue(can_edit_prompt(self.peer, self.prompt))
        self.assertTrue(can_delete_prompt(self.peer, self.prompt))

    def test_prompt_detail_returns_my_permission_for_peer(self):
        PromptAudienceMember.objects.create(
            prompt=self.prompt,
            user=self.peer,
            added_by=self.owner,
            permission_level='edit',
        )

        response = self.peer_client.get(reverse('api:prompt_detail', args=[self.prompt.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['my_permission'], 'edit')

    def test_prompt_audience_put_accepts_permission_payload(self):
        response = self.owner_client.put(
            reverse('api:prompt_audience', args=[self.prompt.id]),
            {
                'audiences': [
                    {'user_id': self.peer.id, 'permission_level': 'delete'},
                    {'user_id': self.owner.id, 'permission_level': 'delete'},
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            PromptAudienceMember.objects.get(prompt=self.prompt, user=self.peer).permission_level,
            'delete',
        )
        self.assertEqual(len(response.data['audiences']), 1)
        self.assertEqual(response.data['audiences'][0]['user_id'], self.peer.id)
        self.assertEqual(response.data['audiences'][0]['permission_level'], 'delete')

    def test_prompt_audience_rejects_invalid_permission_level(self):
        response = self.owner_client.put(
            reverse('api:prompt_audience', args=[self.prompt.id]),
            {
                'audiences': [
                    {'user_id': self.peer.id, 'permission_level': 'owner'},
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('detail', response.data)

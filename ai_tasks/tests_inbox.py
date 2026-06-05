from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from ai_tasks.models import AITaskProgress, STATUS_COMPLETED, STATUS_QUEUED, STATUS_RUNNING


class AITaskInboxApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='task-owner',
            email='owner@example.com',
            password='test-pass-123',
        )
        self.other_user = User.objects.create_user(
            username='task-other',
            email='other@example.com',
            password='test-pass-123',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _create_task(self, *, user, status, title='Task', result=None):
        return AITaskProgress.objects.create(
            user=user,
            task_type='voice_chat',
            status=status,
            title_summary=title,
            deeplink='/assistant/voice?conversation_id=42',
            result=result,
        )

    def test_inbox_requires_authentication(self):
        response = APIClient().get('/api/ai-tasks/inbox/')
        self.assertIn(response.status_code, {401, 403})

    def test_inbox_returns_only_current_user_tasks(self):
        running = self._create_task(user=self.user, status=STATUS_RUNNING, title='Mine running')
        completed = self._create_task(user=self.user, status=STATUS_COMPLETED, title='Mine done')
        self._create_task(user=self.other_user, status=STATUS_RUNNING, title='Other running')
        self._create_task(user=self.other_user, status=STATUS_COMPLETED, title='Other done')

        response = self.client.get('/api/ai-tasks/inbox/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['task_id'] for item in response.data['running']], [str(running.task_id)])
        self.assertEqual([item['task_id'] for item in response.data['recent_completed']], [str(completed.task_id)])

    def test_dismiss_marks_task_and_hides_it_from_recent_list(self):
        task = self._create_task(user=self.user, status=STATUS_COMPLETED, title='Dismiss me')

        dismiss_response = self.client.post(f'/api/ai-tasks/{task.task_id}/dismiss/')
        inbox_response = self.client.get('/api/ai-tasks/inbox/')

        task.refresh_from_db()
        self.assertEqual(dismiss_response.status_code, 204)
        self.assertTrue(task.is_dismissed)
        self.assertEqual(inbox_response.data['recent_completed'], [])

    def test_dismiss_other_users_task_returns_404(self):
        task = self._create_task(user=self.other_user, status=STATUS_COMPLETED)

        response = self.client.post(f'/api/ai-tasks/{task.task_id}/dismiss/')

        self.assertEqual(response.status_code, 404)

    def test_cancel_running_task_sets_cancel_requested(self):
        task = self._create_task(user=self.user, status=STATUS_QUEUED, title='Cancel me')

        response = self.client.post(f'/api/ai-tasks/{task.task_id}/cancel/')

        task.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(task.cancel_requested)

    def test_cancel_completed_task_returns_409(self):
        task = self._create_task(user=self.user, status=STATUS_COMPLETED)

        response = self.client.post(f'/api/ai-tasks/{task.task_id}/cancel/')

        self.assertEqual(response.status_code, 409)

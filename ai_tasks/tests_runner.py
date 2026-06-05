import time

from django.contrib.auth.models import User
from django.test import TransactionTestCase

from ai_tasks.models import AITaskProgress, STATUS_COMPLETED, STATUS_FAILED
from ai_tasks.services.runner import TASK_HANDLERS, complete_task, dispatch_task, register_handler, update_task_progress


class AITaskRunnerTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username='runner-user',
            email='runner@example.com',
            password='test-pass-123',
        )
        self._original_handlers = TASK_HANDLERS.copy()

    def tearDown(self):
        TASK_HANDLERS.clear()
        TASK_HANDLERS.update(self._original_handlers)
        super().tearDown()

    def _wait_for_task(self, task_id: str, timeout: float = 3.0) -> AITaskProgress:
        deadline = time.time() + timeout
        while time.time() < deadline:
            task = AITaskProgress.objects.get(task_id=task_id)
            if task.is_terminal:
                return task
            time.sleep(0.05)
        return AITaskProgress.objects.get(task_id=task_id)

    def test_dispatch_task_completes_with_registered_handler(self):
        def handler(task, payload):
            update_task_progress(str(task.task_id), percent=35, stage='Đang xử lý')
            complete_task(str(task.task_id), result={'ok': True, 'payload': payload})

        register_handler('runner_success', handler)

        task_id = dispatch_task(
            'runner_success',
            self.user,
            {'alpha': 1},
            deeplink='/assistant/voice?conversation_id=7',
            title='Voice background task',
        )
        task = self._wait_for_task(task_id)

        self.assertEqual(task.status, STATUS_COMPLETED)
        self.assertEqual(task.progress_percent, 100)
        self.assertEqual(task.title_summary, 'Voice background task')
        self.assertEqual(task.deeplink, '/assistant/voice?conversation_id=7')
        self.assertEqual(task.result['ok'], True)

    def test_dispatch_task_marks_failure_when_handler_crashes(self):
        def handler(task, payload):
            raise RuntimeError('boom')

        register_handler('runner_failure', handler)

        task_id = dispatch_task(
            'runner_failure',
            self.user,
            {},
            deeplink='/assistant/voice?conversation_id=9',
            title='Failing task',
        )
        task = self._wait_for_task(task_id)

        self.assertEqual(task.status, STATUS_FAILED)
        self.assertIn('boom', task.error_message)

    def test_dispatch_task_is_idempotent_for_client_request_id(self):
        def handler(task, payload):
            complete_task(str(task.task_id), result={'ok': True})

        register_handler('runner_idempotent', handler)

        first = dispatch_task(
            'runner_idempotent',
            self.user,
            {},
            deeplink='/assistant/voice?conversation_id=11',
            title='Idempotent task',
            client_request_id='req-123',
        )
        second = dispatch_task(
            'runner_idempotent',
            self.user,
            {'ignored': True},
            deeplink='/assistant/voice?conversation_id=12',
            title='Another title',
            client_request_id='req-123',
        )

        self.assertEqual(first, second)
        self._wait_for_task(first)

    def test_default_r3_task_kinds_are_registered(self):
        expected = {
            'voice_chat',
            'bulk_template_upload',
            'document_summary',
            'compliance_check',
            'word_ai_edit',
            'company_backup_export',
        }
        self.assertTrue(expected.issubset(set(TASK_HANDLERS)))

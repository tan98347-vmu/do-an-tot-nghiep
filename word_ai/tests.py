import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import GlobalAIConfig
from documents.models import Document, DocumentVersion
from word_ai.models import WordEditJob, WordWorker
from word_ai.services.job_claim_service import claim_next_job
from word_ai.services.commit_result_service import commit_job_result
from word_ai.services.mcp_agent_loop_service import advance_mcp_agent, _guard_agent_decision, _sanitize_agent_decision
from word_ai.services.planning_service import _extract_json_block, _sanitize_plan


def _fake_storage_save(storage, name, content, max_length=None):
    return name


class WordAiApiTests(TestCase):
    def setUp(self):
        test_root = Path(__file__).resolve().parents[1] / '.codex-tmp'
        test_root.mkdir(parents=True, exist_ok=True)
        self.media_dir = Path(tempfile.mkdtemp(prefix='word-ai-tests-', dir=test_root))
        self.addCleanup(lambda: shutil.rmtree(self.media_dir, ignore_errors=True))
        self.media_override = override_settings(MEDIA_ROOT=str(self.media_dir))
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.schedule_preview = patch(
            'word_ai.services.commit_result_service.schedule_document_preview_regeneration',
            return_value=True,
        )
        self.schedule_preview.start()
        self.addCleanup(self.schedule_preview.stop)
        self.client = APIClient()
        self.worker_client = APIClient()
        self.user = User.objects.create_user(username='word-ai-owner', password='secret')
        self.document = Document.objects.create(
            title='Word AI Document',
            owner=self.user,
            content='Original content',
        )
        self.client.force_authenticate(self.user)
        self.worker_token = 'test-word-ai-worker-token'
        self.worker_token_override = override_settings(WORD_AI_LOCAL_AGENT_TOKEN=self.worker_token)
        self.worker_token_override.enable()
        self.addCleanup(self.worker_token_override.disable)

    def test_create_job_snapshots_llm_config(self):
        response = self.client.post(
            reverse('api:word_ai_job_list_create'),
            {
                'document_id': self.document.id,
                'instruction': 'Rewrite the introduction and align the headings.',
                'track_changes': True,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        job = WordEditJob.objects.get(pk=response.data['id'])
        self.assertEqual(job.document_id, self.document.id)
        self.assertEqual(job.status, 'queued')
        self.assertTrue(job.llm_model_name)
        self.assertEqual(job.events.count(), 2)
        self.assertEqual(
            job.events.order_by('-id').first().message,
            'No active Word worker is connected. The job will stay queued until the local agent heartbeats.',
        )
        self.assertEqual(job.llm_model_name, GlobalAIConfig.get_config().ai_model)

    def test_create_job_skips_runtime_warning_when_worker_recently_heartbeated(self):
        WordWorker.objects.create(
            worker_key='direct-host.slot-1',
            slot_label='slot-1',
            status='idle',
            last_seen_at=timezone.now(),
        )
        response = self.client.post(
            reverse('api:word_ai_job_list_create'),
            {
                'document_id': self.document.id,
                'instruction': 'Rewrite the introduction and align the headings.',
                'track_changes': True,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        job = WordEditJob.objects.get(pk=response.data['id'])
        self.assertEqual(job.events.count(), 1)
        self.assertEqual(job.events.first().message, 'Word AI job created.')

    def test_create_job_defaults_to_direct_addin_mcp_runtime(self):
        response = self.client.post(
            reverse('api:word_ai_job_list_create'),
            {
                'document_id': self.document.id,
                'instruction': 'Rewrite the introduction and align the headings.',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        job = WordEditJob.objects.get(pk=response.data['id'])
        self.assertEqual(job.edit_mode, 'direct_addin_mcp')

    def test_create_job_rejects_legacy_direct_edit_when_cutover_is_enabled(self):
        response = self.client.post(
            reverse('api:word_ai_job_list_create'),
            {
                'document_id': self.document.id,
                'instruction': 'Rewrite the introduction.',
                'edit_mode': 'direct_edit',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('edit_mode', response.data)

    @override_settings(WORD_AI_ALLOW_LEGACY_DIRECT_EDIT=True)
    def test_create_job_still_rejects_legacy_direct_edit_even_when_flag_is_set(self):
        response = self.client.post(
            reverse('api:word_ai_job_list_create'),
            {
                'document_id': self.document.id,
                'instruction': 'Rewrite the introduction.',
                'edit_mode': 'direct_edit',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('edit_mode', response.data)

    def test_complete_job_creates_new_document_version(self):
        create_response = self.client.post(
            reverse('api:word_ai_job_list_create'),
            {
                'document_id': self.document.id,
                'instruction': 'Make the document more formal.',
            },
            format='json',
        )
        job = WordEditJob.objects.get(pk=create_response.data['id'])
        worker = WordWorker.objects.create(worker_key='direct-host.slot-1', slot_label='slot-1')

        output_file = SimpleUploadedFile(
            'result.docx',
            b'fake-docx-binary',
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        with patch('django.core.files.storage.filesystem.FileSystemStorage.save', new=_fake_storage_save):
            response = self.worker_client.post(
                reverse('api:word_ai_job_complete', args=[job.id]),
                {
                    'worker_key': worker.worker_key,
                    'summary': 'Updated the tone.',
                    'change_note': 'Word AI revision',
                    'output_file': output_file,
                },
                format='multipart',
                HTTP_X_WORD_AI_WORKER_TOKEN=self.worker_token,
            )
        self.assertEqual(response.status_code, 200)
        self.document.refresh_from_db()
        job.refresh_from_db()
        self.assertEqual(self.document.version_number, 2)
        self.assertEqual(job.status, 'completed')
        self.assertEqual(DocumentVersion.objects.filter(document=self.document).count(), 1)

    @patch('word_ai.services.commit_result_service.schedule_document_preview_regeneration')
    def test_complete_job_schedules_preview_regeneration(self, schedule_preview):
        create_response = self.client.post(
            reverse('api:word_ai_job_list_create'),
            {
                'document_id': self.document.id,
                'instruction': 'Refresh the executive summary.',
            },
            format='json',
        )
        job = WordEditJob.objects.get(pk=create_response.data['id'])
        worker = WordWorker.objects.create(worker_key='direct-host.slot-1', slot_label='slot-1')

        with patch('django.core.files.storage.filesystem.FileSystemStorage.save', new=_fake_storage_save):
            response = self.worker_client.post(
                reverse('api:word_ai_job_complete', args=[job.id]),
                {
                    'worker_key': worker.worker_key,
                    'summary': 'Updated the summary.',
                    'change_note': 'Word AI revision',
                    'output_file': SimpleUploadedFile(
                        'result.docx',
                        b'fake-docx-binary',
                        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    ),
                },
                format='multipart',
                HTTP_X_WORD_AI_WORKER_TOKEN=self.worker_token,
            )
        self.assertEqual(response.status_code, 200)
        schedule_preview.assert_called_once()
        scheduled_document = schedule_preview.call_args.args[0]
        self.assertEqual(scheduled_document.pk, self.document.pk)

    def test_duplicate_complete_is_idempotent(self):
        create_response = self.client.post(
            reverse('api:word_ai_job_list_create'),
            {
                'document_id': self.document.id,
                'instruction': 'Apply the same formal tone.',
            },
            format='json',
        )
        job = WordEditJob.objects.get(pk=create_response.data['id'])
        worker = WordWorker.objects.create(worker_key='direct-host.slot-1', slot_label='slot-1')

        for expected_summary in ('First pass', 'Retry pass'):
            with patch('django.core.files.storage.filesystem.FileSystemStorage.save', new=_fake_storage_save):
                response = self.worker_client.post(
                    reverse('api:word_ai_job_complete', args=[job.id]),
                    {
                        'worker_key': worker.worker_key,
                        'summary': expected_summary,
                        'change_note': 'Word AI revision',
                        'output_file': SimpleUploadedFile(
                            'result.docx',
                            b'fake-docx-binary',
                            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        ),
                    },
                    format='multipart',
                    HTTP_X_WORD_AI_WORKER_TOKEN=self.worker_token,
                )
            self.assertEqual(response.status_code, 200)

        self.document.refresh_from_db()
        job.refresh_from_db()
        self.assertEqual(self.document.version_number, 2)
        self.assertEqual(DocumentVersion.objects.filter(document=self.document).count(), 1)
        self.assertTrue(job.result_version_id)

    def test_complete_job_persists_mcp_trace_fields(self):
        create_response = self.client.post(
            reverse('api:word_ai_job_list_create'),
            {
                'document_id': self.document.id,
                'instruction': 'Make the document more formal.',
                'edit_mode': 'direct_addin_mcp',
            },
            format='json',
        )
        job = WordEditJob.objects.get(pk=create_response.data['id'])
        worker = WordWorker.objects.create(worker_key='direct-host.slot-1', slot_label='slot-1')
        output_file = SimpleUploadedFile(
            'result.docx',
            b'fake-docx-binary',
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        with patch('django.core.files.storage.filesystem.FileSystemStorage.save', new=_fake_storage_save):
            version = commit_job_result(
                job=job,
                worker=worker,
                uploaded_file=output_file,
                summary='Updated the tone.',
                change_note='Word AI revision',
                tool_transcript=[
                    {
                        'command_id': 'cmd-1',
                        'tool_name': 'replace_text',
                        'status': 'completed',
                    }
                ],
                verification_summary={'verified': True},
                artifact_manifest={'output_kind': 'docx_base64'},
                document_checksums={'output_docx_sha256': 'abc123'},
            )
        self.assertEqual(version.version_number, 2)
        job.refresh_from_db()
        self.assertEqual(job.tool_transcript[0]['tool_name'], 'replace_text')
        self.assertTrue(job.verification_summary['verified'])
        self.assertEqual(job.artifact_manifest['output_kind'], 'docx_base64')
        self.assertEqual(job.document_checksums['output_docx_sha256'], 'abc123')

    def test_worker_claim_returns_local_source_file_context(self):
        self.document.output_file = 'generated_docs/source.docx'
        self.document.save(update_fields=['output_file'])
        create_response = self.client.post(
            reverse('api:word_ai_job_list_create'),
            {
                'document_id': self.document.id,
                'instruction': 'Tighten the first paragraph.',
            },
            format='json',
        )
        job = WordEditJob.objects.get(pk=create_response.data['id'])
        job.plan_payload = {
            'mode': 'anchored_edit',
            'target_anchor': '',
            'replacement_text': 'Updated text',
            'format_ops': [],
            'track_changes': False,
            'summary': 'Updated text',
            'warnings': [],
        }
        job.plan_mode = 'anchored_edit'
        job.save(update_fields=['plan_payload', 'plan_mode', 'updated_at'])
        response = self.worker_client.post(
            reverse('api:word_ai_worker_claim'),
            {
                'worker_key': 'direct-host.slot-1',
                'slot_label': 'slot-1',
                'host_name': 'test-host',
            },
            format='json',
            HTTP_X_WORD_AI_WORKER_TOKEN=self.worker_token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['job']['worker_context']['source_file_path'])
        self.assertEqual(response.data['job']['worker_context']['document_version_number'], 1)

    def test_direct_addin_claim_builds_execution_payload_and_session_id(self):
        self.document.output_file = 'generated_docs/source.docx'
        self.document.save(update_fields=['output_file'])
        create_response = self.client.post(
            reverse('api:word_ai_job_list_create'),
            {
                'document_id': self.document.id,
                'instruction': 'Sửa tất cả các từ trong văn bản phải được viết hoa.',
                'edit_mode': 'direct_addin_mcp',
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, 201)
        response = self.worker_client.post(
            reverse('api:word_ai_worker_claim'),
            {
                'worker_key': 'direct-host.slot-1',
                'slot_label': 'slot-1',
                'host_name': 'test-host',
            },
            format='json',
            HTTP_X_WORD_AI_WORKER_TOKEN=self.worker_token,
        )
        self.assertEqual(response.status_code, 200)
        claimed_job = response.data['job']
        self.assertEqual(claimed_job['edit_mode'], 'direct_addin_mcp')
        self.assertTrue(claimed_job['mcp_session_id'])
        self.assertEqual(claimed_job['execution_payload']['schema_version'], 'word-ai-mcp-v1')
        self.assertTrue(claimed_job['execution_payload']['commands'])
        self.assertEqual(claimed_job['execution_payload']['commands'][0]['tool_name'], 'inspect_document')
        self.assertTrue(claimed_job['execution_payload']['agent_loop']['enabled'])
        self.assertTrue(claimed_job['execution_payload']['agent_loop']['must_verify_after_mutation'])
        self.assertEqual(claimed_job['plan_mode'], 'tool_loop')
        self.assertIn('normalize_case_whole_document', claimed_job['execution_payload']['required_capabilities'])
        self.assertEqual(claimed_job['execution_payload']['debug']['runtime'], 'native_word_tool_loop')

    def test_mcp_advance_endpoint_returns_agent_decision(self):
        create_response = self.client.post(
            reverse('api:word_ai_job_list_create'),
            {
                'document_id': self.document.id,
                'instruction': 'Replace the title and then export the file.',
                'edit_mode': 'direct_addin_mcp',
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, 201)
        job = WordEditJob.objects.get(pk=create_response.data['id'])
        job.mcp_session_id = 'session-advance-1'
        job.plan_mode = 'anchored_edit'
        job.plan_payload = {
            'mode': 'anchored_edit',
            'target_anchor': 'Original content',
            'replacement_text': 'Updated content',
            'format_ops': [],
            'track_changes': False,
            'summary': 'Replace the title.',
            'warnings': [],
        }
        job.save(update_fields=['mcp_session_id', 'plan_mode', 'plan_payload', 'updated_at'])
        WordWorker.objects.create(worker_key='direct-host.slot-1', slot_label='slot-1')
        with patch(
            'api.views.word_ai_workers.advance_mcp_agent',
            return_value={
                'action': 'queue_commands',
                'summary': 'Queue verify and export.',
                'warnings': [],
                'commands': [
                    {
                        'id': 'cmd-verify',
                        'tool_name': 'verify_document_case',
                        'input': {
                            'expected': 'uppercase',
                        },
                    },
                    {
                        'id': 'cmd-export',
                        'tool_name': 'export_document',
                        'input': {'include_content_text': True},
                    },
                ],
                'error_code': '',
                'error_detail': '',
            },
        ):
            response = self.worker_client.post(
                reverse('api:word_ai_job_mcp_advance', args=[job.id]),
                {
                    'worker_key': 'direct-host.slot-1',
                    'session_id': 'session-advance-1',
                    'latest_command': {
                        'id': 'cmd-inspect',
                        'tool_name': 'inspect_document',
                        'status': 'completed',
                        'result': {'content_text_length': 16},
                    },
                    'tool_transcript': [
                        {
                            'id': 'cmd-inspect',
                            'tool_name': 'inspect_document',
                            'status': 'completed',
                        }
                    ],
                    'session_snapshot': {
                        'pending_command_count': 0,
                        'in_progress_command_count': 0,
                    },
                },
                format='json',
                HTTP_X_WORD_AI_WORKER_TOKEN=self.worker_token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['action'], 'queue_commands')
        self.assertEqual(response.data['commands'][0]['tool_name'], 'verify_document_case')
        self.assertEqual(response.data['commands'][1]['tool_name'], 'export_document')

    @patch('word_ai.services.mcp_agent_loop_service._build_llm_agent_decision', side_effect=RuntimeError('llm unavailable'))
    def test_mcp_advance_fallback_queues_header_tool_command(self, _mock_decision):
        create_response = self.client.post(
            reverse('api:word_ai_job_list_create'),
            {
                'document_id': self.document.id,
                'instruction': 'Thay toan bo phan header thanh mau moi va bat tracked changes.',
                'edit_mode': 'direct_addin_mcp',
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, 201)
        job = WordEditJob.objects.get(pk=create_response.data['id'])
        job.mcp_session_id = 'session-macro-1'
        job.plan_mode = 'anchored_edit'
        job.plan_payload = {
            'mode': 'anchored_edit',
            'target_anchor': 'Original content',
            'replacement_text': 'Updated content',
            'format_ops': [],
            'track_changes': True,
            'summary': 'Update headers with tracked changes.',
            'warnings': [],
            'macro_capabilities': ['replace_in_headers', 'set_track_revisions'],
        }
        job.save(update_fields=['mcp_session_id', 'plan_mode', 'plan_payload', 'updated_at'])
        WordWorker.objects.create(worker_key='direct-host.slot-1', slot_label='slot-1')
        response = self.worker_client.post(
            reverse('api:word_ai_job_mcp_advance', args=[job.id]),
            {
                'worker_key': 'direct-host.slot-1',
                'session_id': 'session-macro-1',
                'latest_command': {
                    'id': 'cmd-inspect',
                    'tool_name': 'inspect_document',
                    'status': 'completed',
                    'result': {
                        'content_text_length': 16,
                        'track_revisions_state': False,
                    },
                },
                'tool_transcript': [
                    {
                        'id': 'cmd-inspect',
                        'tool_name': 'inspect_document',
                        'status': 'completed',
                    }
                ],
                'session_snapshot': {
                    'pending_command_count': 0,
                    'in_progress_command_count': 0,
                },
            },
            format='json',
            HTTP_X_WORD_AI_WORKER_TOKEN=self.worker_token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['action'], 'queue_commands')
        self.assertEqual(response.data['commands'][0]['tool_name'], 'replace_in_headers')

    @patch('word_ai.services.mcp_agent_loop_service._build_llm_agent_decision', side_effect=RuntimeError('llm unavailable'))
    def test_flagship_fallback_sequence_requires_uppercase_verify_and_bold_verify(self, _mock_decision):
        job = WordEditJob.objects.create(
            document=self.document,
            requested_by=self.user,
            instruction='tat ca cac tu trong van ban phai duoc boi den va viet hoa',
            edit_mode='direct_addin_mcp',
            llm_model_name='fake-model',
            ollama_base_url='http://127.0.0.1:11434',
            prompt_version='word-ai-v1',
            plan_mode='tool_loop',
            plan_payload={'mode': 'tool_loop', 'summary': 'Native Word tool-loop bootstrap context.'},
        )
        decision1 = advance_mcp_agent(
            job=job,
            tool_transcript=[{'id': 'cmd-1', 'tool_name': 'inspect_document', 'status': 'completed'}],
            latest_command={'id': 'cmd-1', 'tool_name': 'inspect_document', 'status': 'completed', 'result': {}},
            session_snapshot={},
        )
        self.assertEqual(decision1['commands'][0]['tool_name'], 'normalize_case_whole_document')

        transcript = [
            {'id': 'cmd-1', 'tool_name': 'inspect_document', 'status': 'completed'},
            {'id': 'cmd-2', 'tool_name': 'normalize_case_whole_document', 'status': 'completed'},
        ]
        decision2 = advance_mcp_agent(
            job=job,
            tool_transcript=transcript,
            latest_command={'id': 'cmd-2', 'tool_name': 'normalize_case_whole_document', 'status': 'completed', 'result': {}},
            session_snapshot={},
        )
        self.assertEqual(decision2['commands'][0]['tool_name'], 'verify_document_case')

        transcript.append(
            {
                'id': 'cmd-3',
                'tool_name': 'verify_document_case',
                'status': 'completed',
                'result': {'is_all_uppercase': True},
            }
        )
        decision3 = advance_mcp_agent(
            job=job,
            tool_transcript=transcript,
            latest_command=transcript[-1],
            session_snapshot={},
        )
        self.assertEqual(decision3['commands'][0]['tool_name'], 'apply_format_whole_document')

        transcript.append(
            {
                'id': 'cmd-4',
                'tool_name': 'apply_format_whole_document',
                'status': 'completed',
                'result': {'bold': True},
            }
        )
        decision4 = advance_mcp_agent(
            job=job,
            tool_transcript=transcript,
            latest_command=transcript[-1],
            session_snapshot={},
        )
        self.assertEqual(decision4['commands'][0]['tool_name'], 'verify_document_format_coverage')

    def test_sanitize_agent_decision_truncates_multi_command_llm_responses(self):
        decision = _sanitize_agent_decision(
            raw_decision={
                'action': 'queue_commands',
                'summary': 'Run mutate then verify.',
                'warnings': [],
                'commands': [
                    {
                        'tool_name': 'normalize_case_whole_document',
                        'input': {'case': 'UPPERCASE'},
                    },
                    {
                        'tool_name': 'verify_document_case',
                        'input': {'case': 'UPPERCASE'},
                    },
                    {
                        'tool_name': 'apply_format_whole_document',
                        'input': {'bold': True},
                    },
                    {
                        'tool_name': 'verify_document_format_coverage',
                        'input': {'format': {'bold': True}},
                    },
                ],
            },
            job=WordEditJob(
                document=self.document,
                requested_by=self.user,
                instruction='tat ca cac tu trong van ban phai duoc boi den va viet hoa',
                edit_mode='direct_addin_mcp',
            ),
            tool_transcript=[],
            latest_command={},
            session_snapshot={},
        )
        self.assertEqual(len(decision['commands']), 1)
        self.assertEqual(decision['commands'][0]['tool_name'], 'normalize_case_whole_document')
        self.assertEqual(decision['commands'][0]['input']['case'], 'uppercase')

    def test_sanitize_agent_decision_backfills_verify_case_from_latest_command(self):
        decision = _sanitize_agent_decision(
            raw_decision={
                'action': 'queue_commands',
                'summary': 'Verify latest uppercase result.',
                'warnings': [],
                'commands': [
                    {
                        'tool_name': 'verify_document_case',
                        'input': {},
                    },
                ],
            },
            job=WordEditJob(
                document=self.document,
                requested_by=self.user,
                instruction='viet hoa toan bo van ban',
                edit_mode='direct_addin_mcp',
            ),
            tool_transcript=[],
            latest_command={
                'tool_name': 'normalize_case_whole_document',
                'input': {'case': 'UPPERCASE'},
                'status': 'completed',
            },
            session_snapshot={},
        )
        self.assertEqual(decision['commands'][0]['input']['expected'], 'uppercase')

    def test_sanitize_agent_decision_normalizes_mutation_alias_inputs(self):
        decision = _sanitize_agent_decision(
            raw_decision={
                'action': 'queue_commands',
                'summary': 'Normalize and format the document.',
                'warnings': [],
                'commands': [
                    {
                        'tool_name': 'normalize_case_whole_document',
                        'input': {'target_case': 'LOWERCASE'},
                    },
                    {
                        'tool_name': 'apply_format_whole_document',
                        'input': {
                            'format': {
                                'bold': True,
                                'italic': True,
                                'fontColor': 'red',
                                'underlined': True,
                            }
                        },
                    },
                ],
            },
            job=WordEditJob(
                document=self.document,
                requested_by=self.user,
                instruction='tat ca van ban phai viet thuong va in dam',
                edit_mode='direct_addin_mcp',
            ),
            tool_transcript=[],
            latest_command={},
            session_snapshot={},
        )
        self.assertEqual(decision['commands'][0]['input']['case'], 'lowercase')
        self.assertNotIn('target_case', decision['commands'][0]['input'])
        self.assertEqual(len(decision['commands']), 1)

    def test_sanitize_agent_decision_normalizes_font_italic_alias(self):
        decision = _sanitize_agent_decision(
            raw_decision={
                'action': 'queue_commands',
                'summary': 'Format the document.',
                'warnings': [],
                'commands': [
                    {
                        'tool_name': 'apply_format_whole_document',
                        'input': {
                            'font_italic': True,
                            'fontColor': 'red',
                        },
                    },
                ],
            },
            job=WordEditJob(
                document=self.document,
                requested_by=self.user,
                instruction='in nghieng van ban',
                edit_mode='direct_addin_mcp',
            ),
            tool_transcript=[],
            latest_command={},
            session_snapshot={},
        )
        self.assertTrue(decision['commands'][0]['input']['italic'])
        self.assertEqual(decision['commands'][0]['input']['font_color'], 'red')
        self.assertNotIn('font_italic', decision['commands'][0]['input'])
        self.assertNotIn('fontColor', decision['commands'][0]['input'])

    def test_sanitize_agent_decision_converts_specific_text_case_change_into_replace(self):
        decision = _sanitize_agent_decision(
            raw_decision={
                'action': 'queue_commands',
                'summary': 'Uppercase a specific text snippet.',
                'warnings': [],
                'commands': [
                    {
                        'tool_name': 'normalize_case_whole_document',
                        'input': {
                            'scope': 'specific_text',
                            'case_type': 'uppercase',
                            'text_to_normalize': 'ngày làm đơn:',
                        },
                    },
                ],
            },
            job=WordEditJob(
                document=self.document,
                requested_by=self.user,
                instruction='chuyen cum ngay lam don thanh viet hoa',
                edit_mode='direct_addin_mcp',
            ),
            tool_transcript=[],
            latest_command={},
            session_snapshot={},
        )
        self.assertEqual(decision['commands'][0]['tool_name'], 'replace_text_matches')
        self.assertEqual(decision['commands'][0]['input']['target_text'], 'ngày làm đơn:')
        self.assertEqual(decision['commands'][0]['input']['replacement_text'], 'NGÀY LÀM ĐƠN:')
        self.assertEqual(decision['commands'][0]['input']['occurrence'], 'all')
        self.assertTrue(decision['commands'][0]['input']['match_case'])
        self.assertTrue(decision['commands'][0]['input']['match_whole_word'])
        self.assertTrue(decision['commands'][0]['input']['preserve_formatting'])

    def test_sanitize_agent_decision_defaults_replace_text_to_exact_match(self):
        decision = _sanitize_agent_decision(
            raw_decision={
                'action': 'queue_commands',
                'summary': 'Replace body text exactly.',
                'warnings': [],
                'commands': [
                    {
                        'tool_name': 'replace_text_matches',
                        'input': {
                            'target_text': 'VNET',
                            'replacement_text': 'Cong ty B',
                        },
                    }
                ],
            },
            job=WordEditJob(
                document=self.document,
                requested_by=self.user,
                instruction='Thay "VNET" thanh "Cong ty B".',
                edit_mode='direct_addin_mcp',
            ),
            tool_transcript=[],
            latest_command={},
            session_snapshot={},
        )
        self.assertEqual(decision['commands'][0]['tool_name'], 'replace_text_matches')
        self.assertEqual(decision['commands'][0]['input']['occurrence'], 'all')
        self.assertTrue(decision['commands'][0]['input']['match_case'])
        self.assertTrue(decision['commands'][0]['input']['match_whole_word'])
        self.assertTrue(decision['commands'][0]['input']['preserve_formatting'])

    def test_sanitize_agent_decision_rejects_export_after_failed_verify(self):
        decision = _sanitize_agent_decision(
            raw_decision={
                'action': 'queue_commands',
                'summary': 'Ready to export.',
                'warnings': [],
                'commands': [
                    {
                        'tool_name': 'export_document',
                        'input': {},
                    },
                ],
            },
            job=WordEditJob(
                document=self.document,
                requested_by=self.user,
                instruction='viet thuong toan bo van ban',
                edit_mode='direct_addin_mcp',
            ),
            tool_transcript=[
                {
                    'tool_name': 'verify_document_case',
                    'status': 'completed',
                    'result': {'verified': False, 'matches_expected_case': False},
                }
            ],
            latest_command={
                'tool_name': 'verify_document_case',
                'status': 'completed',
                'result': {'verified': False, 'matches_expected_case': False},
            },
            session_snapshot={},
        )
        guarded = _guard_agent_decision(
            decision=decision,
            latest_command={
                'tool_name': 'verify_document_case',
                'status': 'completed',
                'result': {'verified': False, 'matches_expected_case': False},
            },
            tool_transcript=[
                {
                    'tool_name': 'verify_document_case',
                    'status': 'completed',
                    'result': {'verified': False, 'matches_expected_case': False},
                }
            ],
            job=WordEditJob(
                document=self.document,
                requested_by=self.user,
                instruction='viet thuong toan bo van ban',
                edit_mode='direct_addin_mcp',
            ),
        )
        self.assertEqual(guarded['action'], 'fail_session')
        self.assertEqual(guarded['error_code'], 'verify_document_case_failed')

    def test_guard_forces_track_changes_off_before_mutation(self):
        decision = _guard_agent_decision(
            decision={
                'action': 'queue_commands',
                'summary': 'Replace body text.',
                'warnings': [],
                'commands': [
                    {
                        'tool_name': 'replace_text_matches',
                        'input': {
                            'target_text': 'Cong ty A',
                            'replacement_text': 'Cong ty B',
                        },
                    }
                ],
                'error_code': '',
                'error_detail': '',
            },
            latest_command={
                'tool_name': 'inspect_document',
                'status': 'completed',
                'result': {'track_revisions_state': True},
            },
            tool_transcript=[
                {
                    'tool_name': 'inspect_document',
                    'status': 'completed',
                    'result': {'track_revisions_state': True},
                }
            ],
            job=WordEditJob(
                document=self.document,
                requested_by=self.user,
                instruction='thay toan bo "Cong ty A" thanh "Cong ty B" trong van ban',
                edit_mode='direct_addin_mcp',
                track_changes=False,
            ),
        )
        self.assertEqual(decision['action'], 'queue_commands')
        self.assertEqual(decision['commands'][0]['tool_name'], 'toggle_track_changes')
        self.assertFalse(decision['commands'][0]['input']['enabled'])

    def test_sanitize_agent_decision_forces_track_changes_on_before_mutation_when_requested(self):
        decision = _sanitize_agent_decision(
            raw_decision={
                'action': 'queue_commands',
                'summary': 'Replace body text.',
                'warnings': [],
                'commands': [
                    {
                        'tool_name': 'replace_text_matches',
                        'input': {
                            'target_text': 'Cong ty A',
                            'replacement_text': 'Cong ty B',
                        },
                    }
                ],
            },
            job=WordEditJob(
                document=self.document,
                requested_by=self.user,
                instruction='thay text va giu track changes',
                edit_mode='direct_addin_mcp',
                track_changes=True,
            ),
            tool_transcript=[
                {
                    'tool_name': 'inspect_document',
                    'status': 'completed',
                    'result': {'track_revisions_state': False},
                }
            ],
            latest_command={
                'tool_name': 'inspect_document',
                'status': 'completed',
                'result': {'track_revisions_state': False},
            },
            session_snapshot={},
        )
        guarded = _guard_agent_decision(
            decision=decision,
            latest_command={
                'tool_name': 'inspect_document',
                'status': 'completed',
                'result': {'track_revisions_state': False},
            },
            tool_transcript=[
                {
                    'tool_name': 'inspect_document',
                    'status': 'completed',
                    'result': {'track_revisions_state': False},
                }
            ],
            job=WordEditJob(
                document=self.document,
                requested_by=self.user,
                instruction='thay text va giu track changes',
                edit_mode='direct_addin_mcp',
                track_changes=True,
            ),
        )
        self.assertEqual(guarded['commands'][0]['tool_name'], 'toggle_track_changes')
        self.assertTrue(guarded['commands'][0]['input']['enabled'])

    @patch('word_ai.services.mcp_agent_loop_service._build_llm_agent_decision', side_effect=RuntimeError('llm unavailable'))
    def test_fallback_detects_exact_text_replacement_request_after_inspect_document(self, _mock_decision):
        job = WordEditJob.objects.create(
            document=self.document,
            requested_by=self.user,
            instruction='Thay "VNET" thanh "Cong ty B".',
            edit_mode='direct_addin_mcp',
            llm_model_name='fake-model',
            ollama_base_url='http://127.0.0.1:11434',
            prompt_version='word-ai-v1',
            plan_mode='tool_loop',
            plan_payload={'mode': 'tool_loop', 'summary': 'Exact replacement runtime.'},
        )
        latest_command = {
            'id': 'cmd-1',
            'tool_name': 'inspect_document',
            'status': 'completed',
            'result': {'track_revisions_state': False},
        }
        decision = advance_mcp_agent(
            job=job,
            tool_transcript=[latest_command],
            latest_command=latest_command,
            session_snapshot={},
        )
        self.assertEqual(decision['action'], 'queue_commands')
        self.assertEqual(decision['commands'][0]['tool_name'], 'inspect_text_matches')
        self.assertEqual(decision['commands'][0]['input']['target_text'], 'VNET')
        self.assertEqual(decision['commands'][0]['input']['replacement_text'], 'Cong ty B')
        self.assertTrue(decision['commands'][0]['input']['match_case'])
        self.assertTrue(decision['commands'][0]['input']['match_whole_word'])

    @patch('word_ai.services.mcp_agent_loop_service._build_llm_agent_decision', side_effect=RuntimeError('llm unavailable'))
    def test_fallback_replaces_exact_text_after_match_inspection(self, _mock_decision):
        job = WordEditJob.objects.create(
            document=self.document,
            requested_by=self.user,
            instruction='Thay "VNET" thanh "Cong ty B".',
            edit_mode='direct_addin_mcp',
            llm_model_name='fake-model',
            ollama_base_url='http://127.0.0.1:11434',
            prompt_version='word-ai-v1',
            plan_mode='tool_loop',
            plan_payload={'mode': 'tool_loop', 'summary': 'Exact replacement runtime.'},
        )
        latest_command = {
            'id': 'cmd-2',
            'tool_name': 'inspect_text_matches',
            'status': 'completed',
            'input': {
                'target_text': 'VNET',
                'replacement_text': 'Cong ty B',
                'match_case': True,
                'match_whole_word': True,
            },
            'result': {'target_count': 3, 'replacement_count': 0},
        }
        decision = advance_mcp_agent(
            job=job,
            tool_transcript=[
                {'id': 'cmd-1', 'tool_name': 'inspect_document', 'status': 'completed'},
                latest_command,
            ],
            latest_command=latest_command,
            session_snapshot={},
        )
        self.assertEqual(decision['action'], 'queue_commands')
        self.assertEqual(decision['commands'][0]['tool_name'], 'replace_text_matches')
        self.assertEqual(decision['commands'][0]['input']['target_text'], 'VNET')
        self.assertEqual(decision['commands'][0]['input']['replacement_text'], 'Cong ty B')
        self.assertTrue(decision['commands'][0]['input']['match_case'])
        self.assertTrue(decision['commands'][0]['input']['match_whole_word'])
        self.assertTrue(decision['commands'][0]['input']['preserve_formatting'])

    def test_fallback_verify_document_case_accepts_lowercase_verified_payload(self):
        job = WordEditJob.objects.create(
            document=self.document,
            requested_by=self.user,
            instruction='chuyen tat ca cac tu thanh viet thuong',
            edit_mode='direct_addin_mcp',
            llm_model_name='fake-model',
            ollama_base_url='http://127.0.0.1:11434',
            prompt_version='word-ai-v1',
            plan_mode='tool_loop',
            plan_payload={'mode': 'tool_loop', 'summary': 'Lowercase runtime.'},
        )
        transcript = [
            {'id': 'cmd-1', 'tool_name': 'inspect_document', 'status': 'completed'},
            {'id': 'cmd-2', 'tool_name': 'normalize_case_whole_document', 'status': 'completed'},
            {
                'id': 'cmd-3',
                'tool_name': 'verify_document_case',
                'status': 'completed',
                'result': {'verified': True, 'matches_expected_case': True, 'is_all_lowercase': True},
            },
        ]
        with patch('word_ai.services.mcp_agent_loop_service._build_llm_agent_decision', side_effect=RuntimeError('llm unavailable')):
            decision = advance_mcp_agent(
                job=job,
                tool_transcript=transcript,
                latest_command=transcript[-1],
                session_snapshot={},
            )
        self.assertEqual(decision['action'], 'queue_commands')
        self.assertEqual(decision['commands'][0]['tool_name'], 'export_document')

    @patch('word_ai.services.mcp_agent_loop_service._build_llm_agent_decision', side_effect=RuntimeError('llm unavailable'))
    def test_fallback_normalize_case_queues_matching_verify_case(self, _mock_decision):
        job = WordEditJob.objects.create(
            document=self.document,
            requested_by=self.user,
            instruction='chuyen tat ca cac tu thanh viet thuong',
            edit_mode='direct_addin_mcp',
            llm_model_name='fake-model',
            ollama_base_url='http://127.0.0.1:11434',
            prompt_version='word-ai-v1',
            plan_mode='tool_loop',
            plan_payload={'mode': 'tool_loop', 'summary': 'Lowercase runtime.'},
        )
        transcript = [
            {'id': 'cmd-1', 'tool_name': 'inspect_document', 'status': 'completed'},
            {'id': 'cmd-2', 'tool_name': 'normalize_case_whole_document', 'status': 'completed'},
        ]
        decision = advance_mcp_agent(
            job=job,
            tool_transcript=transcript,
            latest_command={
                'id': 'cmd-2',
                'tool_name': 'normalize_case_whole_document',
                'status': 'completed',
                'input': {'case': 'lowercase'},
                'result': {'case': 'lowercase'},
            },
            session_snapshot={},
        )
        self.assertEqual(decision['commands'][0]['tool_name'], 'verify_document_case')
        self.assertEqual(decision['commands'][0]['input']['expected'], 'lowercase')

    @patch('word_ai.services.mcp_agent_loop_service._build_llm_agent_decision', side_effect=RuntimeError('llm unavailable'))
    def test_fallback_apply_format_queues_matching_format_verify(self, _mock_decision):
        job = WordEditJob.objects.create(
            document=self.document,
            requested_by=self.user,
            instruction='in nghieng van ban',
            edit_mode='direct_addin_mcp',
            llm_model_name='fake-model',
            ollama_base_url='http://127.0.0.1:11434',
            prompt_version='word-ai-v1',
            plan_mode='tool_loop',
            plan_payload={'mode': 'tool_loop', 'summary': 'Italic runtime.'},
        )
        transcript = [
            {'id': 'cmd-1', 'tool_name': 'inspect_document', 'status': 'completed'},
            {'id': 'cmd-2', 'tool_name': 'apply_format_whole_document', 'status': 'completed'},
        ]
        decision = advance_mcp_agent(
            job=job,
            tool_transcript=transcript,
            latest_command={
                'id': 'cmd-2',
                'tool_name': 'apply_format_whole_document',
                'status': 'completed',
                'input': {'italic': True},
                'result': {'italic': True},
            },
            session_snapshot={},
        )
        self.assertEqual(decision['commands'][0]['tool_name'], 'verify_document_format_coverage')
        self.assertTrue(decision['commands'][0]['input']['italic'])

    def test_guard_fails_when_inspect_text_matches_confirms_target_missing(self):
        decision = _guard_agent_decision(
            decision={
                'action': 'queue_commands',
                'summary': 'Try replacement again.',
                'warnings': ['encoding_mismatch'],
                'commands': [
                    {
                        'tool_name': 'replace_text_matches',
                        'input': {
                            'target_text': 'Suu Minh Tan',
                            'replacement_text': 'Pham Hakcer',
                        },
                    }
                ],
                'error_code': '',
                'error_detail': '',
            },
            latest_command={
                'tool_name': 'inspect_text_matches',
                'status': 'completed',
                'result': {'target_count': 0, 'replacement_count': 0},
            },
            tool_transcript=[
                {
                    'tool_name': 'replace_text_matches',
                    'status': 'completed',
                    'result': {'replaced_count': 0},
                },
                {
                    'tool_name': 'inspect_text_matches',
                    'status': 'completed',
                    'result': {'target_count': 0, 'replacement_count': 0},
                },
            ],
            job=WordEditJob(
                document=self.document,
                requested_by=self.user,
                instruction='sua ten thanh Pham Hakcer',
                edit_mode='direct_addin_mcp',
            ),
        )
        self.assertEqual(decision['action'], 'fail_session')
        self.assertEqual(decision['error_code'], 'text_replacement_target_not_found')

    def test_guard_enforces_replacement_verify_with_match_flags_before_export(self):
        decision = _guard_agent_decision(
            decision={
                'action': 'queue_commands',
                'summary': 'Export immediately.',
                'warnings': [],
                'commands': [
                    {
                        'tool_name': 'export_document',
                        'input': {'include_content_text': True},
                    }
                ],
                'error_code': '',
                'error_detail': '',
            },
            latest_command={
                'tool_name': 'replace_text_matches',
                'status': 'completed',
                'input': {
                    'target_text': 'VNET',
                    'replacement_text': 'Cong ty B',
                    'match_case': True,
                    'match_whole_word': True,
                },
                'result': {'replaced_count': 6},
            },
            tool_transcript=[
                {
                    'tool_name': 'inspect_document',
                    'status': 'completed',
                    'result': {'track_revisions_state': True},
                }
            ],
            job=WordEditJob(
                document=self.document,
                requested_by=self.user,
                instruction='Thay VNET thanh Cong ty B.',
                edit_mode='direct_addin_mcp',
                track_changes=True,
            ),
        )
        self.assertEqual(decision['action'], 'queue_commands')
        self.assertEqual(decision['commands'][0]['tool_name'], 'verify_text_replacement')
        self.assertEqual(decision['commands'][0]['input']['expected_replaced_count'], 6)
        self.assertTrue(decision['commands'][0]['input']['match_case'])
        self.assertTrue(decision['commands'][0]['input']['match_whole_word'])

    def test_advance_returns_verify_failure_before_max_steps_guard(self):
        job = WordEditJob.objects.create(
            document=self.document,
            requested_by=self.user,
            instruction='sua ten thanh Pham Hakcer',
            edit_mode='direct_addin_mcp',
            llm_model_name='fake-model',
            ollama_base_url='http://127.0.0.1:11434',
            prompt_version='word-ai-v1',
            plan_mode='tool_loop',
            plan_payload={'mode': 'tool_loop', 'summary': 'Encoding mismatch repro.'},
        )
        transcript = []
        for index in range(11):
            transcript.append(
                {
                    'id': f'cmd-{index}',
                    'tool_name': 'inspect_document' if index % 2 == 0 else 'replace_text_matches',
                    'status': 'completed',
                    'result': {'replaced_count': 0} if index % 2 == 1 else {},
                }
            )
        latest_command = {
            'id': 'cmd-verify',
            'tool_name': 'verify_text_replacement',
            'status': 'completed',
            'result': {'verified': False, 'matches_expected_replacement': False},
        }
        transcript.append(latest_command)
        decision = advance_mcp_agent(
            job=job,
            tool_transcript=transcript,
            latest_command=latest_command,
            session_snapshot={},
        )
        self.assertEqual(decision['action'], 'fail_session')
        self.assertEqual(decision['error_code'], 'verify_text_replacement_failed')

    @patch('word_ai.services.mcp_agent_loop_service._build_llm_agent_decision', side_effect=RuntimeError('llm unavailable'))
    def test_selection_text_mutation_queues_selection_verify(self, _mock_decision):
        job = WordEditJob.objects.create(
            document=self.document,
            requested_by=self.user,
            instruction='Thay doan dang chon thanh noi dung moi.',
            edit_mode='direct_addin_mcp',
            llm_model_name='fake-model',
            ollama_base_url='http://127.0.0.1:11434',
            prompt_version='word-ai-v1',
            plan_mode='tool_loop',
            plan_payload={'mode': 'tool_loop', 'summary': 'Selection edit runtime.'},
        )
        transcript = [
            {'id': 'cmd-1', 'tool_name': 'inspect_document', 'status': 'completed'},
            {'id': 'cmd-2', 'tool_name': 'replace_selection_text', 'status': 'completed'},
        ]
        decision = advance_mcp_agent(
            job=job,
            tool_transcript=transcript,
            latest_command={
                'id': 'cmd-2',
                'tool_name': 'replace_selection_text',
                'status': 'completed',
                'input': {'replacement_text': 'Noi dung moi'},
                'result': {'scope': 'selection'},
            },
            session_snapshot={},
        )
        self.assertEqual(decision['commands'][0]['tool_name'], 'verify_selection_text')
        self.assertEqual(decision['commands'][0]['input']['expected_text'], 'Noi dung moi')

    @patch('word_ai.services.mcp_agent_loop_service._build_llm_agent_decision', side_effect=RuntimeError('llm unavailable'))
    def test_header_replacement_queues_header_verify(self, _mock_decision):
        job = WordEditJob.objects.create(
            document=self.document,
            requested_by=self.user,
            instruction='Cap nhat header thanh noi dung moi.',
            edit_mode='direct_addin_mcp',
            llm_model_name='fake-model',
            ollama_base_url='http://127.0.0.1:11434',
            prompt_version='word-ai-v1',
            plan_mode='tool_loop',
            plan_payload={
                'mode': 'tool_loop',
                'summary': 'Header update runtime.',
                'target_anchor': 'Header cu',
                'replacement_text': 'Header moi',
            },
        )
        transcript = [
            {'id': 'cmd-1', 'tool_name': 'inspect_document', 'status': 'completed'},
            {'id': 'cmd-2', 'tool_name': 'replace_in_headers', 'status': 'completed'},
        ]
        decision = advance_mcp_agent(
            job=job,
            tool_transcript=transcript,
            latest_command={
                'id': 'cmd-2',
                'tool_name': 'replace_in_headers',
                'status': 'completed',
                'input': {
                    'target_text': 'Header cu',
                    'replacement_text': 'Header moi',
                },
                'result': {'ok': True},
            },
            session_snapshot={},
        )
        self.assertEqual(decision['commands'][0]['tool_name'], 'verify_header_replacement')
        self.assertEqual(decision['commands'][0]['input']['target_text'], 'Header cu')
        self.assertEqual(decision['commands'][0]['input']['replacement_text'], 'Header moi')

    @patch('word_ai.services.mcp_agent_loop_service._build_llm_agent_decision', side_effect=RuntimeError('llm unavailable'))
    def test_line_spacing_mutation_queues_selection_format_verify(self, _mock_decision):
        job = WordEditJob.objects.create(
            document=self.document,
            requested_by=self.user,
            instruction='Tang gian dong cho doan dang chon.',
            edit_mode='direct_addin_mcp',
            llm_model_name='fake-model',
            ollama_base_url='http://127.0.0.1:11434',
            prompt_version='word-ai-v1',
            plan_mode='tool_loop',
            plan_payload={'mode': 'tool_loop', 'summary': 'Line spacing runtime.'},
        )
        transcript = [
            {'id': 'cmd-1', 'tool_name': 'inspect_document', 'status': 'completed'},
            {'id': 'cmd-2', 'tool_name': 'set_line_spacing', 'status': 'completed'},
        ]
        decision = advance_mcp_agent(
            job=job,
            tool_transcript=transcript,
            latest_command={
                'id': 'cmd-2',
                'tool_name': 'set_line_spacing',
                'status': 'completed',
                'input': {'line_spacing': '1.5'},
                'result': {'scope': 'selection', 'line_spacing': '1.5'},
            },
            session_snapshot={},
        )
        self.assertEqual(decision['commands'][0]['tool_name'], 'verify_selection_format')
        self.assertEqual(decision['commands'][0]['input']['line_spacing'], '1.5')

    def test_worker_event_updates_job_status_and_persists_timeline_event(self):
        create_response = self.client.post(
            reverse('api:word_ai_job_list_create'),
            {
                'document_id': self.document.id,
                'instruction': 'Make the body more concise.',
            },
            format='json',
        )
        job = WordEditJob.objects.get(pk=create_response.data['id'])
        worker = WordWorker.objects.create(worker_key='direct-host.slot-1', slot_label='slot-1')
        response = self.worker_client.post(
            reverse('api:word_ai_job_event', args=[job.id]),
            {
                'worker_key': worker.worker_key,
                'step': 'editing',
                'status': 'editing',
                'message': 'Worker started editing.',
                'payload': {'slot_label': 'slot-1'},
            },
            format='json',
            HTTP_X_WORD_AI_WORKER_TOKEN=self.worker_token,
        )
        self.assertEqual(response.status_code, 200)
        job.refresh_from_db()
        self.assertEqual(job.status, 'editing')
        self.assertTrue(job.events.filter(step='editing', status='editing').exists())

    def test_worker_fail_persists_root_cause_payload(self):
        create_response = self.client.post(
            reverse('api:word_ai_job_list_create'),
            {
                'document_id': self.document.id,
                'instruction': 'Update section 3.',
            },
            format='json',
        )
        job = WordEditJob.objects.get(pk=create_response.data['id'])
        worker = WordWorker.objects.create(worker_key='direct-host.slot-2', slot_label='slot-2')
        response = self.worker_client.post(
            reverse('api:word_ai_job_fail', args=[job.id]),
            {
                'worker_key': worker.worker_key,
                'error_code': 'word_runtime_failed',
                'error_detail': 'Word displayed a modal dialog.',
                'failure_payload': {
                    'slot_label': 'slot-2',
                    'workspace_dir': 'C:/Temp/WordAI/slot-2/job-5',
                    'stdout_path': 'C:/Temp/WordAI/slot-2/job-5/logs/runtime.stdout.log',
                    'stderr_path': 'C:/Temp/WordAI/slot-2/job-5/logs/runtime.stderr.log',
                    'failure_category': 'modal_dialog_interference',
                    'fallback_to_single_slot': True,
                },
            },
            format='json',
            HTTP_X_WORD_AI_WORKER_TOKEN=self.worker_token,
        )
        self.assertEqual(response.status_code, 200)
        job.refresh_from_db()
        event = job.events.order_by('-id').first()
        self.assertEqual(job.status, 'failed')
        self.assertEqual(event.status, 'failed')
        self.assertEqual(event.payload['failure_category'], 'modal_dialog_interference')
        self.assertEqual(event.payload['stdout_path'], 'C:/Temp/WordAI/slot-2/job-5/logs/runtime.stdout.log')
        self.assertTrue(event.payload['fallback_to_single_slot'])

    def test_worker_fail_persists_transcript_and_verification_summary(self):
        create_response = self.client.post(
            reverse('api:word_ai_job_list_create'),
            {
                'document_id': self.document.id,
                'instruction': 'Replace VNET with Cong ty B.',
            },
            format='json',
        )
        job = WordEditJob.objects.get(pk=create_response.data['id'])
        worker = WordWorker.objects.create(worker_key='direct-host.slot-1', slot_label='slot-1')
        response = self.worker_client.post(
            reverse('api:word_ai_job_fail', args=[job.id]),
            {
                'worker_key': worker.worker_key,
                'error_code': 'verify_text_replacement_failed',
                'error_detail': 'Replacement verification failed.',
                'tool_transcript': [
                    {
                        'id': 'cmd-1',
                        'tool_name': 'replace_text_matches',
                        'status': 'completed',
                        'input': {
                            'target_text': 'VNET',
                            'replacement_text': 'Cong ty B',
                            'match_case': True,
                            'match_whole_word': True,
                        },
                        'result': {'replaced_count': 6},
                    }
                ],
                'verification_summary': {
                    'verified': False,
                    'replacement': {
                        'verified': False,
                        'target_count': 6,
                        'replacement_count': 0,
                    },
                },
            },
            format='json',
            HTTP_X_WORD_AI_WORKER_TOKEN=self.worker_token,
        )
        self.assertEqual(response.status_code, 200)
        job.refresh_from_db()
        self.assertEqual(job.status, 'failed')
        self.assertEqual(job.tool_transcript[0]['tool_name'], 'replace_text_matches')
        self.assertTrue(job.tool_transcript[0]['input']['match_case'])
        self.assertTrue(job.tool_transcript[0]['input']['match_whole_word'])
        self.assertFalse(job.verification_summary['verified'])
        self.assertEqual(job.verification_summary['replacement']['target_count'], 6)

    def test_worker_auth_is_required_for_worker_endpoints(self):
        response = self.worker_client.post(
            reverse('api:word_ai_worker_claim'),
            {
                'worker_key': 'direct-host.slot-1',
                'slot_label': 'slot-1',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_worker_heartbeat_accepts_token_without_user_authentication(self):
        response = self.worker_client.post(
            reverse('api:word_ai_worker_heartbeat'),
            {
                'worker_key': 'direct-host.slot-1',
                'slot_label': 'slot-1',
                'status': 'idle',
                'metadata': {'free_ram_mb': 8192},
            },
            format='json',
            HTTP_X_WORD_AI_WORKER_TOKEN=self.worker_token,
        )
        self.assertEqual(response.status_code, 200)
        worker = WordWorker.objects.get(worker_key='direct-host.slot-1')
        self.assertEqual(worker.slot_label, 'slot-1')
        self.assertEqual(worker.status, 'idle')

    def test_create_job_rejects_unknown_edit_mode(self):
        response = self.client.post(
            reverse('api:word_ai_job_list_create'),
            {
                'document_id': self.document.id,
                'instruction': 'Rewrite the introduction.',
                'edit_mode': 'not-real',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('edit_mode', response.data)

    def test_planner_json_helpers_accept_fenced_payload_and_sanitize_unknown_ops(self):
        raw = """```json\n{\"mode\":\"anchored_edit\",\"format_ops\":[{\"action\":\"set_alignment\",\"value\":\"center\"},{\"action\":\"bad_op\",\"value\":\"x\"}],\"warnings\":[\"warn_a\"]}\n```"""
        parsed = _extract_json_block(raw)
        plan = _sanitize_plan(
            WordEditJob(track_changes=True, instruction='Can giua tieu de va doi mau chu thanh den.'),
            {
                'mode': 'anchored_edit',
                'format_ops': [
                    {'action': 'set_alignment', 'value': 'center'},
                    {'action': 'set_font_color', 'value': 'black'},
                    {'action': 'bad_op', 'value': 'x'},
                ],
                'warnings': ['warn_a'],
            },
        )
        self.assertIn('"mode":"anchored_edit"', parsed.replace(' ', ''))
        self.assertEqual(len(plan['format_ops']), 2)
        self.assertEqual(plan['format_ops'][1]['action'], 'set_font_color')
        self.assertEqual(plan['warnings'], ['warn_a'])

    def test_planner_sanitize_drops_format_ops_when_instruction_only_changes_text(self):
        plan = _sanitize_plan(
            WordEditJob(track_changes=True, instruction='Thay "Cong ty A" thanh "Cong ty B" va giu nguyen dinh dang.'),
            {
                'mode': 'anchored_edit',
                'format_ops': [
                    {'action': 'set_alignment', 'value': 'center'},
                    {'action': 'set_font_color', 'value': 'black'},
                ],
                'warnings': [],
            },
        )
        self.assertEqual(plan['format_ops'], [])

    def test_claim_bootstraps_native_tool_loop_without_planner_gate(self):
        create_response = self.client.post(
            reverse('api:word_ai_job_list_create'),
            {
                'document_id': self.document.id,
                'instruction': 'Convert this file into an entirely different external template.',
            },
            format='json',
        )
        job = WordEditJob.objects.get(pk=create_response.data['id'])
        claimed_job, worker = claim_next_job(
            worker_key='direct-host.slot-1',
            slot_label='slot-1',
            host_name='test-host',
        )
        self.assertIsNotNone(claimed_job)
        job.refresh_from_db()
        self.assertEqual(job.status, 'claimed')
        self.assertEqual(job.plan_mode, 'tool_loop')
        self.assertEqual(worker.status, 'busy')

    def test_claim_marks_legacy_direct_edit_job_needs_review_when_runtime_is_removed(self):
        job = WordEditJob.objects.create(
            document=self.document,
            requested_by=self.user,
            instruction='Legacy direct edit job.',
            edit_mode='direct_edit',
            llm_model_name='fake-model',
            ollama_base_url='http://127.0.0.1:11434',
            prompt_version='word-ai-v1',
        )
        claimed_job, worker = claim_next_job(
            worker_key='direct-host.slot-1',
            slot_label='slot-1',
            host_name='test-host',
        )
        self.assertIsNone(claimed_job)
        job.refresh_from_db()
        self.assertEqual(job.status, 'needs_review')
        self.assertEqual(worker.status, 'idle')

    @patch('api.views.documents.build_document_preview_pdf')
    def test_completed_job_preview_endpoint_serves_latest_document_version(self, build_preview):
        preview_path = Path(__file__)

        create_response = self.client.post(
            reverse('api:word_ai_job_list_create'),
            {
                'document_id': self.document.id,
                'instruction': 'Refresh the executive summary.',
            },
            format='json',
        )
        job = WordEditJob.objects.get(pk=create_response.data['id'])
        worker = WordWorker.objects.create(worker_key='direct-host.slot-1', slot_label='slot-1')
        with patch('django.core.files.storage.filesystem.FileSystemStorage.save', new=_fake_storage_save):
            complete_response = self.worker_client.post(
                reverse('api:word_ai_job_complete', args=[job.id]),
                {
                    'worker_key': worker.worker_key,
                    'summary': 'Updated the summary.',
                    'change_note': 'Word AI revision',
                    'output_file': SimpleUploadedFile(
                        'result.docx',
                        b'fake-docx-binary',
                        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    ),
                },
                format='multipart',
                HTTP_X_WORD_AI_WORKER_TOKEN=self.worker_token,
            )
        self.assertEqual(complete_response.status_code, 200)

        def _latest_preview(document):
            self.assertEqual(document.version_number, 2)
            return preview_path

        build_preview.side_effect = _latest_preview
        preview_response = self.client.get(reverse('api:document_preview_pdf', args=[self.document.id]))
        self.assertEqual(preview_response.status_code, 200)
        self.assertEqual(preview_response['X-Document-Preview'], 'pdf')
        self.assertEqual(b''.join(preview_response.streaming_content), preview_path.read_bytes())

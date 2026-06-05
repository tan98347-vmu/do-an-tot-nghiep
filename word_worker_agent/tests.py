import json
import os
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import mock_open, patch
from pathlib import Path

from word_worker_agent.backend_client import BackendClient
from word_worker_agent.config import AgentConfig, load_agent_config
from word_worker_agent.job_workspace import build_job_workspace
from word_worker_agent.native_word_tool_bridge import (
    NativeWordToolError,
    _ensure_native_addin_is_current,
    execute_native_word_tool,
)
from word_worker_agent.slot_runner import SlotRunner
from word_worker_agent.slot_state import WorkerSlotState
from word_worker_agent.word_host_session import (
    WordHostSessionError,
    ensure_word_document_open,
)


class AgentConfigTests(unittest.TestCase):
    @patch.dict(
        os.environ,
        {
            'WORD_AI_MAX_WORKER_SLOTS': '2',
            'WORD_AI_ENABLED_WORKER_SLOTS': '2',
            'WORD_AI_PROFILE': 'production',
            'WORD_AI_ENABLE_SLOT2_IN_TEST': '0',
            'WORD_AI_LOCAL_AGENT_TOKEN': 'test-worker-token',
        },
        clear=False,
    )
    def test_slot2_stays_disabled_outside_test_profile(self):
        config = load_agent_config()
        self.assertEqual(config.max_worker_slots, 2)
        self.assertEqual(config.enabled_worker_slots, 1)

    @patch.dict(
        os.environ,
        {
            'WORD_AI_MAX_WORKER_SLOTS': '2',
            'WORD_AI_ENABLED_WORKER_SLOTS': '2',
            'WORD_AI_PROFILE': 'test',
            'WORD_AI_ENABLE_SLOT2_IN_TEST': '1',
            'WORD_AI_LOCAL_AGENT_TOKEN': 'test-worker-token',
        },
        clear=False,
    )
    def test_slot2_can_enable_in_test_profile(self):
        config = load_agent_config()
        self.assertEqual(config.enabled_worker_slots, 2)

    @patch.dict(os.environ, {}, clear=True)
    def test_worker_token_is_required(self):
        with self.assertRaises(RuntimeError) as context:
            load_agent_config()
        self.assertIn('WORD_AI_LOCAL_AGENT_TOKEN', str(context.exception))


class WorkspaceIsolationTests(unittest.TestCase):
    def test_job_workspace_separates_temp_logs_and_artifacts_by_slot(self):
        temp_dir = Path('C:/virtual-workspace-root')
        slot1 = build_job_workspace(base_dir=temp_dir, slot_label='slot-1', job_id=11, create_dirs=False)
        slot2 = build_job_workspace(base_dir=temp_dir, slot_label='slot-2', job_id=22, create_dirs=False)

        self.assertNotEqual(slot1.root_dir, slot2.root_dir)
        self.assertIn('slot-1', str(slot1.temp_dir))
        self.assertIn('slot-2', str(slot2.logs_dir))
        self.assertTrue(str(slot1.output_docx_path).endswith('artifacts\\output.docx'))
        self.assertTrue(str(slot2.runtime_stdout_path).endswith('logs\\runtime.stdout.log'))


class SlotFallbackTests(unittest.TestCase):
    def test_slot2_fallback_does_not_disable_slot1(self):
        slot1 = WorkerSlotState(slot_number=1, enabled=True)
        slot2 = WorkerSlotState(slot_number=2, enabled=True)

        slot2.register_failure(
            detail='Word displayed a modal dialog.',
            category='modal_dialog_interference',
            fallback_to_single_slot=True,
        )

        self.assertTrue(slot1.is_claim_enabled())
        self.assertFalse(slot2.is_claim_enabled())
        self.assertEqual(slot2.disable_reason, 'slot2_auto_fallback')


class BackendClientMultipartTests(unittest.TestCase):
    def test_complete_job_multipart_body_separates_file_headers_from_file_bytes(self):
        client = BackendClient(base_url='http://127.0.0.1:8000/api', worker_token='test-worker-token')
        with patch('builtins.open', mock_open(read_data=b'edited-docx-bytes')):
            body, _content_type = client._build_multipart_body(
                fields={
                    'worker_key': 'direct-host.slot-1',
                    'summary': 'done',
                },
                file_field_name='output_file',
                file_path='C:/virtual-word-ai/result.docx',
                boundary='TESTBOUNDARY',
            )
        self.assertIn(
            (
                b'Content-Disposition: form-data; name="output_file"; filename="result.docx"\r\n'
                b'Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n'
                b'edited-docx-bytes'
            ),
            body,
        )
        self.assertTrue(body.endswith(b'\r\n--TESTBOUNDARY--\r\n'))


class NativeWordToolBridgeTests(unittest.TestCase):
    @patch('word_worker_agent.native_word_tool_bridge.Path.stat', autospec=True)
    @patch('word_worker_agent.native_word_tool_bridge.Path.exists', autospec=True)
    def test_native_addin_stale_detection_blocks_runtime_before_macro_execution(self, exists_mock, stat_mock):
        addin_path = Path('C:/virtual-word-ai/WordAiNativeWorker.dotm')
        macro_bridge_path = Path('C:/virtual-word-ai/WordAiMacroBridge.bas')
        native_tools_path = Path('C:/virtual-word-ai/WordAiNativeTools.bas')
        stat_map = {
            str(addin_path): SimpleNamespace(st_mtime_ns=100),
            str(macro_bridge_path): SimpleNamespace(st_mtime_ns=110),
            str(native_tools_path): SimpleNamespace(st_mtime_ns=120),
        }

        def fake_exists(path_obj):
            return str(path_obj) in stat_map

        def fake_stat(path_obj):
            return stat_map[str(path_obj)]

        exists_mock.side_effect = fake_exists
        stat_mock.side_effect = fake_stat

        with self.assertRaises(NativeWordToolError) as context:
            _ensure_native_addin_is_current(
                addin_path=addin_path,
                module_paths=[macro_bridge_path, native_tools_path],
            )
        self.assertEqual(context.exception.error_code, 'native_word_addin_stale')
        self.assertIn('WordAiNativeTools.bas', context.exception.detail)

    @patch('word_worker_agent.native_word_tool_bridge._ensure_native_addin_is_current')
    @patch('word_worker_agent.native_word_tool_bridge.subprocess.run')
    def test_replace_text_runtime_forwards_match_flags_to_macro_bridge(self, run_mock, _freshness_mock):
        run_mock.return_value = SimpleNamespace(
            returncode=0,
            stdout='{"ok": true}',
            stderr='',
        )

        result = execute_native_word_tool(
            tool_name='replace_text_matches',
            arguments={
                'target_text': 'VNET',
                'replacement_text': 'Cong ty B',
                'occurrence': 'all',
                'match_case': True,
                'match_whole_word': True,
            },
        )

        self.assertEqual(result.tool_name, 'replace_text_matches')
        command = run_mock.call_args.args[0]
        payload = json.loads(command[command.index('-ArgumentsJson') + 1])
        self.assertTrue(payload['match_case'])
        self.assertTrue(payload['match_whole_word'])
        self.assertEqual(payload['target_text'], 'VNET')
        self.assertEqual(payload['replacement_text'], 'Cong ty B')


class WordHostSessionTests(unittest.TestCase):
    @patch('word_worker_agent.word_host_session.subprocess.run')
    def test_open_word_document_parses_json_output(self, run_mock):
        run_mock.return_value = SimpleNamespace(
            returncode=0,
            stdout=json.dumps({'action': 'open', 'opened_existing': False}),
            stderr='',
        )
        result = ensure_word_document_open('C:/virtual-word-ai/input.docx')
        self.assertEqual(result.action, 'open')
        self.assertFalse(result.output_payload['opened_existing'])

    @patch('word_worker_agent.word_host_session.subprocess.run')
    def test_open_word_document_raises_on_failed_script(self, run_mock):
        run_mock.return_value = SimpleNamespace(
            returncode=1,
            stdout='',
            stderr='boom',
        )
        with self.assertRaises(WordHostSessionError) as context:
            ensure_word_document_open('C:/virtual-word-ai/input.docx')
        self.assertEqual(context.exception.error_code, 'word_host_action_failed')


class SlotIsolationExecutionTests(unittest.TestCase):
    def test_two_slots_complete_without_cross_slot_bleed(self):
        workspace_root = Path('C:/virtual-word-ai')
        source_one = workspace_root / 'source-1.docx'
        source_two = workspace_root / 'source-2.docx'
        file_bytes = {
            str(source_one): b'alpha-source',
            str(source_two): b'beta-source',
        }
        text_outputs = {}

        config = AgentConfig(
            backend_base_url='http://127.0.0.1:8000/api',
            worker_token='test-worker-token',
            max_worker_slots=2,
            enabled_worker_slots=2,
            idle_close_seconds=180,
            pause_all_if_free_ram_mb_lt=2000,
            pause_slot2_if_free_ram_mb_lt=3500,
            runtime_profile='test',
            allow_test_slot2=True,
            slot2_failure_threshold=3,
            workspace_root_dir=str(workspace_root),
        )
        backend = _RecordingBackend(file_bytes)
        slot1 = WorkerSlotState(slot_number=1, enabled=True)
        slot2 = WorkerSlotState(slot_number=2, enabled=True)

        def fake_build_workspace(*, base_dir, slot_label, job_id):
            return build_job_workspace(
                base_dir=Path(base_dir),
                slot_label=slot_label,
                job_id=job_id,
                create_dirs=False,
            )

        def fake_exists(path_obj):
            return str(path_obj) in file_bytes

        def fake_read_bytes(path_obj):
            return file_bytes[str(path_obj)]

        def fake_write_bytes(path_obj, data):
            file_bytes[str(path_obj)] = data
            return len(data)

        def fake_write_text(path_obj, data, encoding=None):
            text_outputs[str(path_obj)] = data
            return len(data)

        def fake_advance_session(**payload):
            latest_tool = payload['latest_command']['tool_name']
            if latest_tool == 'inspect_document':
                return {
                    'action': 'queue_commands',
                    'summary': 'Export the current document state.',
                    'warnings': [],
                    'commands': [
                        {
                            'id': f'cmd-export-{payload["job_id"]}',
                            'tool_name': 'export_document',
                            'input': {'include_content_text': True},
                        }
                    ],
                    'error_code': '',
                    'error_detail': '',
                }
            return {
                'action': 'fail_session',
                'summary': 'Unexpected tool transition.',
                'warnings': ['unexpected_transition'],
                'commands': [],
                'error_code': 'unexpected_transition',
                'error_detail': latest_tool,
            }

        def fake_execute_native_word_tool(*, tool_name, arguments):
            if tool_name == 'inspect_document':
                return SimpleNamespace(output_payload={'content_text_length': 11})
            if tool_name == 'export_document':
                if arguments.get('include_content_text'):
                    return SimpleNamespace(output_payload={'content_text': f'export-{threading.current_thread().name}'})
                return SimpleNamespace(output_payload={'content_text': ''})
            if tool_name == 'verify_export_artifact':
                return SimpleNamespace(
                    output_payload={
                        'file_exists': True,
                        'checksum_sha256': 'stubbed-export-checksum',
                        'size_bytes': len(file_bytes[arguments['file_path']]),
                    }
                )
            raise AssertionError(f'Unexpected tool {tool_name}')

        backend.advance_callback = fake_advance_session

        runner1 = SlotRunner(config=config, backend=backend, slot=slot1, host_name='test-host')
        runner2 = SlotRunner(config=config, backend=backend, slot=slot2, host_name='test-host')

        with patch('word_worker_agent.slot_runner.build_job_workspace', side_effect=fake_build_workspace):
            with patch('word_worker_agent.slot_runner.clear_job_workspace', return_value=None):
                with patch('pathlib.Path.exists', new=fake_exists):
                    with patch('pathlib.Path.read_bytes', new=fake_read_bytes):
                        with patch('pathlib.Path.write_bytes', new=fake_write_bytes):
                            with patch('pathlib.Path.write_text', new=fake_write_text):
                                with patch(
                                    'word_worker_agent.slot_runner.ensure_word_document_open',
                                    return_value=SimpleNamespace(
                                        output_payload={'action': 'open', 'opened_existing': False}
                                    ),
                                ):
                                    with patch(
                                        'word_worker_agent.slot_runner.close_word_document_if_open',
                                        return_value=SimpleNamespace(
                                            output_payload={'action': 'close', 'closed': True}
                                        ),
                                    ):
                                        with patch(
                                            'word_worker_agent.slot_runner.execute_native_word_tool',
                                            side_effect=fake_execute_native_word_tool,
                                        ):
                                            thread1 = runner1.start(
                                                {
                                                    'id': 11,
                                                    'document': 101,
                                                    'edit_mode': 'direct_addin_mcp',
                                                    'mcp_session_id': 'session-11',
                                                    'execution_payload': {
                                                        'commands': [
                                                            {'id': 'cmd-1', 'tool_name': 'inspect_document', 'input': {}},
                                                        ]
                                                    },
                                                    'worker_context': {'source_file_path': str(source_one)},
                                                }
                                            )
                                            thread2 = runner2.start(
                                                {
                                                    'id': 22,
                                                    'document': 202,
                                                    'edit_mode': 'direct_addin_mcp',
                                                    'mcp_session_id': 'session-22',
                                                    'execution_payload': {
                                                        'commands': [
                                                            {'id': 'cmd-1', 'tool_name': 'inspect_document', 'input': {}},
                                                        ]
                                                    },
                                                    'worker_context': {'source_file_path': str(source_two)},
                                                }
                                            )
                                            thread1.join(timeout=5)
                                            thread2.join(timeout=5)

        self.assertFalse(thread1.is_alive())
        self.assertFalse(thread2.is_alive())
        self.assertEqual(backend.failures, [])
        self.assertEqual(len(backend.completions), 2)

        completions = {entry['job_id']: entry for entry in backend.completions}
        self.assertEqual(completions[11]['output_bytes'], b'alpha-source')
        self.assertEqual(completions[22]['output_bytes'], b'beta-source')
        self.assertIn('slot-1', completions[11]['output_file_path'])
        self.assertIn('slot-2', completions[22]['output_file_path'])
        self.assertTrue(completions[11]['content_text'].startswith('export-word-ai-slot-1'))
        self.assertTrue(completions[22]['content_text'].startswith('export-word-ai-slot-2'))
        self.assertEqual(
            text_outputs[str(workspace_root / 'slot-1' / 'job-11' / 'artifacts' / 'content.txt')],
            completions[11]['content_text'],
        )
        self.assertEqual(
            text_outputs[str(workspace_root / 'slot-2' / 'job-22' / 'artifacts' / 'content.txt')],
            completions[22]['content_text'],
        )


class SlotRunnerCleanupTests(unittest.TestCase):
    def test_failed_job_keeps_workspace_for_debugging(self):
        workspace = build_job_workspace(
            base_dir=Path('C:/virtual-word-ai'),
            slot_label='slot-1',
            job_id=11,
            create_dirs=False,
        )
        config = AgentConfig(
            backend_base_url='http://127.0.0.1:8000/api',
            worker_token='test-worker-token',
            max_worker_slots=1,
            enabled_worker_slots=1,
            idle_close_seconds=180,
            pause_all_if_free_ram_mb_lt=2000,
            pause_slot2_if_free_ram_mb_lt=3500,
            runtime_profile='production',
            allow_test_slot2=False,
            slot2_failure_threshold=3,
            workspace_root_dir='C:/virtual-word-ai',
        )
        slot = WorkerSlotState(slot_number=1, enabled=True)
        backend = _RecordingBackend({})
        runner = SlotRunner(config=config, backend=backend, slot=slot, host_name='test-host')

        with patch('word_worker_agent.slot_runner.build_job_workspace', return_value=workspace):
            with patch('word_worker_agent.slot_runner.clear_job_workspace') as clear_workspace:
                with patch(
                    'word_worker_agent.slot_runner.ensure_word_document_open',
                    return_value=SimpleNamespace(output_payload={'action': 'open'}),
                ):
                    with patch(
                        'word_worker_agent.slot_runner.close_word_document_if_open',
                        return_value=SimpleNamespace(output_payload={'action': 'close'}),
                    ):
                        with patch(
                            'word_worker_agent.slot_runner.execute_native_word_tool',
                            side_effect=NativeWordToolError('native_word_tool_failed', 'Runtime failed.'),
                        ):
                            with patch('pathlib.Path.exists', return_value=True):
                                with patch('pathlib.Path.read_bytes', return_value=b'input-bytes'):
                                    with patch('pathlib.Path.write_bytes', return_value=len(b'input-bytes')):
                                        runner._run_job(
                                            {
                                                'id': 11,
                                                'document': 101,
                                                'edit_mode': 'direct_addin_mcp',
                                                'execution_payload': {
                                                    'commands': [
                                                        {'id': 'cmd-1', 'tool_name': 'inspect_document', 'input': {}},
                                                    ]
                                                },
                                                'worker_context': {'source_file_path': 'C:/virtual-word-ai/source-1.docx'},
                                            }
                                        )

        clear_workspace.assert_not_called()
        self.assertEqual(backend.failures[0]['error_code'], 'native_word_tool_failed')

    def test_direct_addin_session_uploads_completed_result(self):
        workspace_root = Path('C:/virtual-word-ai')
        source_doc = workspace_root / 'source-1.docx'
        file_bytes = {str(source_doc): b'input-docx'}
        text_outputs = {}
        config = AgentConfig(
            backend_base_url='http://127.0.0.1:8000/api',
            worker_token='test-worker-token',
            max_worker_slots=1,
            enabled_worker_slots=1,
            idle_close_seconds=180,
            pause_all_if_free_ram_mb_lt=2000,
            pause_slot2_if_free_ram_mb_lt=3500,
            runtime_profile='test',
            allow_test_slot2=True,
            slot2_failure_threshold=3,
            workspace_root_dir=str(workspace_root),
        )
        backend = _RecordingBackend(file_bytes)
        slot = WorkerSlotState(slot_number=1, enabled=True)
        runner = SlotRunner(config=config, backend=backend, slot=slot, host_name='test-host')

        def fake_build_workspace(*, base_dir, slot_label, job_id):
            return build_job_workspace(
                base_dir=Path(base_dir),
                slot_label=slot_label,
                job_id=job_id,
                create_dirs=False,
            )

        def fake_exists(path_obj):
            return str(path_obj) in file_bytes

        def fake_read_bytes(path_obj):
            return file_bytes[str(path_obj)]

        def fake_write_bytes(path_obj, data):
            file_bytes[str(path_obj)] = data
            return len(data)

        def fake_write_text(path_obj, data, encoding=None):
            text_outputs[str(path_obj)] = data
            return len(data)

        workspace_input_path = str(workspace_root / 'slot-1' / 'job-11' / 'temp' / 'input.docx')

        def fake_advance_session(**payload):
            latest_tool = payload['latest_command']['tool_name']
            if latest_tool == 'inspect_document':
                return {
                    'action': 'queue_commands',
                    'summary': 'Export the edited document.',
                    'warnings': [],
                    'commands': [
                        {'id': 'cmd-2', 'tool_name': 'export_document', 'input': {'include_content_text': True}},
                    ],
                    'error_code': '',
                    'error_detail': '',
                }
            raise AssertionError(f'Unexpected latest tool: {latest_tool}')

        def fake_execute_native_word_tool(*, tool_name, arguments):
            if tool_name == 'inspect_document':
                file_bytes[workspace_input_path] = b'edited-docx'
                return SimpleNamespace(output_payload={'content_text_length': 8})
            if tool_name == 'export_document':
                return SimpleNamespace(output_payload={'content_text': 'EDITED'})
            if tool_name == 'verify_export_artifact':
                return SimpleNamespace(
                    output_payload={
                        'file_exists': True,
                        'checksum_sha256': 'stubbed-export-checksum',
                        'size_bytes': len(file_bytes[arguments['file_path']]),
                    }
                )
            raise AssertionError(f'Unexpected tool {tool_name}')

        backend.advance_callback = fake_advance_session

        with patch('word_worker_agent.slot_runner.build_job_workspace', side_effect=fake_build_workspace):
            with patch('word_worker_agent.slot_runner.clear_job_workspace', return_value=None):
                with patch('pathlib.Path.exists', new=fake_exists):
                    with patch('pathlib.Path.read_bytes', new=fake_read_bytes):
                        with patch('pathlib.Path.write_bytes', new=fake_write_bytes):
                            with patch('pathlib.Path.write_text', new=fake_write_text):
                                with patch(
                                    'word_worker_agent.slot_runner.ensure_word_document_open',
                                    return_value=SimpleNamespace(
                                        output_payload={'action': 'open', 'opened_existing': False}
                                    ),
                                ) as open_mock:
                                    with patch(
                                        'word_worker_agent.slot_runner.close_word_document_if_open',
                                        return_value=SimpleNamespace(
                                            output_payload={'action': 'close', 'closed': True}
                                        ),
                                    ) as close_mock:
                                        with patch(
                                            'word_worker_agent.slot_runner.execute_native_word_tool',
                                            side_effect=fake_execute_native_word_tool,
                                        ):
                                            thread = runner.start(
                                                {
                                                    'id': 11,
                                                    'document': 101,
                                                    'edit_mode': 'direct_addin_mcp',
                                                    'mcp_session_id': 'session-11',
                                                    'execution_payload': {
                                                        'commands': [
                                                            {'id': 'cmd-1', 'tool_name': 'inspect_document', 'input': {}},
                                                        ]
                                                    },
                                                    'worker_context': {'source_file_path': str(source_doc)},
                                                }
                                            )
                                            thread.join(timeout=5)
        open_mock.assert_called_once()
        close_mock.assert_called_once()

        self.assertFalse(thread.is_alive())
        self.assertEqual(backend.failures, [])
        self.assertEqual(backend.completions[0]['summary'], 'Word native tool-loop edit completed.')
        self.assertEqual(backend.completions[0]['output_bytes'], b'edited-docx')
        self.assertEqual(backend.completions[0]['content_text'], 'EDITED')
        self.assertFalse(backend.completions[0]['verification_summary']['verified'])
        self.assertEqual(
            text_outputs[str(workspace_root / 'slot-1' / 'job-11' / 'artifacts' / 'content.txt')],
            'EDITED',
        )


class SlotRunnerVerificationSummaryTests(unittest.TestCase):
    def test_verification_summary_tracks_selection_and_advanced_verify_results(self):
        config = AgentConfig(
            backend_base_url='http://127.0.0.1:8000/api',
            worker_token='test-worker-token',
            max_worker_slots=1,
            enabled_worker_slots=1,
            idle_close_seconds=180,
            pause_all_if_free_ram_mb_lt=2000,
            pause_slot2_if_free_ram_mb_lt=3500,
            runtime_profile='test',
            allow_test_slot2=True,
            slot2_failure_threshold=3,
            workspace_root_dir='C:/virtual-word-ai',
        )
        runner = SlotRunner(
            config=config,
            backend=_RecordingBackend({}),
            slot=WorkerSlotState(slot_number=1, enabled=True),
            host_name='test-host',
        )
        summary = runner._build_verification_summary(
            [
                {
                    'tool_name': 'verify_selection_text',
                    'result': {'verified': True, 'expected_text': 'Moi'},
                },
                {
                    'tool_name': 'verify_track_changes_state',
                    'result': {'verified': True, 'actual_enabled': True},
                },
                {
                    'tool_name': 'verify_export_artifact',
                    'result': {'verified': True, 'file_exists': True},
                },
            ]
        )

        self.assertTrue(summary['verified'])
        self.assertTrue(summary['selection']['text']['verified'])
        self.assertTrue(summary['advanced']['track_changes']['verified'])
        self.assertIn('verify_selection_text', summary['verify_results'])
        self.assertIn('verify_track_changes_state', summary['verify_results'])

    def test_verification_summary_fails_when_any_verify_step_fails(self):
        config = AgentConfig(
            backend_base_url='http://127.0.0.1:8000/api',
            worker_token='test-worker-token',
            max_worker_slots=1,
            enabled_worker_slots=1,
            idle_close_seconds=180,
            pause_all_if_free_ram_mb_lt=2000,
            pause_slot2_if_free_ram_mb_lt=3500,
            runtime_profile='test',
            allow_test_slot2=True,
            slot2_failure_threshold=3,
            workspace_root_dir='C:/virtual-word-ai',
        )
        runner = SlotRunner(
            config=config,
            backend=_RecordingBackend({}),
            slot=WorkerSlotState(slot_number=1, enabled=True),
            host_name='test-host',
        )
        summary = runner._build_verification_summary(
            [
                {
                    'tool_name': 'verify_document_case',
                    'result': {'verified': True, 'is_all_uppercase': True},
                },
                {
                    'tool_name': 'verify_selection_format',
                    'result': {'verified': False, 'matches_expected_format': False},
                },
                {
                    'tool_name': 'verify_export_artifact',
                    'result': {'verified': True, 'file_exists': True},
                },
            ]
        )

        self.assertFalse(summary['verified'])
        self.assertFalse(summary['selection']['format']['verified'])


class _RecordingBackend:
    def __init__(self, file_bytes, advance_callback=None):
        self.events = []
        self.completions = []
        self.failures = []
        self.file_bytes = file_bytes
        self.advance_callback = advance_callback
        self.advance_calls = []

    def post_job_event(self, **payload):
        self.events.append(payload)

    def complete_job(
        self,
        *,
        job_id,
        worker_key,
        output_file_path,
        summary,
        change_note,
        content_text,
        tool_transcript=None,
        verification_summary=None,
        artifact_manifest=None,
        document_checksums=None,
    ):
        self.completions.append(
            {
                'job_id': job_id,
                'worker_key': worker_key,
                'output_file_path': output_file_path,
                'output_bytes': self.file_bytes[output_file_path],
                'summary': summary,
                'change_note': change_note,
                'content_text': content_text,
                'tool_transcript': tool_transcript or [],
                'verification_summary': verification_summary or {},
                'artifact_manifest': artifact_manifest or {},
                'document_checksums': document_checksums or {},
            }
        )

    def fail_job(self, **payload):
        self.failures.append(payload)

    def advance_tool_loop(self, **payload):
        self.advance_calls.append(payload)
        if self.advance_callback is None:
            return {
                'action': 'fail_session',
                'summary': 'No advance callback configured.',
                'warnings': ['missing_advance_callback'],
                'commands': [],
                'error_code': 'missing_advance_callback',
                'error_detail': '',
            }
        return self.advance_callback(**payload)

    def advance_mcp_session(self, **payload):
        return self.advance_tool_loop(**payload)

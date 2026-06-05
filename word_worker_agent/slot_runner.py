import hashlib
import threading
from pathlib import Path

from word_ai.services.native_word_tool_catalog import is_mutation_tool, is_verify_tool
from word_worker_agent.errors import WordWorkerRuntimeError
from word_worker_agent.failure_policy import classify_worker_failure, slot2_should_fallback
from word_worker_agent.job_workspace import build_job_workspace, clear_job_workspace
from word_worker_agent.logging import log_event
from word_worker_agent.native_word_tool_bridge import NativeWordToolError, execute_native_word_tool
from word_worker_agent.word_host_session import (
    WordHostSessionError,
    close_word_document_if_open,
    ensure_word_document_open,
)


class SlotRunner:
    def __init__(self, *, config, backend, slot, host_name):
        self.config = config
        self.backend = backend
        self.slot = slot
        self.host_name = host_name

    def start(self, job):
        thread = threading.Thread(
            target=self._run_job,
            args=(job,),
            daemon=True,
            name=f'word-ai-{self.slot.label}-job-{job["id"]}',
        )
        self.slot.attach_runner(thread, job)
        thread.start()
        return thread

    def _run_job(self, job):
        workspace = build_job_workspace(
            base_dir=Path(self.config.workspace_root_dir),
            slot_label=self.slot.label,
            job_id=job['id'],
        )
        should_cleanup_workspace = True
        try:
            self._execute_job(job, workspace)
            self.slot.register_success()
        except WordWorkerRuntimeError as exc:
            should_cleanup_workspace = False
            self._report_failure(
                job,
                workspace,
                exc.error_code,
                exc.detail,
                tool_transcript=getattr(exc, 'tool_transcript', None),
                verification_summary=getattr(exc, 'verification_summary', None),
            )
        except Exception as exc:
            should_cleanup_workspace = False
            self._report_failure(job, workspace, 'word_agent_unhandled', str(exc))
        finally:
            if should_cleanup_workspace and not self.config.preserve_job_workspaces:
                clear_job_workspace(workspace)
            self.slot.mark_idle()

    def _execute_job(self, job, workspace):
        if str(job.get('edit_mode') or '') != 'direct_addin_mcp':
            raise WordWorkerRuntimeError(
                'unsupported_edit_mode',
                f'Unsupported Word AI runtime for slot runner: {job.get("edit_mode")}',
            )
        self._execute_native_tool_loop_job(job, workspace)

    def _execute_native_tool_loop_job(self, job, workspace):
        context = job.get('worker_context') or {}
        execution_payload = job.get('execution_payload') or {}
        source_path = str(context.get('source_file_path') or '').strip()
        if not source_path:
            raise WordWorkerRuntimeError('missing_source_file', 'Job did not include a local source file path.')
        source_docx = Path(source_path)
        if not source_docx.exists():
            raise WordWorkerRuntimeError('source_file_missing', f'Source file does not exist: {source_docx}')

        initial_commands = list(execution_payload.get('commands') or [])
        if not initial_commands:
            raise WordWorkerRuntimeError('missing_execution_payload', 'Native Word tool-loop job did not include bootstrap commands.')

        Path(workspace.input_docx_path).write_bytes(source_docx.read_bytes())
        try:
            host_result = ensure_word_document_open(str(workspace.input_docx_path))
        except WordHostSessionError as exc:
            raise WordWorkerRuntimeError(exc.error_code, exc.detail) from exc

        self.slot.mark_editing()
        self.backend.post_job_event(
            job_id=job['id'],
            worker_key=self.slot.worker_key,
            step='native_tool_loop_ready',
            status='editing',
            message='Native Word tool-loop session is ready.',
            payload={
                'slot_label': self.slot.label,
                'workspace_dir': str(workspace.root_dir),
                'source_file_path': str(source_docx),
                'session_id': str(job.get('mcp_session_id') or execution_payload.get('session_id') or ''),
                'command_count': len(initial_commands),
                'schema_version': execution_payload.get('schema_version', ''),
                'required_capabilities': execution_payload.get('required_capabilities') or [],
                'word_host_open': host_result.output_payload,
            },
        )
        log_event(
            'info',
            component='word_worker_agent.runtime',
            step='native_tool_loop_ready',
            status='editing',
            message='Native Word tool-loop session started.',
            job_id=job['id'],
            document_id=job.get('document'),
            worker_slot=self.slot.label,
            payload={
                'session_id': str(job.get('mcp_session_id') or execution_payload.get('session_id') or ''),
                'command_count': len(initial_commands),
            },
        )

        pending_commands = list(initial_commands)
        tool_transcript = []
        latest_command = {}

        try:
            while True:
                if not pending_commands:
                    decision = self.backend.advance_tool_loop(
                        job_id=job['id'],
                        worker_key=self.slot.worker_key,
                        session_id=str(job.get('mcp_session_id') or execution_payload.get('session_id') or ''),
                        latest_command=latest_command,
                        tool_transcript=tool_transcript,
                        session_snapshot=self._session_snapshot(tool_transcript, pending_commands),
                    )
                    action = str(decision.get('action') or '').strip().lower()
                    if action == 'fail_session':
                        raise WordWorkerRuntimeError(
                            str(decision.get('error_code') or 'tool_loop_failed'),
                            str(decision.get('error_detail') or decision.get('summary') or 'Tool loop failed.'),
                        )
                    if action == 'manual_review':
                        raise WordWorkerRuntimeError(
                            'tool_loop_manual_review_required',
                            str(decision.get('summary') or 'Tool loop requires manual review.'),
                        )
                    pending_commands = list(decision.get('commands') or [])
                    if not pending_commands:
                        raise WordWorkerRuntimeError(
                            'tool_loop_stalled',
                            'Tool loop returned no commands before export completed.',
                        )

                command = pending_commands.pop(0)
                latest_command = self._execute_word_command(job, workspace, command)
                tool_transcript.append(latest_command)
                if command['tool_name'] == 'export_document':
                    self._complete_native_tool_loop_job(
                        job=job,
                        workspace=workspace,
                        tool_transcript=tool_transcript,
                        export_result=latest_command.get('result') or {},
                    )
                    break
        except WordWorkerRuntimeError as exc:
            exc.tool_transcript = list(tool_transcript)
            if tool_transcript:
                exc.verification_summary = self._build_verification_summary(tool_transcript)
            raise
        finally:
            self._close_input_document(job, workspace)

    def _execute_word_command(self, job, workspace, command):
        tool_name = str(command.get('tool_name') or '').strip()
        tool_input = dict(command.get('input') or {})
        self.backend.post_job_event(
            job_id=job['id'],
            worker_key=self.slot.worker_key,
            step='tool_start',
            status='editing',
            message='Word native tool started.',
            payload={
                'slot_label': self.slot.label,
                'tool_name': tool_name,
                'tool_input': tool_input,
            },
        )
        try:
            result = execute_native_word_tool(
                tool_name=tool_name,
                arguments=tool_input,
            ).output_payload
        except NativeWordToolError as exc:
            raise WordWorkerRuntimeError(exc.error_code, exc.detail) from exc

        command_record = {
            'id': str(command.get('id') or ''),
            'tool_name': tool_name,
            'status': 'completed',
            'input': tool_input,
            'result': result,
        }
        self.backend.post_job_event(
            job_id=job['id'],
            worker_key=self.slot.worker_key,
            step='tool_complete',
            status='editing',
            message='Word native tool completed.',
            payload={
                'slot_label': self.slot.label,
                'tool_name': tool_name,
                'result': result,
            },
        )
        return command_record

    def _complete_native_tool_loop_job(self, *, job, workspace, tool_transcript, export_result):
        Path(workspace.output_docx_path).write_bytes(Path(workspace.input_docx_path).read_bytes())
        artifact_verification = execute_native_word_tool(
            tool_name='verify_export_artifact',
            arguments={'file_path': str(workspace.output_docx_path)},
        ).output_payload
        tool_transcript.append(
            {
                'id': 'local-verify-export',
                'tool_name': 'verify_export_artifact',
                'status': 'completed',
                'input': {'file_path': str(workspace.output_docx_path)},
                'result': artifact_verification,
            }
        )
        content_text = str(export_result.get('content_text') or '')
        Path(workspace.extracted_text_path).write_text(content_text, encoding='utf-8')
        output_bytes = Path(workspace.output_docx_path).read_bytes()
        verification_summary = self._build_verification_summary(tool_transcript)
        verification_summary['export_artifact'] = artifact_verification
        if self._requires_verified_output(tool_transcript) and not verification_summary.get('verified'):
            raise WordWorkerRuntimeError(
                'hard_verify_required_before_success',
                'The Word runtime exported a document without passing the required verify steps.',
            )
        document_checksums = {
            'output_docx_sha256': hashlib.sha256(output_bytes).hexdigest(),
            'content_text_sha256': hashlib.sha256(content_text.encode('utf-8')).hexdigest(),
        }
        artifact_manifest = {
            'runtime': 'native_word_tool_loop',
            'tool_count': len(tool_transcript),
            'output_kind': 'workspace_docx',
            'export_verification': artifact_verification,
        }

        self.slot.mark_uploading()
        self.backend.post_job_event(
            job_id=job['id'],
            worker_key=self.slot.worker_key,
            step='tool_loop_uploading',
            status='uploading',
            message='Native Word tool-loop completed; uploading exported document.',
            payload={
                'slot_label': self.slot.label,
                'tool_transcript_count': len(tool_transcript),
                'verification_summary': verification_summary,
                'artifact_manifest': artifact_manifest,
                'document_checksums': document_checksums,
            },
        )
        self.backend.complete_job(
            job_id=job['id'],
            worker_key=self.slot.worker_key,
            output_file_path=str(workspace.output_docx_path),
            summary='Word native tool-loop edit completed.',
            change_note='Word AI native tool-loop edit',
            content_text=content_text,
            tool_transcript=tool_transcript,
            verification_summary=verification_summary,
            artifact_manifest=artifact_manifest,
            document_checksums=document_checksums,
        )
        log_event(
            'info',
            component='word_worker_agent.runtime',
            step='tool_loop_complete',
            status='completed',
            message='Native Word tool-loop uploaded a completed result.',
            job_id=job['id'],
            document_id=job.get('document'),
            worker_slot=self.slot.label,
            payload={
                'tool_transcript_count': len(tool_transcript),
                'verification_summary': verification_summary,
            },
        )

    def _build_verification_summary(self, tool_transcript):
        summary = {
            'verified': False,
            'case': {},
            'format': {},
            'selection': {},
            'advanced': {},
            'verify_results': {},
            'export_artifact': {},
        }
        for item in tool_transcript:
            tool_name = str(item.get('tool_name') or '').strip()
            result = dict(item.get('result') or {})
            if tool_name == 'verify_document_case':
                summary['case'] = result
            elif tool_name == 'verify_document_format_coverage':
                summary['format'] = result
            elif tool_name == 'verify_text_replacement':
                summary['replacement'] = result
            elif tool_name == 'verify_selection_text':
                summary['selection']['text'] = result
            elif tool_name == 'verify_selection_case':
                summary['selection']['case'] = result
            elif tool_name == 'verify_selection_format':
                summary['selection']['format'] = result
            elif tool_name == 'verify_track_changes_state':
                summary['advanced']['track_changes'] = result
            elif tool_name == 'verify_header_replacement':
                summary['advanced']['headers'] = result
            elif tool_name == 'verify_footer_replacement':
                summary['advanced']['footers'] = result
            elif tool_name == 'verify_table_replacement':
                summary['advanced']['tables'] = result
            elif tool_name == 'verify_comment_selection':
                summary['advanced']['comments'] = result
            elif tool_name == 'verify_export_artifact':
                summary['export_artifact'] = result
            if is_verify_tool(tool_name):
                summary['verify_results'][tool_name] = result
        verify_results = {
            tool_name: result
            for tool_name, result in summary['verify_results'].items()
            if tool_name != 'verify_export_artifact'
        }
        has_verification = bool(verify_results)
        all_verifies_passed = all(
            self._verify_tool_result_passed(tool_name, result)
            for tool_name, result in verify_results.items()
        )
        export_verified = not summary['export_artifact'] or self._verify_tool_result_passed(
            'verify_export_artifact',
            summary['export_artifact'],
        )
        summary['verified'] = bool(has_verification and all_verifies_passed and export_verified)
        return summary

    def _verify_tool_result_passed(self, tool_name, result):
        payload = dict(result or {})
        if 'verified' in payload:
            return bool(payload.get('verified'))
        if tool_name == 'verify_export_artifact':
            return bool(payload.get('file_exists'))
        if 'matches_expected_case' in payload:
            return bool(payload.get('matches_expected_case'))
        if 'matches_expected_format' in payload:
            return bool(payload.get('matches_expected_format'))
        if 'matches_expected_replacement' in payload:
            return bool(payload.get('matches_expected_replacement'))
        if 'is_all_lowercase' in payload:
            return bool(payload.get('is_all_lowercase'))
        if 'is_all_uppercase' in payload:
            return bool(payload.get('is_all_uppercase'))
        return False

    def _requires_verified_output(self, tool_transcript):
        for item in tool_transcript:
            tool_name = str(item.get('tool_name') or '').strip()
            if is_mutation_tool(tool_name) and not is_verify_tool(tool_name):
                return True
        return False

    def _session_snapshot(self, tool_transcript, pending_commands):
        return {
            'completed_command_count': len(tool_transcript),
            'pending_command_count': len(pending_commands),
            'completed_tool_names': [str(item.get('tool_name') or '') for item in tool_transcript],
        }

    def _report_failure(self, job, workspace, error_code, detail, tool_transcript=None, verification_summary=None):
        failure_category = classify_worker_failure(error_code, detail)
        fallback_to_single_slot = slot2_should_fallback(
            self.config,
            slot_number=self.slot.slot_number,
            failure_count=self.slot.failure_count + 1,
            failure_category=failure_category,
        )
        failure_payload = self._build_failure_payload(
            job,
            workspace,
            error_code=error_code,
            detail=detail,
            failure_category=failure_category,
            fallback_to_single_slot=fallback_to_single_slot,
        )
        self.slot.register_failure(
            detail=detail,
            category=failure_category,
            fallback_to_single_slot=fallback_to_single_slot,
        )
        self.slot.mark_error(detail)
        self.backend.fail_job(
            job_id=job['id'],
            worker_key=self.slot.worker_key,
            error_code=error_code,
            error_detail=detail,
            tool_transcript=tool_transcript,
            verification_summary=verification_summary,
            failure_payload=failure_payload,
        )
        log_event(
            'error',
            component='word_worker_agent.runtime',
            step='failed',
            status='failed',
            message=detail,
            job_id=job['id'],
            document_id=job.get('document'),
            worker_slot=self.slot.label,
            error_code=error_code,
            payload=failure_payload,
        )

    def _build_failure_payload(self, job, workspace, *, error_code, detail, failure_category, fallback_to_single_slot):
        context = job.get('worker_context') or {}
        plan_payload = job.get('plan_payload') or {}
        return {
            'slot_label': self.slot.label,
            'workspace_dir': str(workspace.root_dir),
            'temp_dir': str(workspace.temp_dir),
            'logs_dir': str(workspace.logs_dir),
            'artifacts_dir': str(workspace.artifacts_dir),
            'stdout_path': str(workspace.runtime_stdout_path),
            'stderr_path': str(workspace.runtime_stderr_path),
            'input_docx_path': str(workspace.input_docx_path),
            'output_docx_path': str(workspace.output_docx_path),
            'source_file_path': str(context.get('source_file_path') or ''),
            'plan_mode': job.get('plan_mode', ''),
            'replacement_text_preview': str(plan_payload.get('replacement_text') or '')[:160],
            'execution_payload': job.get('execution_payload') or {},
            'error_code': error_code,
            'error_detail': detail,
            'failure_category': failure_category,
            'fallback_to_single_slot': fallback_to_single_slot,
        }

    def _close_input_document(self, job, workspace):
        try:
            host_result = close_word_document_if_open(str(workspace.input_docx_path))
        except WordHostSessionError as exc:
            self.backend.post_job_event(
                job_id=job['id'],
                worker_key=self.slot.worker_key,
                step='word_host_close',
                status='warning',
                message='Word input document close attempt failed.',
                level='warning',
                payload={
                    'slot_label': self.slot.label,
                    'input_docx_path': str(workspace.input_docx_path),
                    'error_code': exc.error_code,
                    'error_detail': exc.detail,
                },
            )
            return
        self.backend.post_job_event(
            job_id=job['id'],
            worker_key=self.slot.worker_key,
            step='word_host_close',
            status='completed',
            message='Word input document close attempt completed.',
            payload={
                'slot_label': self.slot.label,
                'input_docx_path': str(workspace.input_docx_path),
                'word_host_close': host_result.output_payload,
            },
        )

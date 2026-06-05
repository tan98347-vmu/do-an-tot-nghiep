import uuid

from word_ai.services.event_log_service import append_job_event
from word_ai.services.native_word_tool_catalog import allowed_native_word_tools


def mcp_schema_version():
    from django.conf import settings

    return getattr(settings, 'WORD_AI_MCP_SCHEMA_VERSION', 'word-ai-mcp-v1')


def build_direct_addin_execution_payload(job, plan_payload):
    session_id = f'word-ai-job-{job.id}-{uuid.uuid4().hex[:10]}'
    payload = {
        'schema_version': mcp_schema_version(),
        'session_id': session_id,
        'planner_mode': str((plan_payload or {}).get('mode') or '').strip(),
        'planner_summary': str((plan_payload or {}).get('summary') or '').strip(),
        'required_capabilities': allowed_native_word_tools(),
        'commands': [
            _build_command(
                'inspect_document',
                {
                    'scope': 'whole_document',
                    'include_text_excerpt': True,
                    'include_track_revisions_state': True,
                },
            )
        ],
        'agent_loop': {
            'enabled': True,
            'initial_tool': 'inspect_document',
            'must_verify_after_mutation': True,
            'export_is_terminal': True,
        },
        'debug': {
            'runtime': 'native_word_tool_loop',
            'instruction_length': len(str(job.instruction or '')),
            'track_changes': bool(job.track_changes),
        },
    }
    append_job_event(
        job,
        step='mcp_contract',
        status='prepared',
        message='Native Word tool-loop execution payload prepared.',
        payload={
            'session_id': session_id,
            'schema_version': payload['schema_version'],
            'command_count': len(payload['commands']),
            'required_capabilities': payload['required_capabilities'],
            'runtime': 'native_word_tool_loop',
        },
    )
    return payload


def _build_command(tool_name, command_input):
    return {
        'id': f'cmd-{uuid.uuid4().hex[:12]}',
        'tool_name': tool_name,
        'input': command_input,
    }

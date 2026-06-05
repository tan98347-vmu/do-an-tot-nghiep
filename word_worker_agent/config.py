import os
import tempfile
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    backend_base_url: str
    worker_token: str
    max_worker_slots: int
    enabled_worker_slots: int
    idle_close_seconds: int
    pause_all_if_free_ram_mb_lt: int
    pause_slot2_if_free_ram_mb_lt: int
    runtime_profile: str
    allow_test_slot2: bool
    slot2_failure_threshold: int
    workspace_root_dir: str
    preserve_job_workspaces: bool = False


def _bool_env(name, default=False):
    raw = (os.getenv(name, '1' if default else '0') or '').strip().lower()
    return raw in {'1', 'true', 'yes', 'on'}


def _resolve_enabled_worker_slots(*, max_worker_slots, requested_enabled_slots, runtime_profile, allow_test_slot2):
    enabled_slots = min(max(requested_enabled_slots, 1), max_worker_slots)
    if enabled_slots < 2:
        return enabled_slots
    if runtime_profile == 'test' and allow_test_slot2:
        return enabled_slots
    return 1


def _required_env(name):
    value = (os.getenv(name, '') or '').strip()
    if not value:
        raise RuntimeError(f'Missing required environment variable: {name}')
    return value


def load_agent_config():
    max_worker_slots = max(int(os.getenv('WORD_AI_MAX_WORKER_SLOTS', '2') or '2'), 1)
    requested_enabled_slots = max(int(os.getenv('WORD_AI_ENABLED_WORKER_SLOTS', '1') or '1'), 1)
    runtime_profile = (os.getenv('WORD_AI_PROFILE', 'production') or 'production').strip().lower()
    allow_test_slot2 = _bool_env('WORD_AI_ENABLE_SLOT2_IN_TEST', default=False)
    return AgentConfig(
        backend_base_url=os.getenv('WORD_AI_BACKEND_BASE_URL', 'http://127.0.0.1:8000/api'),
        worker_token=_required_env('WORD_AI_LOCAL_AGENT_TOKEN'),
        max_worker_slots=max_worker_slots,
        enabled_worker_slots=_resolve_enabled_worker_slots(
            max_worker_slots=max_worker_slots,
            requested_enabled_slots=requested_enabled_slots,
            runtime_profile=runtime_profile,
            allow_test_slot2=allow_test_slot2,
        ),
        idle_close_seconds=max(int(os.getenv('WORD_AI_WORD_IDLE_CLOSE_SECONDS', '180') or '180'), 30),
        pause_all_if_free_ram_mb_lt=max(int(os.getenv('WORD_AI_PAUSE_ALL_FREE_RAM_MB_LT', '2000') or '2000'), 512),
        pause_slot2_if_free_ram_mb_lt=max(int(os.getenv('WORD_AI_PAUSE_SLOT2_FREE_RAM_MB_LT', '3500') or '3500'), 1024),
        runtime_profile=runtime_profile,
        allow_test_slot2=allow_test_slot2,
        slot2_failure_threshold=max(int(os.getenv('WORD_AI_SLOT2_FAILURE_THRESHOLD', '3') or '3'), 2),
        workspace_root_dir=os.getenv(
            'WORD_AI_WORKSPACE_ROOT',
            os.path.join(tempfile.gettempdir(), 'WordAI'),
        ),
        preserve_job_workspaces=_bool_env('WORD_AI_PRESERVE_JOB_WORKSPACES', default=False),
    )

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name('run_word_addin_host.ps1')


class WordHostSessionError(RuntimeError):
    def __init__(self, error_code, detail):
        super().__init__(detail)
        self.error_code = error_code
        self.detail = detail


@dataclass(frozen=True)
class WordHostSessionResult:
    action: str
    document_path: str
    output_payload: dict


def ensure_word_document_open(document_path):
    return _run_word_host_action(action='open', document_path=document_path)


def close_word_document_if_open(document_path):
    return _run_word_host_action(action='close', document_path=document_path)


def _run_word_host_action(*, action, document_path):
    normalized_action = str(action or '').strip().lower()
    if normalized_action not in {'open', 'close'}:
        raise WordHostSessionError('word_host_invalid_action', f'Unsupported Word host action: {action}')
    normalized_path = str(Path(document_path).resolve())
    completed = subprocess.run(
        [
            'powershell.exe',
            '-NoProfile',
            '-NonInteractive',
            '-ExecutionPolicy',
            'Bypass',
            '-File',
            str(SCRIPT_PATH),
            '-Action',
            normalized_action,
            '-DocumentPath',
            normalized_path,
        ],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=180,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or '').strip() or 'Word host action failed.'
        raise WordHostSessionError('word_host_action_failed', detail)
    stdout_text = (completed.stdout or '').strip()
    try:
        payload = json.loads(stdout_text or '{}')
    except json.JSONDecodeError as exc:
        raise WordHostSessionError('word_host_invalid_output', stdout_text or 'Word host returned invalid JSON.') from exc
    return WordHostSessionResult(
        action=normalized_action,
        document_path=normalized_path,
        output_payload=payload,
    )

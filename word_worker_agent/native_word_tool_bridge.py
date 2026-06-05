import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from hashlib import sha256


SCRIPT_PATH = Path(__file__).with_name('run_word_native_tool.ps1')
REPO_ROOT = SCRIPT_PATH.parent.parent
DEFAULT_ADDIN_PATH = REPO_ROOT / '.codex-runtime' / 'native-word-addin' / 'WordAiNativeWorker.dotm'
VBA_MODULE_PATHS = (
    REPO_ROOT / 'word_addin' / 'vba' / 'WordAiMacroBridge.bas',
    REPO_ROOT / 'word_addin' / 'vba' / 'WordAiNativeTools.bas',
)


TOOL_REGISTRY = {
    'inspect_document': {
        'macro_name': 'WordAiNativeTools.InspectDocument',
        'required_arguments': [],
        'save_after': False,
    },
    'inspect_selection': {
        'macro_name': 'WordAiNativeTools.InspectSelection',
        'required_arguments': [],
        'save_after': False,
    },
    'inspect_text_matches': {
        'macro_name': 'WordAiNativeTools.InspectTextMatches',
        'required_arguments': ['target_text'],
        'save_after': False,
    },
    'inspect_format_state': {
        'macro_name': 'WordAiNativeTools.InspectFormatState',
        'required_arguments': [],
        'save_after': False,
    },
    'replace_text_matches': {
        'macro_name': 'WordAiNativeTools.ReplaceTextMatches',
        'required_arguments': ['target_text', 'replacement_text'],
        'save_after': True,
    },
    'replace_selection_text': {
        'macro_name': 'WordAiNativeTools.ReplaceSelectionText',
        'required_arguments': ['replacement_text'],
        'save_after': True,
    },
    'verify_text_replacement': {
        'macro_name': 'WordAiNativeTools.VerifyTextReplacement',
        'required_arguments': ['target_text', 'replacement_text'],
        'save_after': False,
    },
    'normalize_case_whole_document': {
        'macro_name': 'WordAiNativeTools.NormalizeCaseWholeDocument',
        'required_arguments': ['case'],
        'save_after': True,
    },
    'normalize_case_selection': {
        'macro_name': 'WordAiNativeTools.NormalizeCaseSelection',
        'required_arguments': ['case'],
        'save_after': True,
    },
    'apply_format_whole_document': {
        'macro_name': 'WordAiNativeTools.ApplyFormatWholeDocument',
        'required_arguments': [],
        'save_after': True,
    },
    'apply_format_selection': {
        'macro_name': 'WordAiNativeTools.ApplyFormatSelection',
        'required_arguments': [],
        'save_after': True,
    },
    'clear_format_selection': {
        'macro_name': 'WordAiNativeTools.ClearFormatSelection',
        'required_arguments': [],
        'save_after': True,
    },
    'set_paragraph_alignment': {
        'macro_name': 'WordAiNativeTools.SetParagraphAlignment',
        'required_arguments': ['alignment'],
        'save_after': True,
    },
    'set_line_spacing': {
        'macro_name': 'WordAiNativeTools.SetLineSpacing',
        'required_arguments': ['line_spacing'],
        'save_after': True,
    },
    'set_paragraph_spacing': {
        'macro_name': 'WordAiNativeTools.SetParagraphSpacing',
        'required_arguments': [],
        'save_after': True,
    },
    'toggle_track_changes': {
        'macro_name': 'WordAiNativeTools.ToggleTrackChanges',
        'required_arguments': ['enabled'],
        'save_after': True,
    },
    'replace_in_headers': {
        'macro_name': 'WordAiNativeTools.ReplaceInHeaders',
        'required_arguments': ['target_text', 'replacement_text'],
        'save_after': True,
    },
    'replace_in_footers': {
        'macro_name': 'WordAiNativeTools.ReplaceInFooters',
        'required_arguments': ['target_text', 'replacement_text'],
        'save_after': True,
    },
    'replace_in_tables': {
        'macro_name': 'WordAiNativeTools.ReplaceInTables',
        'required_arguments': ['target_text', 'replacement_text'],
        'save_after': True,
    },
    'insert_comment_selection': {
        'macro_name': 'WordAiNativeTools.InsertCommentSelection',
        'required_arguments': ['comment_text'],
        'save_after': True,
    },
    'verify_document_case': {
        'macro_name': 'WordAiNativeTools.VerifyDocumentCase',
        'required_arguments': ['expected'],
        'save_after': False,
    },
    'verify_document_format_coverage': {
        'macro_name': 'WordAiNativeTools.VerifyDocumentFormatCoverage',
        'required_arguments': [],
        'save_after': False,
    },
    'verify_selection_text': {
        'macro_name': 'WordAiNativeTools.VerifySelectionText',
        'required_arguments': ['expected_text'],
        'save_after': False,
    },
    'verify_selection_case': {
        'macro_name': 'WordAiNativeTools.VerifySelectionCase',
        'required_arguments': ['expected'],
        'save_after': False,
    },
    'verify_selection_format': {
        'macro_name': 'WordAiNativeTools.VerifySelectionFormat',
        'required_arguments': [],
        'save_after': False,
    },
    'verify_track_changes_state': {
        'macro_name': 'WordAiNativeTools.VerifyTrackChangesState',
        'required_arguments': ['expected_enabled'],
        'save_after': False,
    },
    'verify_header_replacement': {
        'macro_name': 'WordAiNativeTools.VerifyHeaderReplacement',
        'required_arguments': ['target_text', 'replacement_text'],
        'save_after': False,
    },
    'verify_footer_replacement': {
        'macro_name': 'WordAiNativeTools.VerifyFooterReplacement',
        'required_arguments': ['target_text', 'replacement_text'],
        'save_after': False,
    },
    'verify_table_replacement': {
        'macro_name': 'WordAiNativeTools.VerifyTableReplacement',
        'required_arguments': ['target_text', 'replacement_text'],
        'save_after': False,
    },
    'verify_comment_selection': {
        'macro_name': 'WordAiNativeTools.VerifyCommentSelection',
        'required_arguments': [],
        'save_after': False,
    },
    'export_document': {
        'macro_name': 'WordAiNativeTools.ExportDocument',
        'required_arguments': [],
        'save_after': True,
    },
}


class NativeWordToolError(RuntimeError):
    def __init__(self, error_code, detail):
        super().__init__(detail)
        self.error_code = error_code
        self.detail = detail


@dataclass(frozen=True)
class NativeWordToolResult:
    tool_name: str
    macro_name: str
    output_payload: dict


def execute_native_word_tool(*, tool_name, arguments):
    if str(tool_name or '').strip() == 'verify_export_artifact':
        return _verify_export_artifact(arguments=arguments)
    spec = TOOL_REGISTRY.get(str(tool_name or '').strip())
    if spec is None:
        raise NativeWordToolError('native_word_tool_not_allowed', f'Unsupported Word tool: {tool_name}')

    payload = dict(arguments or {})
    missing = [name for name in spec['required_arguments'] if name not in payload]
    if missing:
        raise NativeWordToolError(
            'native_word_tool_missing_arguments',
            f'Missing arguments for {tool_name}: {", ".join(missing)}',
        )
    _ensure_native_addin_is_current()

    completed = subprocess.run(
        [
            'powershell.exe',
            '-NoProfile',
            '-NonInteractive',
            '-ExecutionPolicy',
            'Bypass',
            '-File',
            str(SCRIPT_PATH),
            '-MacroName',
            spec['macro_name'],
            '-ArgumentsJson',
            json.dumps(payload, ensure_ascii=True),
            '-SaveAfter',
            'true' if spec['save_after'] else 'false',
        ],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=240,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or '').strip() or 'Native Word tool execution failed.'
        raise NativeWordToolError('native_word_tool_failed', detail)

    stdout_text = (completed.stdout or '').strip()
    try:
        output_payload = json.loads(stdout_text or '{}')
    except json.JSONDecodeError as exc:
        raise NativeWordToolError(
            'native_word_tool_invalid_output',
            stdout_text or 'Native Word tool returned invalid JSON.',
        ) from exc

    return NativeWordToolResult(
        tool_name=str(tool_name),
        macro_name=spec['macro_name'],
        output_payload=output_payload,
    )


def _verify_export_artifact(*, arguments):
    payload = dict(arguments or {})
    file_path = str(payload.get('file_path') or '').strip()
    if not file_path:
        raise NativeWordToolError('native_word_tool_missing_arguments', 'Missing arguments for verify_export_artifact: file_path')
    artifact_path = Path(file_path)
    if not artifact_path.exists():
        raise NativeWordToolError('native_word_export_missing', f'Export artifact does not exist: {artifact_path}')
    file_bytes = artifact_path.read_bytes()
    output_payload = {
        'ok': True,
        'file_exists': True,
        'file_path': str(artifact_path),
        'file_size_bytes': len(file_bytes),
        'sha256': sha256(file_bytes).hexdigest(),
        'verified': True,
    }
    return NativeWordToolResult(
        tool_name='verify_export_artifact',
        macro_name='local.verify_export_artifact',
        output_payload=output_payload,
    )


def _ensure_native_addin_is_current(*, addin_path=None, module_paths=None):
    resolved_addin_path = Path(addin_path or DEFAULT_ADDIN_PATH)
    if not resolved_addin_path.exists():
        raise NativeWordToolError(
            'native_word_addin_missing',
            'Khong tim thay Word AI native add-in. Hay chay lai deploy/word_worker_direct_host/build_native_word_addin.ps1 '
            'va deploy/word_worker_direct_host/install_native_word_addin.ps1 truoc khi dung Word AI.',
        )

    source_modules = [Path(item) for item in (module_paths or VBA_MODULE_PATHS)]
    stale_modules = []
    addin_mtime_ns = resolved_addin_path.stat().st_mtime_ns
    for module_path in source_modules:
        if not module_path.exists():
            continue
        if module_path.stat().st_mtime_ns > addin_mtime_ns:
            stale_modules.append(module_path.name)

    if stale_modules:
        module_list = ', '.join(stale_modules)
        raise NativeWordToolError(
            'native_word_addin_stale',
            'Word AI native add-in dang cu hon source VBA hien tai '
            f'({module_list}). Hay rebuild add-in bang deploy/word_worker_direct_host/build_native_word_addin.ps1 '
            'roi reload/cai lai add-in trong Word truoc khi chay Word AI.',
        )

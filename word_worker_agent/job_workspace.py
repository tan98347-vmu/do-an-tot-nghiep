import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class JobWorkspace:
    root_dir: Path
    temp_dir: Path
    logs_dir: Path
    artifacts_dir: Path
    input_docx_path: Path
    output_docx_path: Path
    plan_json_path: Path
    extracted_text_path: Path
    runtime_stdout_path: Path
    runtime_stderr_path: Path


def build_job_workspace(*, base_dir, slot_label, job_id, create_dirs=True):
    root_dir = Path(base_dir) / slot_label / f'job-{job_id}'
    temp_dir = root_dir / 'temp'
    logs_dir = root_dir / 'logs'
    artifacts_dir = root_dir / 'artifacts'
    if create_dirs:
        temp_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)
        artifacts_dir.mkdir(parents=True, exist_ok=True)
    return JobWorkspace(
        root_dir=root_dir,
        temp_dir=temp_dir,
        logs_dir=logs_dir,
        artifacts_dir=artifacts_dir,
        input_docx_path=temp_dir / 'input.docx',
        output_docx_path=artifacts_dir / 'output.docx',
        plan_json_path=temp_dir / 'plan.json',
        extracted_text_path=artifacts_dir / 'content.txt',
        runtime_stdout_path=logs_dir / 'runtime.stdout.log',
        runtime_stderr_path=logs_dir / 'runtime.stderr.log',
    )


def clear_job_workspace(workspace):
    shutil.rmtree(workspace.root_dir, ignore_errors=True)

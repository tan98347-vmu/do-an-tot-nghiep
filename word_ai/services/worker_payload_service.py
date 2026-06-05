from pathlib import Path


def build_worker_job_context(job):
    output_file = job.document.output_file
    source_file_path = ''
    source_file_name = ''
    if output_file:
        source_file_name = Path(output_file.name).name
        try:
            source_file_path = output_file.path
        except (NotImplementedError, ValueError):
            source_file_path = ''

    return {
        'document_title': job.document.title,
        'document_version_number': job.document.version_number,
        'source_file_name': source_file_name,
        'source_file_path': source_file_path,
        'workspace_name': f'job-{job.id}',
        'edit_mode': job.edit_mode,
        'mcp_session_id': job.mcp_session_id,
        'execution_payload': job.execution_payload,
    }

import json
import mimetypes
import uuid
from pathlib import Path
from urllib import error, request


class BackendClient:
    def __init__(self, *, base_url, worker_token):
        self.base_url = base_url.rstrip('/')
        self.worker_token = worker_token

    def _open_json(self, req, *, timeout):
        try:
            with request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except error.HTTPError as exc:
            detail = exc.read().decode('utf-8', errors='replace').strip()
            if detail:
                raise RuntimeError(f'HTTP {exc.code}: {detail}') from exc
            raise RuntimeError(f'HTTP {exc.code}: {exc.reason}') from exc

    def _post_json(self, path, payload):
        body = json.dumps(payload).encode('utf-8')
        req = request.Request(
            f'{self.base_url}{path}',
            data=body,
            method='POST',
            headers={
                'Content-Type': 'application/json',
                'X-Word-AI-Worker-Token': self.worker_token,
            },
        )
        return self._open_json(req, timeout=30)

    def _build_multipart_body(self, *, fields, file_field_name, file_path, boundary):
        file_name = Path(file_path).name
        content_type = mimetypes.guess_type(file_name)[0] or 'application/octet-stream'
        body = bytearray()

        for key, value in fields.items():
            body.extend(f'--{boundary}\r\n'.encode('utf-8'))
            body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode('utf-8'))
            body.extend(self._serialize_form_value(value).encode('utf-8'))
            body.extend(b'\r\n')

        body.extend(f'--{boundary}\r\n'.encode('utf-8'))
        body.extend(
            f'Content-Disposition: form-data; name="{file_field_name}"; filename="{file_name}"\r\n'.encode('utf-8')
        )
        body.extend(f'Content-Type: {content_type}\r\n\r\n'.encode('utf-8'))
        with open(file_path, 'rb') as file_handle:
            body.extend(file_handle.read())
        body.extend(f'\r\n--{boundary}--\r\n'.encode('utf-8'))
        return bytes(body), content_type

    def _serialize_form_value(self, value):
        if value is None:
            return ''
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=True)
        return str(value)

    def _multipart_request(self, path, fields, file_field_name, file_path):
        boundary = f'----WordAIBoundary{uuid.uuid4().hex}'
        body, _content_type = self._build_multipart_body(
            fields=fields,
            file_field_name=file_field_name,
            file_path=file_path,
            boundary=boundary,
        )

        req = request.Request(
            f'{self.base_url}{path}',
            data=body,
            method='POST',
            headers={
                'Content-Type': f'multipart/form-data; boundary={boundary}',
                'X-Word-AI-Worker-Token': self.worker_token,
            },
        )
        return self._open_json(req, timeout=120)

    def claim_job(self, *, worker_key, slot_label, host_name, metadata=None):
        return self._post_json(
            '/word-ai/workers/claim/',
            {
                'worker_key': worker_key,
                'slot_label': slot_label,
                'host_name': host_name,
                'metadata': metadata or {},
            },
        )

    def heartbeat(self, *, worker_key, slot_label, status, metadata=None, current_job_id=None):
        return self._post_json(
            '/word-ai/workers/heartbeat/',
            {
                'worker_key': worker_key,
                'slot_label': slot_label,
                'status': status,
                'metadata': metadata or {},
                'current_job_id': current_job_id,
            },
        )

    def post_job_event(self, *, job_id, worker_key, step, status='', message='', level='info', payload=None):
        return self._post_json(
            f'/word-ai/jobs/{job_id}/event/',
            {
                'worker_key': worker_key,
                'step': step,
                'status': status,
                'message': message,
                'level': level,
                'payload': payload or {},
            },
        )

    def advance_tool_loop(
        self,
        *,
        job_id,
        worker_key,
        session_id,
        latest_command,
        tool_transcript,
        session_snapshot,
    ):
        return self._post_json(
            f'/word-ai/jobs/{job_id}/tool-loop/advance/',
            {
                'worker_key': worker_key,
                'session_id': session_id,
                'latest_command': latest_command or {},
                'tool_transcript': tool_transcript or [],
                'session_snapshot': session_snapshot or {},
            },
        )

    def advance_mcp_session(
        self,
        *,
        job_id,
        worker_key,
        session_id,
        latest_command,
        tool_transcript,
        session_snapshot,
    ):
        return self.advance_tool_loop(
            job_id=job_id,
            worker_key=worker_key,
            session_id=session_id,
            latest_command=latest_command,
            tool_transcript=tool_transcript,
            session_snapshot=session_snapshot,
        )

    def complete_job(
        self,
        *,
        job_id,
        worker_key,
        output_file_path,
        summary='',
        change_note='',
        content_text='',
        tool_transcript=None,
        verification_summary=None,
        artifact_manifest=None,
        document_checksums=None,
    ):
        return self._multipart_request(
            f'/word-ai/jobs/{job_id}/complete/',
            {
                'worker_key': worker_key,
                'summary': summary,
                'change_note': change_note,
                'content_text': content_text,
                'tool_transcript': tool_transcript or [],
                'verification_summary': verification_summary or {},
                'artifact_manifest': artifact_manifest or {},
                'document_checksums': document_checksums or {},
            },
            'output_file',
            output_file_path,
        )

    def fail_job(
        self,
        *,
        job_id,
        worker_key,
        error_code,
        error_detail='',
        tool_transcript=None,
        verification_summary=None,
        failure_payload=None,
    ):
        return self._post_json(
            f'/word-ai/jobs/{job_id}/fail/',
            {
                'worker_key': worker_key,
                'error_code': error_code,
                'error_detail': error_detail,
                'tool_transcript': tool_transcript or [],
                'verification_summary': verification_summary or {},
                'failure_payload': failure_payload or {},
            },
        )

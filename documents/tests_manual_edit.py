import shutil
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db.models.fields.files import FieldFile
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from word_ai.test_utils import PromptCheckedApiClient

from accounts.models import Company, CompanyStatus, CompanyUserMembership
from accounts.storage_paths import company_storage_slug
from documents.models import Document, DocumentVersion
from documents.manual_edit_models import DocumentManualEditSession
from documents.manual_edit_provider import build_manual_edit_wopi_src


def _build_docx_bytes(*paragraphs):
    import docx as python_docx

    buffer = BytesIO()
    document = python_docx.Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    document.save(buffer)
    return buffer.getvalue()


@override_settings(
    MANUAL_EDIT_PROVIDER='collabora',
    COLLABORA_PUBLIC_URL='http://collabora.test',
)
class DocumentManualEditTests(TestCase):
    def setUp(self):
        self.media_dir = Path(tempfile.mkdtemp(prefix='document-manual-edit-'))
        self.addCleanup(lambda: shutil.rmtree(self.media_dir, ignore_errors=True))
        self.media_override = override_settings(MEDIA_ROOT=str(self.media_dir))
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self._stored_files = {}

        def fake_storage_save(storage, name, content, max_length=None):
            if hasattr(content, 'seek'):
                content.seek(0)
            self._stored_files[name] = content.read()
            if hasattr(content, 'seek'):
                content.seek(0)
            return name

        def fake_field_open(file_field, mode='rb'):
            return BytesIO(self._stored_files.get(file_field.name, b''))

        self.storage_save_patch = patch(
            'django.core.files.storage.filesystem.FileSystemStorage.save',
            new=fake_storage_save,
        )
        self.field_open_patch = patch.object(FieldFile, 'open', new=fake_field_open)
        self.storage_save_patch.start()
        self.field_open_patch.start()
        self.addCleanup(self.storage_save_patch.stop)
        self.addCleanup(self.field_open_patch.stop)

        self.user = User.objects.create_user(username='manual-owner', password='secret')
        self.client = PromptCheckedApiClient(self.user)
        self.document = Document.objects.create(
            title='Manual Edit Target',
            owner=self.user,
            content='Ban dau',
        )
        initial_docx = _build_docx_bytes('Ban dau')
        self.document.output_file.save(
            'manual-target.docx',
            ContentFile(initial_docx),
            save=False,
        )
        self.document.save(update_fields=['output_file'])
        self._stored_files[self.document.output_file.name] = initial_docx

    def _create_session(self):
        response = self.client.post(
            reverse('api:document_manual_edit_session_create', args=[self.document.id]),
            {},
            format='json',
        )
        self.assertIn(response.status_code, {200, 201})
        return response

    def test_create_session_creates_working_copy_and_editor_url(self):
        response = self._create_session()
        self.assertEqual(response.status_code, 201)
        payload = response.data['session']
        self.assertTrue(payload['editor_url'])
        self.assertTrue(payload['is_active'])
        self.assertIsNone(payload['working_copy_updated_at'])
        session = DocumentManualEditSession.objects.get(pk=payload['id'])
        self.assertTrue(bool(session.working_copy_file))
        self.assertEqual(session.status, DocumentManualEditSession.Status.ACTIVE)
        self.assertIsNone(session.working_copy_updated_at)

    def test_second_create_reuses_same_active_session_for_same_user(self):
        first = self._create_session()
        second = self._create_session()
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.data['created_new'])
        self.assertEqual(first.data['session']['id'], second.data['session']['id'])

    def test_provider_status_endpoint_reports_ready(self):
        response = self.client.get(
            reverse('api:document_manual_edit_provider_status'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['provider'], 'collabora')
        self.assertTrue(response.data['is_ready'])
        self.assertEqual(response.data['code'], 'ready')

    @override_settings(COLLABORA_PUBLIC_URL='http://127.0.0.1:8888')
    @patch(
        'documents.manual_edit_provider.urlopen',
        side_effect=HTTPError(
            url='http://127.0.0.1:8888/hosting/discovery',
            code=502,
            msg='Bad Gateway',
            hdrs=None,
            fp=None,
        ),
    )
    def test_provider_status_reports_unreachable_loopback_editor(
        self,
        _mock_urlopen,
    ):
        response = self.client.get(
            reverse('api:document_manual_edit_provider_status'),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['is_ready'])
        self.assertEqual(response.data['code'], 'collabora_runtime_unreachable')
        self.assertIn('HTTP 502', response.data['detail'])

    @override_settings(COLLABORA_PUBLIC_URL='http://127.0.0.1:8888')
    @patch(
        'documents.manual_edit_provider.urlopen',
        side_effect=HTTPError(
            url='http://127.0.0.1:8888/hosting/discovery',
            code=502,
            msg='Bad Gateway',
            hdrs=None,
            fp=None,
        ),
    )
    def test_create_session_fails_fast_when_loopback_editor_is_down(
        self,
        _mock_urlopen,
    ):
        response = self.client.post(
            reverse('api:document_manual_edit_session_create', args=[self.document.id]),
            {},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('HTTP 502', response.data['detail'])

    @override_settings(MANUAL_EDIT_WOPI_SRC_BASE_URL='http://host.docker.internal:8000')
    def test_wopi_src_can_use_explicit_public_base_url(self):
        create_response = self._create_session()
        session_id = create_response.data['session']['id']
        session = DocumentManualEditSession.objects.get(pk=session_id)

        request = create_response.wsgi_request
        wopi_src = build_manual_edit_wopi_src(session, request)

        self.assertTrue(wopi_src.startswith('http://host.docker.internal:8000/'))
        self.assertIn('/api/documents/manual-edit/wopi/files/', wopi_src)
        self.assertFalse(wopi_src.endswith('/'))

    def test_wopi_src_has_no_trailing_slash_for_collabora_contents_resolution(self):
        create_response = self._create_session()
        session_id = create_response.data['session']['id']
        session = DocumentManualEditSession.objects.get(pk=session_id)

        request = create_response.wsgi_request
        wopi_src = build_manual_edit_wopi_src(session, request)

        self.assertIn(f'/api/documents/manual-edit/wopi/files/{session.wopi_file_id}', wopi_src)
        self.assertFalse(wopi_src.endswith('/'))

    @override_settings(
        COLLABORA_PUBLIC_URL='http://127.0.0.1:8888',
        MANUAL_EDIT_WOPI_SRC_BASE_URL='',
    )
    def test_wopi_src_falls_back_to_host_docker_internal_for_local_windows_default(self):
        create_response = self._create_session()
        session_id = create_response.data['session']['id']
        session = DocumentManualEditSession.objects.get(pk=session_id)

        request = create_response.wsgi_request
        with patch('documents.manual_edit_provider.os.name', 'nt'):
            wopi_src = build_manual_edit_wopi_src(session, request)

        self.assertTrue(wopi_src.startswith('http://host.docker.internal:8888/'))

    @override_settings(
        COLLABORA_PUBLIC_URL='https://manual-test.ngrok-free.dev',
        MANUAL_EDIT_WOPI_SRC_BASE_URL='',
    )
    def test_wopi_src_falls_back_to_host_docker_internal_for_ngrok_single_domain_on_windows(self):
        create_response = self._create_session()
        session_id = create_response.data['session']['id']
        session = DocumentManualEditSession.objects.get(pk=session_id)

        request = create_response.wsgi_request
        with patch('documents.manual_edit_provider.os.name', 'nt'):
            wopi_src = build_manual_edit_wopi_src(session, request)

        self.assertTrue(wopi_src.startswith('http://host.docker.internal:8888/'))

    @override_settings(MANUAL_EDIT_WOPI_SRC_BASE_URL='')
    def test_wopi_src_uses_forwarded_host_when_available(self):
        create_response = self._create_session()
        session_id = create_response.data['session']['id']
        session = DocumentManualEditSession.objects.get(pk=session_id)

        request = create_response.wsgi_request
        request.META['HTTP_X_FORWARDED_HOST'] = 'proxy.example.test:9443'
        request.META['HTTP_X_FORWARDED_PROTO'] = 'https'

        with patch('documents.manual_edit_provider.os.name', 'posix'):
            wopi_src = build_manual_edit_wopi_src(session, request)

        self.assertTrue(wopi_src.startswith('https://proxy.example.test:9443/'))

    def test_wopi_file_endpoint_accepts_no_slash_without_redirect(self):
        create_response = self._create_session()
        session_id = create_response.data['session']['id']
        session = DocumentManualEditSession.objects.get(pk=session_id)

        response = self.client.get(
            reverse('api:document_manual_edit_wopi_file', args=[session.wopi_file_id]),
            {'access_token': session.access_token},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_wopi_file_endpoint_keeps_legacy_slash_alias_working(self):
        create_response = self._create_session()
        session_id = create_response.data['session']['id']
        session = DocumentManualEditSession.objects.get(pk=session_id)

        response = self.client.get(
            f'/api/documents/manual-edit/wopi/files/{session.wopi_file_id}/',
            {'access_token': session.access_token},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_wopi_contents_endpoint_accepts_no_slash_without_redirect(self):
        create_response = self._create_session()
        session_id = create_response.data['session']['id']
        session = DocumentManualEditSession.objects.get(pk=session_id)

        response = self.client.get(
            reverse('api:document_manual_edit_wopi_contents', args=[session.wopi_file_id]),
            {'access_token': session.access_token},
        )

        self.assertEqual(response.status_code, 200)

    def test_wopi_contents_endpoint_keeps_legacy_slash_alias_working(self):
        create_response = self._create_session()
        session_id = create_response.data['session']['id']
        session = DocumentManualEditSession.objects.get(pk=session_id)

        response = self.client.get(
            f'/api/documents/manual-edit/wopi/files/{session.wopi_file_id}/contents/',
            {'access_token': session.access_token},
        )

        self.assertEqual(response.status_code, 200)

    def test_heartbeat_extends_active_session_expiry(self):
        create_response = self._create_session()
        session_id = create_response.data['session']['id']
        session = DocumentManualEditSession.objects.get(pk=session_id)
        initial_expiry = session.expires_at

        response = self.client.post(
            reverse('api:document_manual_edit_session_heartbeat', args=[session_id]),
            {},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertGreater(session.expires_at, initial_expiry)
        self.assertTrue(response.data['is_active'])

    def test_wopi_put_updates_working_copy_sync_timestamp(self):
        create_response = self._create_session()
        session_id = create_response.data['session']['id']
        session = DocumentManualEditSession.objects.get(pk=session_id)
        self.assertIsNone(session.working_copy_updated_at)

        put_response = self.client.post(
            reverse('api:document_manual_edit_wopi_contents', args=[session.wopi_file_id]),
            data=_build_docx_bytes('Noi dung vua duoc dong bo'),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            QUERY_STRING=f'access_token={session.access_token}',
            HTTP_X_WOPI_OVERRIDE='PUT',
        )
        self.assertEqual(put_response.status_code, 200)

        detail_response = self.client.get(
            reverse('api:document_manual_edit_session_detail', args=[session_id]),
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertIsNotNone(detail_response.data['working_copy_updated_at'])

        session.refresh_from_db()
        self.assertIsNotNone(session.working_copy_updated_at)

    def test_expired_session_releases_lock_and_allows_new_session(self):
        create_response = self._create_session()
        old_session_id = create_response.data['session']['id']
        session = DocumentManualEditSession.objects.get(pk=old_session_id)
        session.expires_at = timezone.now() - timezone.timedelta(seconds=5)
        session.save(update_fields=['expires_at', 'updated_at'])

        retry_response = self.client.post(
            reverse('api:document_manual_edit_session_create', args=[self.document.id]),
            {},
            format='json',
        )
        self.assertEqual(retry_response.status_code, 201)
        self.assertNotEqual(retry_response.data['session']['id'], old_session_id)
        session.refresh_from_db()
        self.assertEqual(session.status, DocumentManualEditSession.Status.EXPIRED)

    @patch('documents.manual_edit_services.schedule_document_preview_regeneration')
    def test_finish_session_creates_new_document_version(self, schedule_preview):
        create_response = self._create_session()
        session_id = create_response.data['session']['id']
        session = DocumentManualEditSession.objects.get(pk=session_id)

        wopi_response = self.client.post(
            reverse('api:document_manual_edit_wopi_contents', args=[session.wopi_file_id]),
            data=_build_docx_bytes('Noi dung da sua', 'Dong thu hai'),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            QUERY_STRING=f'access_token={session.access_token}',
            HTTP_X_WOPI_OVERRIDE='PUT',
        )
        self.assertEqual(wopi_response.status_code, 200)

        finish_response = self.client.post(
            reverse('api:document_manual_edit_session_finish', args=[session_id]),
            {'change_note': 'Manual finish'},
            format='json',
        )
        self.assertEqual(finish_response.status_code, 200)
        self.document.refresh_from_db()
        session.refresh_from_db()
        self.assertEqual(self.document.version_number, 2)
        self.assertIn('Noi dung da sua', self.document.content)
        self.assertEqual(DocumentVersion.objects.filter(document=self.document).count(), 1)
        self.assertEqual(session.status, DocumentManualEditSession.Status.FINISHED)
        self.assertFalse(bool(session.working_copy_file))
        schedule_preview.assert_called_once()

    def test_finish_session_rejects_unchanged_working_copy(self):
        create_response = self._create_session()
        session_id = create_response.data['session']['id']

        finish_response = self.client.post(
            reverse('api:document_manual_edit_session_finish', args=[session_id]),
            {'change_note': 'No-op finish'},
            format='json',
        )

        self.assertEqual(finish_response.status_code, 400)
        self.assertIn('Khong co thay doi moi nao', finish_response.data['detail'])
        self.document.refresh_from_db()
        session = DocumentManualEditSession.objects.get(pk=session_id)
        self.assertEqual(self.document.version_number, 1)
        self.assertEqual(DocumentVersion.objects.filter(document=self.document).count(), 0)
        self.assertEqual(session.status, DocumentManualEditSession.Status.ACTIVE)

    def test_wopi_unlock_still_succeeds_after_session_finished(self):
        create_response = self._create_session()
        session_id = create_response.data['session']['id']
        session = DocumentManualEditSession.objects.get(pk=session_id)
        session.lock_token = 'cool-lock-token'
        session.save(update_fields=['lock_token', 'updated_at'])

        self.client.post(
            reverse('api:document_manual_edit_wopi_contents', args=[session.wopi_file_id]),
            data=_build_docx_bytes('Noi dung da sua de unlock'),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            QUERY_STRING=f'access_token={session.access_token}',
            HTTP_X_WOPI_OVERRIDE='PUT',
            HTTP_X_WOPI_LOCK='cool-lock-token',
        )

        finish_response = self.client.post(
            reverse('api:document_manual_edit_session_finish', args=[session_id]),
            {'change_note': 'Finish before unlock'},
            format='json',
        )
        self.assertEqual(finish_response.status_code, 200)

        unlock_response = self.client.post(
            reverse('api:document_manual_edit_wopi_file', args=[session.wopi_file_id]),
            data={},
            QUERY_STRING=f'access_token={session.access_token}',
            HTTP_X_WOPI_OVERRIDE='UNLOCK',
            HTTP_X_WOPI_LOCK='cool-lock-token',
        )
        self.assertEqual(unlock_response.status_code, 200)

    def test_cancel_session_keeps_current_document_unchanged(self):
        create_response = self._create_session()
        session_id = create_response.data['session']['id']
        cancel_response = self.client.post(
            reverse('api:document_manual_edit_session_cancel', args=[session_id]),
            {},
            format='json',
        )
        self.assertEqual(cancel_response.status_code, 200)
        self.document.refresh_from_db()
        session = DocumentManualEditSession.objects.get(pk=session_id)
        self.assertEqual(self.document.version_number, 1)
        self.assertEqual(DocumentVersion.objects.filter(document=self.document).count(), 0)
        self.assertEqual(session.status, DocumentManualEditSession.Status.CANCELLED)
        self.assertFalse(bool(session.working_copy_file))

    def test_active_manual_edit_blocks_word_ai_job_creation(self):
        self._create_session()
        response = self.client.post(
            reverse('api:word_ai_job_list_create'),
            {
                'document_id': self.document.id,
                'instruction': 'Try to edit while manual editor is active.',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_active_manual_edit_blocks_version_restore(self):
        version = DocumentVersion.objects.create(
            document=self.document,
            version_number=1,
            content='Noi dung cu',
            created_by=self.user,
        )
        version.output_file.save(
            'older.docx',
            ContentFile(_build_docx_bytes('Noi dung cu')),
            save=False,
        )
        version.save(update_fields=['output_file'])
        self._create_session()
        response = self.client.post(
            reverse('api:document_version_restore', args=[self.document.id, version.id]),
        )
        self.assertEqual(response.status_code, 409)

    def test_wopi_contents_blocks_cross_company_working_copy_prefix(self):
        company_a = Company.objects.create(code='manual-a', name='Manual A', status=CompanyStatus.ACTIVE)
        company_b = Company.objects.create(code='manual-b', name='Manual B', status=CompanyStatus.ACTIVE)
        CompanyUserMembership.objects.create(
            company=company_a,
            user=self.user,
            local_username=self.user.username,
            role='company_user',
            is_active=True,
        )
        self.document.company = company_a
        self.document.save(update_fields=['company'])

        create_response = self._create_session()
        session_id = create_response.data['session']['id']
        session = DocumentManualEditSession.objects.get(pk=session_id)
        session.working_copy_file.name = (
            f"companies/{company_storage_slug(company_b)}/manual_edit_working_copies/"
            f"document_{self.document.id}/tampered.docx"
        )
        session.save(update_fields=['working_copy_file', 'updated_at'])

        response = self.client.get(
            reverse('api:document_manual_edit_wopi_contents', args=[session.wopi_file_id]),
            {'access_token': session.access_token},
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn('cong ty khac', str(response.json().get('detail', '')).lower())

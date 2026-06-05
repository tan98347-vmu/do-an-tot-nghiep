import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from documents.models import Document, DocumentVersion


def _fake_storage_save(storage, name, content, max_length=None):
    return name


class DocumentWordAiRegressionTests(TestCase):
    def setUp(self):
        test_root = Path(__file__).resolve().parents[1] / '.codex-tmp'
        test_root.mkdir(parents=True, exist_ok=True)
        self.media_dir = Path(tempfile.mkdtemp(prefix='document-tests-', dir=test_root))
        self.addCleanup(lambda: shutil.rmtree(self.media_dir, ignore_errors=True))
        self.media_override = override_settings(MEDIA_ROOT=str(self.media_dir))
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)

        self.client = APIClient()
        self.user = User.objects.create_user(username='document-owner', password='secret')
        self.client.force_authenticate(self.user)

    def test_document_create_endpoint_still_accepts_basic_payload(self):
        response = self.client.post(
            reverse('api:document_list'),
            {
                'title': 'Regression Draft',
                'content': 'Initial content',
                'status': 'draft',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Document.objects.get(pk=response.data['id']).title, 'Regression Draft')

    @patch('api.views.documents.schedule_document_preview_regeneration')
    def test_document_version_restore_creates_new_version_and_requeues_preview(self, schedule_preview):
        document = Document.objects.create(
            title='Restore Me',
            owner=self.user,
            content='Current content',
        )
        document.output_file = 'generated_docs/current.docx'
        document.save(update_fields=['output_file'])
        version = DocumentVersion.objects.create(
            document=document,
            version_number=1,
            content='Original content',
            change_note='Initial version',
            created_by=self.user,
        )
        version.output_file = 'doc_versions/original.docx'
        version.save(update_fields=['output_file'])

        with patch('django.db.models.fields.files.FieldFile.open', return_value=BytesIO(b'original-docx')):
            with patch('django.core.files.storage.filesystem.FileSystemStorage.save', new=_fake_storage_save):
                response = self.client.post(reverse('api:document_version_restore', args=[document.id, version.id]))
        self.assertEqual(response.status_code, 200)
        document.refresh_from_db()
        self.assertEqual(document.version_number, 2)
        self.assertEqual(document.content, 'Original content')
        self.assertEqual(DocumentVersion.objects.filter(document=document).count(), 2)
        schedule_preview.assert_called_once()
        self.assertEqual(schedule_preview.call_args.args[0].pk, document.pk)

    @patch('api.views.documents._extract_text_from_docx', return_value='Uploaded content')
    @patch('api.views.documents.schedule_document_preview_regeneration')
    def test_document_upload_requeues_preview_generation(self, schedule_preview, extract_text):
        with patch('django.core.files.storage.filesystem.FileSystemStorage.save', new=_fake_storage_save):
            response = self.client.post(
                reverse('api:document_upload'),
                {
                    'title': 'Upload Me',
                    'docx_file': SimpleUploadedFile(
                        'upload.docx',
                        b'fake-docx-binary',
                        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    ),
                },
                format='multipart',
            )
        self.assertEqual(response.status_code, 201)
        extract_text.assert_called_once()
        schedule_preview.assert_called_once()
        uploaded_document = Document.objects.get(pk=response.data['id'])
        self.assertEqual(schedule_preview.call_args.args[0].pk, uploaded_document.pk)

    @patch('api.views.documents.build_document_preview_pdf')
    def test_document_preview_endpoint_still_streams_pdf(self, build_preview):
        document = Document.objects.create(
            title='Preview Me',
            owner=self.user,
            content='Preview body',
        )
        document.output_file = 'generated_docs/preview.docx'
        document.save(update_fields=['output_file'])
        preview_path = Path(__file__)
        build_preview.return_value = preview_path

        response = self.client.get(reverse('api:document_preview_pdf', args=[document.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(response['X-Document-Preview'], 'pdf')
        self.assertEqual(b''.join(response.streaming_content), preview_path.read_bytes())

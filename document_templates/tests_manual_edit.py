import shutil
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db.models.fields.files import FieldFile
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Company, CompanyStatus, CompanyUserMembership
from accounts.storage_paths import company_storage_slug
from document_templates.manual_edit_models import TemplateManualEditSession
from document_templates.models import DocumentTemplate, TemplateVersion


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
class TemplateManualEditTests(TestCase):
    def setUp(self):
        self.media_dir = Path(tempfile.mkdtemp(prefix='template-manual-edit-'))
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

        self.client = APIClient()
        self.user = User.objects.create_user(
            username='template-owner',
            password='secret',
        )
        self.company = Company.objects.create(
            code='template-manual-edit',
            name='Template Manual Edit Co',
            status=CompanyStatus.ACTIVE,
        )
        CompanyUserMembership.objects.create(
            company=self.company,
            user=self.user,
            local_username='template-owner',
            role='company_admin',
        )
        self.client.force_authenticate(self.user)
        self.template = DocumentTemplate.objects.create(
            title='Mẫu thông báo',
            content='<p>Ban dau</p>',
            owner=self.user,
            company=self.company,
            visibility=DocumentTemplate.VISIBILITY_PRIVATE,
        )

    def _create_session(self):
        response = self.client.post(
            reverse('api:template_manual_edit_session_create', args=[self.template.id]),
            {},
            format='json',
        )
        self.assertIn(response.status_code, {200, 201})
        return response

    def test_create_session_bootstraps_docx_working_copy(self):
        response = self._create_session()

        self.assertEqual(response.status_code, 201)
        payload = response.data['session']
        self.assertTrue(payload['editor_url'])
        self.assertTrue(payload['is_active'])

        self.template.refresh_from_db()
        session = TemplateManualEditSession.objects.get(pk=payload['id'])
        self.assertEqual(self.template.source_type, DocumentTemplate.SOURCE_DOCX)
        self.assertTrue(bool(self.template.docx_file.name))
        self.assertTrue(bool(session.working_copy_file.name))
        normalized_working_copy = session.working_copy_file.name.replace('\\', '/')
        self.assertIn(
            f"companies/{company_storage_slug(self.company)}/manual_edit_working_copies/",
            normalized_working_copy,
        )

    def test_finish_session_updates_template_and_creates_version_snapshot(self):
        create_response = self._create_session()
        session_id = create_response.data['session']['id']
        session = TemplateManualEditSession.objects.get(pk=session_id)
        edited_docx = _build_docx_bytes('Noi dung da sua', 'Bien {{ho_ten}}')

        update_response = self.client.generic(
            'POST',
            reverse('api:template_manual_edit_wopi_contents', args=[session.wopi_file_id])
            + f'?access_token={session.access_token}',
            edited_docx,
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            HTTP_X_WOPI_OVERRIDE='PUT',
        )
        self.assertEqual(update_response.status_code, 200)

        finish_response = self.client.post(
            reverse('api:template_manual_edit_session_finish', args=[session_id]),
            {'change_note': 'Cap nhat bang editor thu cong'},
            format='json',
        )

        self.assertEqual(finish_response.status_code, 200)
        self.template.refresh_from_db()
        session.refresh_from_db()
        self.assertEqual(session.status, TemplateManualEditSession.Status.FINISHED)
        self.assertEqual(self.template.version, '1.1')
        self.assertEqual(self.template.source_type, DocumentTemplate.SOURCE_DOCX)
        self.assertIn('Noi dung da sua', self.template.content)
        self.assertEqual(self.template.versions.count(), 1)
        version = TemplateVersion.objects.get(template=self.template)
        self.assertEqual(version.change_note, 'Cap nhat bang editor thu cong')
        self.assertFalse(bool(session.working_copy_file))

    def test_cancel_session_marks_session_cancelled(self):
        create_response = self._create_session()
        session_id = create_response.data['session']['id']

        cancel_response = self.client.post(
            reverse('api:template_manual_edit_session_cancel', args=[session_id]),
            {},
            format='json',
        )

        self.assertEqual(cancel_response.status_code, 200)
        session = TemplateManualEditSession.objects.get(pk=session_id)
        self.assertEqual(session.status, TemplateManualEditSession.Status.CANCELLED)
        self.assertFalse(session.is_active)

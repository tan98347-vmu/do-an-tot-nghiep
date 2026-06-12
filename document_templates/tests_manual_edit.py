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

    def test_wopi_check_file_info_exposes_postmessage_origin(self):
        """Collabora chi gui App_LoadingStatus/Action_Save_Resp ve host khi
        CheckFileInfo co PostMessageOrigin. Thieu field nay -> bam "Luu & hoan tat"
        bao 'Trinh sua web chua san sang de nhan lenh luu'."""
        create_response = self._create_session()
        session_id = create_response.data['session']['id']
        session = TemplateManualEditSession.objects.get(pk=session_id)

        info = self.client.get(
            reverse('api:template_manual_edit_wopi_file', args=[session.wopi_file_id])
            + f'?access_token={session.access_token}'
        )
        self.assertEqual(info.status_code, 200)
        self.assertIn('PostMessageOrigin', info.json())
        # Mac dinh '*' de Collabora postMessage chac chan toi duoc frame cha trong moi
        # topo deploy (request WOPI la server-to-server nen khong suy ra origin trinh
        # duyet duoc). Host xac thuc theo event.source nen '*' van an toan.
        self.assertEqual(info.json()['PostMessageOrigin'], '*')

    def test_wopi_postmessage_origin_uses_browser_origin_from_create(self):
        """Origin THAT cua trinh duyet (bat tu request tao phien) phai duoc tra ve
        trong CheckFileInfo -> Collabora postMessage dung dich. Day la fix dut diem
        cho loi 'chua san sang nhan lenh luu' tren moi topo deploy."""
        resp = self.client.post(
            reverse('api:template_manual_edit_session_create', args=[self.template.id]),
            {}, format='json', HTTP_ORIGIN='https://app.example.vn',
        )
        self.assertIn(resp.status_code, {200, 201})
        session = TemplateManualEditSession.objects.get(pk=resp.data['session']['id'])
        self.assertEqual(session.post_message_origin, 'https://app.example.vn')

        info = self.client.get(
            reverse('api:template_manual_edit_wopi_file', args=[session.wopi_file_id])
            + f'?access_token={session.access_token}'
        )
        self.assertEqual(info.json()['PostMessageOrigin'], 'https://app.example.vn')

    @override_settings(MANUAL_EDIT_POSTMESSAGE_ORIGIN='https://aiagentvmu.id.vn')
    def test_wopi_postmessage_origin_can_be_pinned(self):
        create_response = self._create_session()
        session = TemplateManualEditSession.objects.get(
            pk=create_response.data['session']['id']
        )
        info = self.client.get(
            reverse('api:template_manual_edit_wopi_file', args=[session.wopi_file_id])
            + f'?access_token={session.access_token}'
        )
        self.assertEqual(info.json()['PostMessageOrigin'], 'https://aiagentvmu.id.vn')

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


@override_settings(
    MANUAL_EDIT_PROVIDER='collabora',
    COLLABORA_PUBLIC_URL='http://collabora.test',
)
class TemplateManualEditDoesNotResetGroupApprovalTests(TemplateManualEditTests):
    """Thanh vien sua mau chia se nhom bang trinh sua thu cong -> KHONG duoc reset
    trang thai duyet ve pending_leader (loi 'mau bien mat khoi tab Mau phong ban')."""

    def setUp(self):
        super().setUp()
        from accounts.models import UserGroup, UserGroupMembership
        from sharing import services

        self.group = UserGroup.objects.create(name='Phong ky thuat', company=self.company)
        # Chu so huu mau (self.user) la TRUONG NHOM
        UserGroupMembership.objects.create(
            group=self.group, user=self.user, role=UserGroupMembership.ROLE_LEADER,
        )
        self.member = User.objects.create_user(username='kt-member', password='secret')
        CompanyUserMembership.objects.create(
            company=self.company, user=self.member, local_username='kt-member', role='member',
        )
        UserGroupMembership.objects.create(
            group=self.group, user=self.member, role=UserGroupMembership.ROLE_MEMBER,
        )
        # Truong nhom chia se mau cho nhom voi toan quyen -> grant active ngay
        services.create_grant(
            resource=self.template, scope='group', permission_level='delete',
            target_group=self.group, actor=self.user,
        )
        self.template.refresh_from_db()

    def test_member_manual_edit_finish_keeps_group_approval(self):
        from document_templates.models import STATUS_APPROVED
        from sharing import services

        # Tien dieu kien: sau khi chia se, mau da approved + visibility group
        self.assertEqual(self.template.status, STATUS_APPROVED)
        self.assertEqual(self.template.visibility, DocumentTemplate.VISIBILITY_GROUP)
        self.assertTrue(services.can_view(self.member, self.template))

        # Thanh vien mo phien sua thu cong
        member_client = APIClient()
        member_client.force_authenticate(self.member)
        create_resp = member_client.post(
            reverse('api:template_manual_edit_session_create', args=[self.template.id]),
            {}, format='json',
        )
        self.assertIn(create_resp.status_code, {200, 201}, create_resp.content)
        session_id = create_resp.data['session']['id']
        session = TemplateManualEditSession.objects.get(pk=session_id)

        # Editor luu noi dung moi vao working copy (WOPI PUT)
        edited = _build_docx_bytes('Noi dung thanh vien sua', 'Bien {{x}}')
        put_resp = member_client.generic(
            'POST',
            reverse('api:template_manual_edit_wopi_contents', args=[session.wopi_file_id])
            + f'?access_token={session.access_token}',
            edited,
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            HTTP_X_WOPI_OVERRIDE='PUT',
        )
        self.assertEqual(put_resp.status_code, 200)

        # Thanh vien bam "Luu & hoan tat"
        finish_resp = member_client.post(
            reverse('api:template_manual_edit_session_finish', args=[session_id]),
            {'change_note': 'thanh vien chinh sua'}, format='json',
        )
        self.assertEqual(finish_resp.status_code, 200, finish_resp.content)

        self.template.refresh_from_db()
        # CHINH: status KHONG duoc quay ve pending_leader
        self.assertEqual(
            self.template.status, STATUS_APPROVED,
            'BUG: sua noi dung khien mau bi reset ve cho-truong-nhom-duyet',
        )
        self.assertEqual(self.template.visibility, DocumentTemplate.VISIBILITY_GROUP)
        # Thanh vien (va ca nhom) van xem duoc
        self.assertTrue(services.can_view(self.member, self.template))

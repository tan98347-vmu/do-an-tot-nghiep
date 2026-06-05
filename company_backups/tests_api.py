import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.company_services import create_company_user
from accounts.models import Company, CompanyRole, CompanyStatus
from company_backups.models import KIND_MANUAL, STATUS_RESTORED
from company_backups.services.manager import create_backup
from company_backups.services.password import ensure_settings, set_backup_password
from company_backups.services.restore import restore_company_zip


class CompanyBackupApiTests(TestCase):
    def setUp(self):
        super().setUp()
        self.media_root = Path('media') / f'test_company_backups_{uuid4().hex}'
        self.media_root.mkdir(parents=True, exist_ok=True)
        self.temp_root = self.media_root / f'tmp_{uuid4().hex}'
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self.settings_override = override_settings(MEDIA_ROOT=str(self.media_root))
        self.settings_override.enable()
        self.original_tempdir = tempfile.tempdir
        tempfile.tempdir = str(self.temp_root)
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(lambda: shutil.rmtree(self.media_root, ignore_errors=True))
        self.addCleanup(lambda: shutil.rmtree(self.temp_root, ignore_errors=True))
        self.addCleanup(self._restore_tempdir)
        self._tmp_counter = 0
        self.manager_mkdtemp_patch = patch(
            'company_backups.services.manager.tempfile.mkdtemp',
            side_effect=self._workspace_mkdtemp,
        )
        self.restore_mkdtemp_patch = patch(
            'company_backups.services.restore.tempfile.mkdtemp',
            side_effect=self._workspace_mkdtemp,
        )
        self.manager_mkdtemp_patch.start()
        self.restore_mkdtemp_patch.start()
        self.addCleanup(self.manager_mkdtemp_patch.stop)
        self.addCleanup(self.restore_mkdtemp_patch.stop)

        self.company = Company.objects.create(
            code='company-a',
            name='Company A',
            status=CompanyStatus.ACTIVE,
        )
        self.admin = create_company_user(
            company=self.company,
            local_username='admin_a',
            email='admin-a@example.com',
            password='secret12345',
            role=CompanyRole.COMPANY_ADMIN,
            full_name='Admin A',
        )
        settings_obj = ensure_settings(self.company)
        set_backup_password(settings_obj, 'backup-pass-123')
        self.client.force_login(self.admin.user)

    def _restore_tempdir(self):
        tempfile.tempdir = self.original_tempdir

    def _workspace_mkdtemp(self, prefix='tmp', dir=None):
        self._tmp_counter += 1
        path = self.temp_root / f'{prefix}{self._tmp_counter}'
        path.mkdir(parents=True, exist_ok=False)
        return str(path)

    def _create_password_encrypted_backup(self):
        backup = create_backup(
            company=self.company,
            components=['ai_config'],
            kind=KIND_MANUAL,
            user=self.admin.user,
            async_run=False,
            password='backup-pass-123',
        )
        self.assertTrue(backup.is_encrypted)
        return backup

    def test_company_admin_can_download_password_encrypted_backup(self):
        backup = self._create_password_encrypted_backup()

        response = self.client.get(
            reverse('api:cb_download', kwargs={'pk': backup.pk}),
            HTTP_X_BACKUP_PASSWORD='backup-pass-123',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/zip')
        self.assertTrue(b''.join(response.streaming_content).startswith(b'PK'))

    def test_backup_create_service_emits_detailed_logs(self):
        with self.assertLogs('company_backups', level='INFO') as captured:
            backup = self._create_password_encrypted_backup()

        output = '\n'.join(captured.output)
        self.assertIn('create_backup record created', output)
        self.assertIn(f'backup_id={backup.pk}', output)
        self.assertIn('backup build pipeline finished', output)

    def test_company_admin_can_restore_password_encrypted_backup(self):
        backup = self._create_password_encrypted_backup()

        response = self.client.post(
            reverse('api:cb_restore', kwargs={'pk': backup.pk}),
            data={'password': 'backup-pass-123'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        backup.refresh_from_db()
        self.assertEqual(backup.status, STATUS_RESTORED)

    def test_backup_restore_logs_visible_from_view_and_service(self):
        backup = self._create_password_encrypted_backup()

        with self.assertLogs('api.views.company_backups', level='INFO') as captured_view:
            response = self.client.post(
                reverse('api:cb_restore', kwargs={'pk': backup.pk}),
                data={'password': 'backup-pass-123'},
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200, response.content)
        view_output = '\n'.join(captured_view.output)
        self.assertIn('backup restore requested', view_output)
        self.assertIn('backup restore completed', view_output)

        backup = self._create_password_encrypted_backup()
        with self.assertLogs('company_backups', level='INFO') as captured_service:
            restored = restore_company_zip(
                company=self.company,
                backup=backup,
                user=self.admin.user,
                password='backup-pass-123',
            )
        self.assertTrue(restored)
        service_output = '\n'.join(captured_service.output)
        self.assertIn('restore started', service_output)
        self.assertIn('restore completed', service_output)

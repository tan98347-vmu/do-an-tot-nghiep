# Chức năng web liên quan: Hồ sơ cá nhân và Tài khoản, phòng ban và nhóm.
# Vai trò backend trong luồng: Tệp này giữ phần logic backend dùng chung cho hồ sơ cá nhân, tài khoản, phòng ban, nhóm và phân quyền truy cập, để các flow ở màn Hồ sơ cá nhân, màn đăng nhập/đăng ký và các dialog quản trị tài khoản, phòng ban, nhóm không phải lặp lại cùng một rule ở nhiều nơi.
# Đầu vào/đầu ra chính: Giữ các helper, cấu hình và rule backend dùng lại ở nhiều flow khác nhau.
# Người dùng sẽ thấy trên web: Người dùng sẽ thấy dữ liệu, badge trạng thái, quyền nút và thông báo trên các chức năng Hồ sơ cá nhân và Tài khoản, phòng ban và nhóm thay đổi đúng theo kết quả nghiệp vụ.

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from accounts.company_services import create_company_user
from accounts.models import Company, CompanyAIConfig, CompanyRole, CompanyStatus
from document_templates.models import DocumentTemplate

# [Web] `AuthProfileApiTests` gom một cụm xử lý backend dùng chung cho nhóm màn Hồ sơ, tài khoản và quản trị người dùng.

class AuthProfileApiTests(TestCase):
    # [Web] `setUp` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Hồ sơ, tài khoản và quản trị người dùng đang cần.

    def setUp(self):
        self.company = Company.objects.create(
            code='profile-company',
            name='Profile Company',
            status=CompanyStatus.ACTIVE,
        )
        self.bootstrap = create_company_user(
            company=self.company,
            local_username='employee_user',
            password='secret123',
            email='employee@example.com',
            role=CompanyRole.COMPANY_USER,
            full_name='Employee User',
        )
        self.user = self.bootstrap.user
        self.user.profile.ma_nhan_vien = 'NV001'
        self.user.profile.save(update_fields=['ma_nhan_vien'])
        self.template = DocumentTemplate.objects.create(
            owner=self.user,
            title='Mau don co bien',
            description='',
            content='<p>{{ho_ten}}</p><p>{{ten_cong_ty}}</p>',
            source_type=DocumentTemplate.SOURCE_MANUAL,
            status='approved',
            visibility='private',
            company=self.company,
        )

    # [Web] `test_login_accepts_employee_code` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Hồ sơ, tài khoản và quản trị người dùng đang cần.

    def test_login_accepts_employee_code(self):
        response = self.client.post(
            reverse('api:login'),
            data={
                'identifier': 'NV001',
                'password': 'secret123',
                'login_scope': 'company',
                'company_id': self.company.pk,
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload['user']['username'], 'employee_user')

    # [Web] `test_me_patch_rejects_invalid_phone` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Hồ sơ, tài khoản và quản trị người dùng đang cần.

    def test_me_patch_rejects_invalid_phone(self):
        self.client.force_login(self.user)

        response = self.client.patch(
            reverse('api:me'),
            data={'so_dien_thoai': '09abc12345'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn('so_dien_thoai', response.json())

    # [Web] `test_me_patch_saves_phone_and_address` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Hồ sơ, tài khoản và quản trị người dùng đang cần.

    def test_me_patch_saves_phone_and_address(self):
        self.client.force_login(self.user)

        response = self.client.patch(
            reverse('api:me'),
            data={
                'so_dien_thoai': '+84 912 345 678',
                'dia_chi': '123 Duong ABC, Quan 1',
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile.so_dien_thoai, '84912345678')
        self.assertEqual(self.user.profile.dia_chi, '123 Duong ABC, Quan 1')

    def test_me_patch_saves_and_replaces_aliases(self):
        self.client.force_login(self.user)

        create_response = self.client.patch(
            reverse('api:me'),
            data={
                'aliases': [
                    {'alias': 'Sep Lon', 'is_primary_hint': True},
                    {'alias': 'Chi Van Thu'},
                ],
            },
            content_type='application/json',
        )

        self.assertEqual(create_response.status_code, 200, create_response.content)
        self.user.refresh_from_db()
        aliases = list(
            self.user.aliases.order_by('-is_primary_hint', 'alias').values_list(
                'alias',
                'normalized_alias',
                'is_primary_hint',
            )
        )
        self.assertEqual(
            aliases,
            [
                ('Sep Lon', 'sep lon', True),
                ('Chi Van Thu', 'chi van thu', False),
            ],
        )
        self.assertEqual(len(create_response.json()['profile']['aliases']), 2)

        replace_response = self.client.patch(
            reverse('api:me'),
            data={
                'aliases': [
                    {'alias': 'Chi Van Thu', 'is_primary_hint': True},
                ],
            },
            content_type='application/json',
        )

        self.assertEqual(replace_response.status_code, 200, replace_response.content)
        self.user.refresh_from_db()
        self.assertEqual(self.user.aliases.count(), 1)
        alias = self.user.aliases.get()
        self.assertEqual(alias.alias, 'Chi Van Thu')
        self.assertTrue(alias.is_primary_hint)

    def test_me_patch_rejects_duplicate_aliases_after_normalize(self):
        self.client.force_login(self.user)

        response = self.client.patch(
            reverse('api:me'),
            data={
                'aliases': [
                    {'alias': 'Tro ly Sep'},
                    {'alias': 'tro-ly sep'},
                ],
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn('aliases', response.json())

    @patch('ai_engine.rag_engine.get_llm')
    def test_prefill_profile_recreates_missing_profile_instead_of_500(self, get_llm_mock):
        class _Response:
            content = '{"ho_ten": "Employee User"}'

        class _Llm:
            def invoke(self, _messages):
                return _Response()

        get_llm_mock.return_value = _Llm()
        self.user.profile.delete()
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('api:ai_doc_prefill_profile'),
            data={'template_id': self.template.pk},
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.user.refresh_from_db()
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertEqual(response.json()['variables']['ho_ten'], 'Employee User')

    @patch('ai_engine.rag_engine.get_llm')
    def test_prefill_company_handles_missing_profile_without_server_error(self, get_llm_mock):
        class _Response:
            content = '{"ten_cong_ty": "Profile Company"}'

        class _Llm:
            def invoke(self, _messages):
                return _Response()

        get_llm_mock.return_value = _Llm()
        CompanyAIConfig.objects.update_or_create(
            company=self.company,
            defaults={'company_context': 'Ten cong ty: Profile Company'},
        )
        self.user.profile.delete()
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('api:ai_doc_prefill_company'),
            data={'template_id': self.template.pk},
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['variables']['ten_cong_ty'], 'Profile Company')

    @patch('api.views.ai_doc._extract_variables_from_source_text')
    @patch('api.views.ai_doc._extract_text_from_pdf_with_cloud_ocr')
    @patch('ai_engine.rag_engine.extract_pdf_text')
    def test_extract_pdf_falls_back_to_cloud_ocr_for_scan_pdf(
        self,
        extract_pdf_text_mock,
        pdf_cloud_ocr_mock,
        extract_variables_mock,
    ):
        extract_pdf_text_mock.return_value = ''
        pdf_cloud_ocr_mock.return_value = 'Cong hoa xa hoi chu nghia Viet Nam'
        extract_variables_mock.return_value = {'ho_ten': 'Employee User'}
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('api:ai_doc_extract_pdf'),
            data={
                'template_id': self.template.pk,
                'pdf_file': SimpleUploadedFile('scan.pdf', b'%PDF-scan%', content_type='application/pdf'),
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['variables']['ho_ten'], 'Employee User')
        pdf_cloud_ocr_mock.assert_called_once()
        extract_variables_mock.assert_called_once()

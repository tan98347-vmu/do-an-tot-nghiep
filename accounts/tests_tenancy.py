from unittest.mock import Mock, patch

from django.db.utils import ProgrammingError
from django.test import TestCase

from accounts.company_services import create_company_user
from accounts.models import Company, CompanyAIConfig, CompanyRole, CompanyStatus, Department
from accounts.tenancy import (
    build_effective_ai_context,
    build_effective_company_context,
    build_employee_profile_context,
    is_platform_admin,
)
from api.views.ai_doc import _resolve_ocr_model


class MultiCompanyTenancyContextTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            code='tenant-context',
            name='Tenant Context Company',
            status=CompanyStatus.ACTIVE,
            company_context='Cong ty chuyen xu ly van ban noi bo va ky so.',
        )
        self.department = Department.objects.create(
            company=self.company,
            code='HC',
            name='Hanh Chinh',
        )
        self.bootstrap = create_company_user(
            company=self.company,
            local_username='employee_ctx',
            email='employee-ctx@example.com',
            password='secret12345',
            role=CompanyRole.COMPANY_USER,
            full_name='Nguyen Van Context',
            department=self.department,
            profile_data={
                'age_years': 31,
                'so_yeu_ly_lich': 'Nhan vien phu trach nghiep vu hop dong va quan ly ho so.',
                'ma_nhan_vien': 'CTX-001',
                'chuc_danh': 'Chuyen Vien',
            },
        )
        self.config = CompanyAIConfig.seed_defaults(self.company)
        self.config.company_context = self.company.company_context
        self.config.ocr_model = 'qwen3-vl:7b'
        self.config.image_ocr_model = 'qwen3-vl:235b-cloud'
        self.config.save(update_fields=['company_context', 'ocr_model', 'image_ocr_model', 'updated_at'])

    def test_build_employee_profile_context_includes_department_and_profile(self):
        text = build_employee_profile_context(self.bootstrap.user)

        self.assertIn('Context Nguyen Van', text)
        self.assertIn('Ten dang nhap: employee_ctx', text)
        self.assertIn('Tuoi: 31', text)
        self.assertIn('Chuc danh: Chuyen Vien', text)
        self.assertIn('Ma nhan vien: CTX-001', text)
        self.assertIn('Phong ban: Hanh Chinh', text)
        self.assertIn('Ho so nhan su: Nhan vien phu trach nghiep vu hop dong va quan ly ho so.', text)

    def test_build_effective_ai_context_includes_company_and_employee_context(self):
        text = build_effective_ai_context(user=self.bootstrap.user)

        self.assertIn('NGU CANH CONG TY:', text)
        self.assertIn('Cong ty chuyen xu ly van ban noi bo va ky so.', text)
        self.assertIn('HO SO NHAN VIEN:', text)
        self.assertIn('Context Nguyen Van', text)
        self.assertIn('Phong ban: Hanh Chinh', text)

    def test_build_effective_company_context_prefers_company_ai_config(self):
        self.company.company_context = 'Ngu canh company config moi.'
        self.company.save(update_fields=['company_context'])
        self.config.company_context = 'Ngu canh company config moi.'
        self.config.save(update_fields=['company_context', 'updated_at'])

        text = build_effective_company_context(user=self.bootstrap.user)

        self.assertEqual(text, 'Ngu canh company config moi.')

    def test_resolve_ocr_model_uses_company_ai_config_for_current_user(self):
        model_name = _resolve_ocr_model('test-flow', user=self.bootstrap.user)

        self.assertEqual(model_name, 'qwen3-vl:7b')

    def test_resolve_ocr_model_uses_company_image_ocr_model_for_extract_image_flow(self):
        model_name = _resolve_ocr_model('ai_doc_extract_image', user=self.bootstrap.user)

        self.assertEqual(model_name, 'qwen3-vl:235b-cloud')

    def test_company_admin_superuser_is_not_treated_as_platform_admin(self):
        self.bootstrap.user.is_superuser = True
        self.bootstrap.user.is_staff = True
        self.bootstrap.user.save(update_fields=['is_superuser', 'is_staff'])

        self.assertFalse(is_platform_admin(self.bootstrap.user))

    def test_platform_admin_marker_controls_platform_access(self):
        platform_user = self.bootstrap.user.__class__.objects.create_user(
            username='platform_marker_user',
            password='secret12345',
            email='platform-marker@example.com',
        )
        platform_user.is_staff = True
        platform_user.is_superuser = True
        platform_user.save(update_fields=['is_staff', 'is_superuser'])
        platform_user.profile.is_platform_admin_account = True
        platform_user.profile.save(update_fields=['is_platform_admin_account'])

        self.assertTrue(is_platform_admin(platform_user))

    def test_platform_admin_fallback_uses_membership_when_profile_marker_unavailable(self):
        class FailingProfileUser:
            is_authenticated = True
            is_superuser = True

            @property
            def profile(self):
                raise ProgrammingError('missing column')

        user = FailingProfileUser()

        no_membership_qs = Mock()
        no_membership_qs.exists.return_value = False
        with patch('accounts.tenancy.CompanyUserMembership.objects.filter', return_value=no_membership_qs):
            self.assertTrue(is_platform_admin(user))

        has_membership_qs = Mock()
        has_membership_qs.exists.return_value = True
        with patch('accounts.tenancy.CompanyUserMembership.objects.filter', return_value=has_membership_qs):
            self.assertFalse(is_platform_admin(user))

"""Tests: xoa cung cong ty chi can mat khau platform admin + doi mat khau platform admin."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.company_lifecycle_services import (
    CompanyHardDeleteError,
    hard_delete_company,
)
from accounts.models import Company, CompanyStatus


def _make_platform_admin(username, password):
    user = User.objects.create_user(username=username, password=password)
    profile = user.profile
    profile.is_platform_admin_account = True
    profile.save(update_fields=['is_platform_admin_account'])
    return user


class HardDeleteCompanyTests(TestCase):
    """Xoa cung cong ty chi yeu cau mat khau admin quan tri nen tang."""

    def test_hard_delete_only_needs_platform_password(self):
        admin = _make_platform_admin('padmin', 'secret123')
        company = Company.objects.create(
            code='C1', name='Cong ty 1', status=CompanyStatus.DELETED,
        )
        result = hard_delete_company(
            company,
            platform_admin_user=admin,
            platform_admin_password='secret123',
        )
        self.assertEqual(result.company_code, 'C1')
        self.assertFalse(Company.objects.filter(pk=result.company_id).exists())

    def test_hard_delete_rejects_wrong_platform_password(self):
        admin = _make_platform_admin('padmin2', 'secret123')
        company = Company.objects.create(
            code='C2', name='Cong ty 2', status=CompanyStatus.DELETED,
        )
        with self.assertRaises(CompanyHardDeleteError):
            hard_delete_company(
                company,
                platform_admin_user=admin,
                platform_admin_password='wrong-pass',
            )
        self.assertTrue(Company.objects.filter(pk=company.pk).exists())

    def test_hard_delete_endpoint_without_company_password(self):
        admin = _make_platform_admin('padmin3', 'secret123')
        company = Company.objects.create(
            code='C3', name='Cong ty 3', status=CompanyStatus.DELETED,
        )
        self.client.force_login(admin)
        resp = self.client.post(
            reverse('api:platform_company_hard_delete', args=[company.pk]),
            data={'platform_admin_password': 'secret123'},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertFalse(Company.objects.filter(pk=company.pk).exists())


class PlatformAdminChangePasswordTests(TestCase):
    """Doi mat khau platform admin: can mat khau cu dung."""

    def setUp(self):
        self.admin = _make_platform_admin('padmin_cp', 'oldpass123')
        self.client.force_login(self.admin)
        self.url = reverse('api:platform_admin_change_password')

    def test_change_password_success(self):
        resp = self.client.post(
            self.url,
            data={'old_password': 'oldpass123', 'new_password': 'newpass456'},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('newpass456'))

    def test_change_password_wrong_old(self):
        resp = self.client.post(
            self.url,
            data={'old_password': 'wrong', 'new_password': 'newpass456'},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('oldpass123'))

    def test_change_password_too_short(self):
        resp = self.client.post(
            self.url,
            data={'old_password': 'oldpass123', 'new_password': '123'},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

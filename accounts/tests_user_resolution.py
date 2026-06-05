from django.test import TestCase

from accounts.company_services import create_company_user
from accounts.models import Company, CompanyRole, CompanyStatus, Department, DepartmentMembership, UserAlias
from accounts.user_resolution import (
    resolve_choice_from_candidates,
    resolve_recipient_query,
    search_recipient_candidates,
)


class UserResolutionTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            code='recipient-a',
            name='Recipient A',
            status=CompanyStatus.ACTIVE,
        )
        self.other_company = Company.objects.create(
            code='recipient-b',
            name='Recipient B',
            status=CompanyStatus.ACTIVE,
        )
        self.actor = create_company_user(
            company=self.company,
            local_username='actor',
            password='secret123',
            email='actor@example.com',
            role=CompanyRole.COMPANY_USER,
            full_name='Actor User',
        ).user
        self.recipient_alias = create_company_user(
            company=self.company,
            local_username='lan.office',
            password='secret123',
            email='lan@example.com',
            role=CompanyRole.COMPANY_USER,
            full_name='Tran Thi Lan',
        ).user
        self.recipient_alias.profile.ma_nhan_vien = 'NV-LAN-01'
        self.recipient_alias.profile.save(update_fields=['ma_nhan_vien'])
        UserAlias.objects.create(
            user=self.recipient_alias,
            alias='Chi Lan Van Thu',
            is_primary_hint=True,
        )
        self.recipient_code = create_company_user(
            company=self.company,
            local_username='hoa.hr',
            password='secret123',
            email='hoa@example.com',
            role=CompanyRole.COMPANY_USER,
            full_name='Nguyen Thi Hoa',
        ).user
        self.recipient_code.profile.ma_nhan_vien = 'HR-204'
        self.recipient_code.profile.save(update_fields=['ma_nhan_vien'])
        self.outsider = create_company_user(
            company=self.other_company,
            local_username='outsider',
            password='secret123',
            email='outsider@example.com',
            role=CompanyRole.COMPANY_USER,
            full_name='Tran Thi Lan',
        ).user

    def test_search_recipient_candidates_matches_alias_and_stays_in_company(self):
        candidates = search_recipient_candidates(
            'chi lan van thu',
            company=self.company,
            actor=self.actor,
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]['user_id'], self.recipient_alias.id)
        self.assertEqual(candidates[0]['match_reason'], 'exact_alias')
        self.assertNotIn(self.outsider.id, [item['user_id'] for item in candidates])

    def test_resolve_recipient_query_prefers_employee_code(self):
        result = resolve_recipient_query(
            'HR-204',
            company=self.company,
            actor=self.actor,
        )

        self.assertEqual(result['status'], 'resolved')
        self.assertEqual(result['recipient']['user_id'], self.recipient_code.id)
        self.assertEqual(result['recipient']['match_reason'], 'exact_employee_code')

    def test_resolve_recipient_query_returns_ambiguous_for_same_name(self):
        dept_hr = Department.objects.create(company=self.company, name='Nhan su', code='HR')
        dept_ops = Department.objects.create(company=self.company, name='Van thu', code='OPS')
        minh_one = create_company_user(
            company=self.company,
            local_username='minh.hr',
            password='secret123',
            email='minh.hr@example.com',
            role=CompanyRole.COMPANY_USER,
            full_name='Le Van Minh',
        ).user
        minh_two = create_company_user(
            company=self.company,
            local_username='minh.ops',
            password='secret123',
            email='minh.ops@example.com',
            role=CompanyRole.COMPANY_USER,
            full_name='Le Van Minh',
        ).user
        DepartmentMembership.objects.create(department=dept_hr, user=minh_one, is_active=True)
        DepartmentMembership.objects.create(department=dept_ops, user=minh_two, is_active=True)

        result = resolve_recipient_query(
            'Le Van Minh',
            company=self.company,
            actor=self.actor,
        )

        self.assertEqual(result['status'], 'ambiguous')
        self.assertEqual(len(result['candidates']), 2)
        self.assertIn('Ban muon gui cho ai?', result['clarification_prompt'])

    def test_resolve_choice_from_candidates_uses_department_hint(self):
        dept_hr = Department.objects.create(company=self.company, name='Nhan su', code='HR2')
        dept_ops = Department.objects.create(company=self.company, name='Van thu', code='OPS2')
        minh_one = create_company_user(
            company=self.company,
            local_username='minh.hr2',
            password='secret123',
            email='minh.hr2@example.com',
            role=CompanyRole.COMPANY_USER,
            full_name='Le Van Minh',
        ).user
        minh_two = create_company_user(
            company=self.company,
            local_username='minh.ops2',
            password='secret123',
            email='minh.ops2@example.com',
            role=CompanyRole.COMPANY_USER,
            full_name='Le Van Minh',
        ).user
        DepartmentMembership.objects.create(department=dept_hr, user=minh_one, is_active=True)
        DepartmentMembership.objects.create(department=dept_ops, user=minh_two, is_active=True)
        initial = resolve_recipient_query(
            'Le Van Minh',
            company=self.company,
            actor=self.actor,
        )

        clarified = resolve_choice_from_candidates('nhan su', initial['candidates'])

        self.assertEqual(clarified['status'], 'resolved')
        self.assertEqual(clarified['recipient']['user_id'], minh_one.id)

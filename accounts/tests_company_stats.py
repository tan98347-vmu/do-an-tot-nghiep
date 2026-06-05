"""Test cho accounts.services.company_stats — schema + cache."""

from django.core.cache import cache
from django.test import TestCase

from accounts.models import Company, CompanyStatus
from accounts.services.company_stats import (
    CACHE_KEY_PREFIX, compute_company_stats, invalidate_company_stats,
)


class CompanyStatsTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(
            code='r5-stats-test',
            name='R5 Stats Test Co',
            status=CompanyStatus.ACTIVE,
            email='stats@test.local',
        )

    def setUp(self):
        cache.delete(f'{CACHE_KEY_PREFIX}:{self.company.pk}')

    def test_schema_required_keys(self):
        result = compute_company_stats(self.company)
        self.assertIn('company', result)
        self.assertIn('counts', result)
        self.assertIn('storage', result)
        self.assertIn('last_backup', result)
        # company sub-schema
        for key in ('id', 'code', 'name', 'status', 'created_at'):
            self.assertIn(key, result['company'])
        # counts sub-schema (6 metric)
        for key in ('users', 'departments', 'positions', 'templates', 'documents', 'prompts'):
            self.assertIn(key, result['counts'])
            self.assertIsInstance(result['counts'][key], int)
        # storage
        self.assertIn('total_bytes', result['storage'])
        self.assertIn('by_subdir', result['storage'])

    def test_cache_hit_returns_same_object(self):
        first = compute_company_stats(self.company)
        # mutate cache to detect cache-hit
        cached_key = f'{CACHE_KEY_PREFIX}:{self.company.pk}'
        marker = {'company': {'sentinel': True}, 'counts': {}, 'storage': {'total_bytes': 0, 'by_subdir': {}}, 'last_backup': None}
        cache.set(cached_key, marker, 60)
        second = compute_company_stats(self.company)
        self.assertEqual(second['company'].get('sentinel'), True)
        # bypass=True khong nhan marker
        third = compute_company_stats(self.company, bypass_cache=True)
        self.assertNotEqual(third['company'].get('sentinel'), True)

    def test_invalidate_clears_cache(self):
        compute_company_stats(self.company)
        invalidate_company_stats(self.company.pk)
        cached_key = f'{CACHE_KEY_PREFIX}:{self.company.pk}'
        self.assertIsNone(cache.get(cached_key))

    def test_counts_are_non_negative(self):
        result = compute_company_stats(self.company)
        for k, v in result['counts'].items():
            self.assertGreaterEqual(v, 0, f'{k} expected >= 0, got {v}')

    def test_no_backup_returns_none(self):
        result = compute_company_stats(self.company)
        self.assertIsNone(result['last_backup'])

    def test_with_backup_returns_dict(self):
        from company_backups.models import CompanyBackup
        b = CompanyBackup.objects.create(
            company=self.company, name='test.zip', kind='manual',
            components=['documents'], file_path='test.zip', size_bytes=0,
            status='ready',
        )
        invalidate_company_stats(self.company.pk)
        result = compute_company_stats(self.company)
        self.assertIsNotNone(result['last_backup'])
        self.assertEqual(result['last_backup']['id'], b.id)
        self.assertIn('signature_status', result['last_backup'])
        self.assertIn('is_encrypted', result['last_backup'])

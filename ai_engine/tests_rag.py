# Chức năng web liên quan: Trợ lý AI, Hỏi đáp tài liệu và Sinh văn bản từ mẫu.
# Vai trò backend trong luồng: Tệp này giữ phần logic backend dùng chung cho trợ lý AI, RAG, OCR/prefill và sinh văn bản từ mẫu, để các flow ở màn Trợ lý AI, Hỏi đáp tài liệu, kết quả RAG và luồng Sinh văn bản từ mẫu không phải lặp lại cùng một rule ở nhiều nơi.
# Đầu vào/đầu ra chính: Giữ các helper, cấu hình và rule backend dùng lại ở nhiều flow khác nhau.
# Người dùng sẽ thấy trên web: Người dùng sẽ thấy dữ liệu, badge trạng thái, quyền nút và thông báo trên các chức năng Trợ lý AI, Hỏi đáp tài liệu và Sinh văn bản từ mẫu thay đổi đúng theo kết quả nghiệp vụ.

from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import TestCase

from ai_engine.management.commands import rebuild_rag_index as rebuild_command
from ai_engine.rag_index import (
    document_collection_names_for_companies,
    template_collection_names_for_companies,
)
from ai_engine.rag_search import (
    _db_search_documents,
    _db_search_templates,
    _progressive_semantic_hits,
    _query_terms,
    _semantic_collection_names,
)
from accounts.models import Company, CompanyRole, CompanyStatus, CompanyUserMembership
from accounts.models import UserGroup, UserGroupMembership
from api.trash_services import mark_deleted, restore_deleted
from document_templates.models import DocumentTemplate, TemplateCategory
from documents.models import Document
from sharing.constants import (
    APPROVAL_ACTIVE,
    APPROVAL_PENDING_ADMIN,
    PERMISSION_VIEW,
    SCOPE_COLLEAGUES,
    SCOPE_EVERYONE,
    SCOPE_GROUP,
)
from sharing.models import ShareGrant

# [Web] `RagSearchImprovementTests` gom một cụm xử lý backend dùng chung cho nhóm màn AI và hỏi đáp tài liệu.

class RagSearchImprovementTests(TestCase):
    # [Web] `setUp` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn AI và hỏi đáp tài liệu đang cần.

    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='secret')
        self.company = Company.objects.create(
            code='rag-company',
            name='RAG Company',
            status=CompanyStatus.ACTIVE,
        )
        CompanyUserMembership.objects.create(
            company=self.company,
            user=self.user,
            local_username='tester',
        )

    def _create_company_user(self, username, company, *, role=CompanyRole.COMPANY_USER):
        user = User.objects.create_user(username=username, password='secret')
        CompanyUserMembership.objects.create(
            company=company,
            user=user,
            local_username=username,
            role=role,
        )
        return user

    def _create_company(self, code):
        return Company.objects.create(
            code=code,
            name=code.replace('-', ' ').title(),
            status=CompanyStatus.ACTIVE,
        )

    def _create_group(self, company, name):
        return UserGroup.objects.create(company=company, name=name)

    def _grant_view(self, resource, target_user):
        ShareGrant.objects.create(
            content_type=ContentType.objects.get_for_model(type(resource)),
            object_id=resource.pk,
            scope=SCOPE_COLLEAGUES,
            target_user=target_user,
            permission_level=PERMISSION_VIEW,
            approval_status=APPROVAL_ACTIVE,
            created_by=getattr(resource, 'owner', None) or getattr(resource, 'created_by', None),
        )

    def _create_pending_view_grant(self, resource, target_user):
        ShareGrant.objects.create(
            content_type=ContentType.objects.get_for_model(type(resource)),
            object_id=resource.pk,
            scope=SCOPE_COLLEAGUES,
            target_user=target_user,
            permission_level=PERMISSION_VIEW,
            approval_status=APPROVAL_PENDING_ADMIN,
            created_by=getattr(resource, 'owner', None) or getattr(resource, 'created_by', None),
        )

    def _grant_group_view(self, resource, group):
        ShareGrant.objects.create(
            content_type=ContentType.objects.get_for_model(type(resource)),
            object_id=resource.pk,
            scope=SCOPE_GROUP,
            target_group=group,
            permission_level=PERMISSION_VIEW,
            approval_status=APPROVAL_ACTIVE,
            created_by=getattr(resource, 'owner', None) or getattr(resource, 'created_by', None),
        )

    def _grant_everyone_view(self, resource):
        ShareGrant.objects.create(
            content_type=ContentType.objects.get_for_model(type(resource)),
            object_id=resource.pk,
            scope=SCOPE_EVERYONE,
            permission_level=PERMISSION_VIEW,
            approval_status=APPROVAL_ACTIVE,
            created_by=getattr(resource, 'owner', None) or getattr(resource, 'created_by', None),
        )

    # [Web] `test_query_terms_drop_stopwords_but_keep_meaningful_tokens` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn AI và hỏi đáp tài liệu đang cần.

    def test_query_terms_drop_stopwords_but_keep_meaningful_tokens(self):
        self.assertEqual(
            _query_terms('hop dong the chap co phan'),
            ['hop', 'dong', 'chap', 'phan'],
        )

    # [Web] `test_template_search_handles_accentless_query` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn AI và hỏi đáp tài liệu đang cần.

    @patch('ai_engine.rag_search._progressive_semantic_hits', return_value={})
    def test_template_search_handles_accentless_query(self, _mock_semantic):
        category = TemplateCategory.objects.create(name='Hop dong', description='Loai hop dong')
        DocumentTemplate.objects.create(
            owner=self.user,
            title='Hop dong the chap co phan',
            description='Mau hop dong the chap co phan',
            content='Noi dung mau hop dong the chap co phan',
            category=category,
        )
        DocumentTemplate.objects.create(
            owner=self.user,
            title='Quy che chi tieu noi bo',
            description='Van ban khong lien quan',
            content='Noi dung quy che noi bo',
        )

        accentless = _db_search_templates('hop dong the chap co phan', self.user, 3)
        accented = _db_search_templates('hợp đồng thế chấp cổ phần', self.user, 3)

        self.assertTrue(accentless)
        self.assertTrue(accented)
        self.assertEqual(accentless[0]['citation']['title'], 'Hop dong the chap co phan')
        self.assertEqual(accented[0]['citation']['title'], 'Hop dong the chap co phan')

    # [Web] `test_document_search_handles_accentless_query` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn AI và hỏi đáp tài liệu đang cần.

    @patch('ai_engine.rag_search._progressive_semantic_hits', return_value={})
    def test_document_search_handles_accentless_query(self, _mock_semantic):
        category = TemplateCategory.objects.create(name='Quy che', description='Van ban noi bo')
        Document.objects.create(
            owner=self.user,
            title='Quy che thanh toan cong tac phi',
            content='Noi dung quy che cong tac phi bang tien mat',
            doc_number='QC-01/2026',
            category=category,
            visibility='private',
            share_status='active',
        )
        Document.objects.create(
            owner=self.user,
            title='Thong bao nghi le',
            content='Thong bao nghi le 30/4',
            visibility='private',
            share_status='active',
        )

        results = _db_search_documents('quy che thanh toan cong tac phi', self.user, 3)
        self.assertTrue(results)
        self.assertEqual(results[0]['citation']['title'], 'Quy che thanh toan cong tac phi')

    @patch('ai_engine.rag_search._progressive_semantic_hits', return_value={})
    def test_document_search_falls_back_to_content_when_semantic_index_lags(self, _mock_semantic):
        Document.objects.create(
            owner=self.user,
            title='Van ban moi tao',
            content='Dieu khoan dac biet ve phi trien khai AI Omega 2026.',
            visibility='private',
            share_status='active',
        )

        results = _db_search_documents('phi trien khai AI Omega 2026', self.user, 1)

        self.assertTrue(results)
        self.assertEqual(results[0]['citation']['title'], 'Van ban moi tao')
        self.assertIn('Omega 2026', results[0]['context'])

    @patch('ai_engine.rag_search._progressive_semantic_hits', return_value={})
    def test_document_search_only_reads_viewable_documents_in_user_company(self, _mock_semantic):
        same_company_owner = self._create_company_user('same-doc-owner', self.company)
        shared_document = Document.objects.create(
            owner=same_company_owner,
            title='Van ban duoc chia se',
            content='Noi dung chia se noi bo Sigma 2026.',
            visibility='private',
            share_status='active',
        )
        self._grant_view(shared_document, self.user)
        Document.objects.create(
            owner=same_company_owner,
            title='Van ban cung cong ty chua chia se',
            content='Noi dung cung cong ty nhung khong co quyen xem Sigma 2026.',
            visibility='private',
            share_status='active',
        )
        other_company = self._create_company('other-doc-company')
        other_owner = self._create_company_user('other-doc-owner', other_company)
        Document.objects.create(
            owner=other_owner,
            title='Van ban cong ty khac',
            content='Noi dung bi cam doc Sigma 2026.',
            visibility='private',
            share_status='active',
        )

        results = _db_search_documents('Sigma 2026', self.user, 3)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['citation']['title'], 'Van ban duoc chia se')

    @patch('ai_engine.rag_search._progressive_semantic_hits', return_value={})
    def test_rag_denies_pending_and_cross_company_grants(self, _mock_semantic):
        same_company_owner = self._create_company_user('pending-owner', self.company)
        pending_document = Document.objects.create(
            owner=same_company_owner,
            title='Van ban grant chua duyet',
            content='Noi dung khong duoc doc Permission Tight 2026.',
            visibility='private',
            share_status='active',
        )
        pending_template = DocumentTemplate.objects.create(
            owner=same_company_owner,
            title='Mau grant chua duyet',
            description='Mo ta',
            content='Noi dung mau khong duoc doc Permission Tight 2026.',
        )
        self._create_pending_view_grant(pending_document, self.user)
        self._create_pending_view_grant(pending_template, self.user)

        other_company = self._create_company('cross-grant-company')
        other_owner = self._create_company_user('cross-grant-owner', other_company)
        cross_document = Document.objects.create(
            owner=other_owner,
            title='Van ban grant khac cong ty',
            content='Noi dung grant khac cong ty Permission Tight 2026.',
            visibility='private',
            share_status='active',
        )
        cross_template = DocumentTemplate.objects.create(
            owner=other_owner,
            title='Mau grant khac cong ty',
            description='Mo ta',
            content='Noi dung mau grant khac cong ty Permission Tight 2026.',
        )
        self._grant_view(cross_document, self.user)
        self._grant_view(cross_template, self.user)

        self.assertEqual(_db_search_documents('Permission Tight 2026', self.user, 5), [])
        self.assertEqual(_db_search_templates('Permission Tight 2026', self.user, 5), [])

    @patch('ai_engine.rag_search._progressive_semantic_hits', return_value={})
    def test_rag_accepts_active_group_and_everyone_scopes_in_user_company(self, _mock_semantic):
        same_company_owner = self._create_company_user('scope-owner', self.company)
        group = self._create_group(self.company, 'RAG Scope Group')
        UserGroupMembership.objects.create(group=group, user=self.user)
        UserGroupMembership.objects.create(group=group, user=same_company_owner)

        group_document = Document.objects.create(
            owner=same_company_owner,
            title='Van ban scope nhom',
            content='Noi dung scope nhom GroupScope 2026.',
            visibility='private',
            share_status='active',
        )
        group_template = DocumentTemplate.objects.create(
            owner=same_company_owner,
            title='Mau scope nhom',
            description='Mo ta',
            content='Noi dung mau scope nhom GroupScope 2026.',
        )
        everyone_document = Document.objects.create(
            owner=same_company_owner,
            title='Van ban scope moi nguoi',
            content='Noi dung scope moi nguoi EveryoneScope 2026.',
            visibility='private',
            share_status='active',
        )
        everyone_template = DocumentTemplate.objects.create(
            owner=same_company_owner,
            title='Mau scope moi nguoi',
            description='Mo ta',
            content='Noi dung mau scope moi nguoi EveryoneScope 2026.',
        )
        self._grant_group_view(group_document, group)
        self._grant_group_view(group_template, group)
        self._grant_everyone_view(everyone_document)
        self._grant_everyone_view(everyone_template)

        group_documents = _db_search_documents('GroupScope 2026', self.user, 3)
        group_templates = _db_search_templates('GroupScope 2026', self.user, 3)
        everyone_documents = _db_search_documents('EveryoneScope 2026', self.user, 3)
        everyone_templates = _db_search_templates('EveryoneScope 2026', self.user, 3)

        self.assertEqual(group_documents[0]['citation']['title'], 'Van ban scope nhom')
        self.assertEqual(group_templates[0]['citation']['title'], 'Mau scope nhom')
        self.assertEqual(everyone_documents[0]['citation']['title'], 'Van ban scope moi nguoi')
        self.assertEqual(everyone_templates[0]['citation']['title'], 'Mau scope moi nguoi')

    @patch('ai_engine.rag_search._progressive_semantic_hits', return_value={})
    def test_template_search_falls_back_to_content_when_semantic_index_lags(self, _mock_semantic):
        DocumentTemplate.objects.create(
            owner=self.user,
            title='Mau moi tao',
            description='Mo ta chung',
            content='Noi dung quy dinh dieu kien bao hanh Zeta 2026.',
        )

        results = _db_search_templates('dieu kien bao hanh Zeta 2026', self.user, 1)

        self.assertTrue(results)
        self.assertEqual(results[0]['citation']['title'], 'Mau moi tao')
        self.assertIn('Zeta 2026', results[0]['context'])

    @patch('ai_engine.rag_search._progressive_semantic_hits', return_value={})
    def test_template_search_only_reads_viewable_templates_in_user_company(self, _mock_semantic):
        same_company_owner = self._create_company_user('same-template-owner', self.company)
        shared_template = DocumentTemplate.objects.create(
            owner=same_company_owner,
            title='Mau duoc chia se',
            description='Mo ta',
            content='Noi dung mau chia se Kappa 2026.',
        )
        self._grant_view(shared_template, self.user)
        DocumentTemplate.objects.create(
            owner=same_company_owner,
            title='Mau cung cong ty chua chia se',
            description='Mo ta',
            content='Noi dung mau cung cong ty nhung khong co quyen xem Kappa 2026.',
        )
        other_company = self._create_company('other-template-company')
        other_owner = self._create_company_user('other-template-owner', other_company)
        DocumentTemplate.objects.create(
            owner=other_owner,
            title='Mau cong ty khac',
            description='Mo ta',
            content='Noi dung mau bi cam doc Kappa 2026.',
        )

        results = _db_search_templates('Kappa 2026', self.user, 3)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['citation']['title'], 'Mau duoc chia se')

    @patch('ai_engine.rag_search._progressive_semantic_hits', return_value={})
    @patch('ai_engine.rag_search.get_accessible_documents')
    def test_document_rag_uses_current_document_permission_queryset(self, mock_accessible, _mock_semantic):
        same_company_owner = self._create_company_user('current-doc-owner', self.company)
        allowed_document = Document.objects.create(
            owner=same_company_owner,
            title='Van ban theo quyen hien tai',
            content='Noi dung theo quyen hien tai CurrentPermissionDoc 2026.',
            visibility='private',
            share_status='active',
        )
        Document.objects.create(
            owner=same_company_owner,
            title='Van ban khong nam trong queryset quyen',
            content='Noi dung khong nam trong queryset quyen CurrentPermissionDoc 2026.',
            visibility='private',
            share_status='active',
        )
        mock_accessible.return_value = Document.objects.filter(pk=allowed_document.pk)

        results = _db_search_documents('CurrentPermissionDoc 2026', self.user, 5)

        mock_accessible.assert_called_once_with(self.user)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['citation']['title'], 'Van ban theo quyen hien tai')

    @patch('ai_engine.rag_search._progressive_semantic_hits', return_value={})
    @patch('ai_engine.rag_search.get_accessible_templates')
    def test_template_rag_uses_current_template_permission_queryset(self, mock_accessible, _mock_semantic):
        same_company_owner = self._create_company_user('current-template-owner', self.company)
        allowed_template = DocumentTemplate.objects.create(
            owner=same_company_owner,
            title='Mau theo quyen hien tai',
            description='Mo ta',
            content='Noi dung mau theo quyen hien tai CurrentPermissionTemplate 2026.',
        )
        DocumentTemplate.objects.create(
            owner=same_company_owner,
            title='Mau khong nam trong queryset quyen',
            description='Mo ta',
            content='Noi dung mau khong nam trong queryset quyen CurrentPermissionTemplate 2026.',
        )
        mock_accessible.return_value = DocumentTemplate.objects.filter(pk=allowed_template.pk)

        results = _db_search_templates('CurrentPermissionTemplate 2026', self.user, 5)

        mock_accessible.assert_called_once_with(self.user)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['citation']['title'], 'Mau theo quyen hien tai')

    @patch('ai_engine.rag_search._semantic_rank_map', return_value={})
    def test_rag_semantic_search_does_not_read_global_legacy_collections(self, mock_semantic):
        _db_search_documents('semantic only document', self.user, 1)
        _db_search_templates('semantic only template', self.user, 1)

        called_collections = [call.args[1] for call in mock_semantic.call_args_list]
        self.assertIn(f'company_{self.company.pk}_document_rag_kb', called_collections)
        self.assertIn(f'company_{self.company.pk}_template_rag_kb', called_collections)
        self.assertNotIn('document_rag_kb', called_collections)
        self.assertNotIn('template_rag_kb', called_collections)

    @patch('ai_engine.rag_search._progressive_semantic_hits', return_value={})
    def test_rag_search_follows_current_permissions_for_user_without_active_company(self, _mock_semantic):
        legacy_user = User.objects.create_user(username='legacy-user', password='secret')
        Document.objects.create(
            owner=legacy_user,
            title='Legacy document',
            content='Noi dung legacy khong co company',
            visibility='private',
            share_status='active',
        )
        DocumentTemplate.objects.create(
            owner=legacy_user,
            title='Legacy template',
            description='Mo ta',
            content='Noi dung legacy template khong co company',
        )

        document_results = _db_search_documents('legacy', legacy_user, 1)
        template_results = _db_search_templates('legacy', legacy_user, 1)

        self.assertEqual(document_results[0]['citation']['title'], 'Legacy document')
        self.assertEqual(template_results[0]['citation']['title'], 'Legacy template')

    @patch('ai_engine.rag_search._semantic_rank_map')
    def test_rag_semantic_hits_are_filtered_by_current_permission_queryset(self, mock_semantic):
        same_company_owner = self._create_company_user('semantic-denied-owner', self.company)
        accessible_document = Document.objects.create(
            owner=self.user,
            title='Van ban semantic duoc phep',
            content='Noi dung chung khong chua tu khoa.',
            visibility='private',
            share_status='active',
        )
        denied_document = Document.objects.create(
            owner=same_company_owner,
            title='Van ban semantic bi chan',
            content='Noi dung rieng khong chua tu khoa.',
            visibility='private',
            share_status='active',
        )
        accessible_template = DocumentTemplate.objects.create(
            owner=self.user,
            title='Mau semantic duoc phep',
            description='Mo ta',
            content='Noi dung mau chung khong chua tu khoa.',
        )
        denied_template = DocumentTemplate.objects.create(
            owner=same_company_owner,
            title='Mau semantic bi chan',
            description='Mo ta',
            content='Noi dung mau rieng khong chua tu khoa.',
        )

        def fake_semantic(_question, collection_name, *, fetch_k=64):
            if 'document' in collection_name:
                return {
                    denied_document.pk: {
                        'rank': 0,
                        'metadata': {'id': denied_document.pk},
                        'chunk_text': 'Forbidden semantic Vector Guard 2026.',
                    },
                    accessible_document.pk: {
                        'rank': 1,
                        'metadata': {'id': accessible_document.pk},
                        'chunk_text': 'Allowed semantic Vector Guard 2026.',
                    },
                }
            if 'template' in collection_name:
                return {
                    denied_template.pk: {
                        'rank': 0,
                        'metadata': {'id': denied_template.pk},
                        'chunk_text': 'Forbidden template semantic Vector Guard 2026.',
                    },
                    accessible_template.pk: {
                        'rank': 1,
                        'metadata': {'id': accessible_template.pk},
                        'chunk_text': 'Allowed template semantic Vector Guard 2026.',
                    },
                }
            return {}

        mock_semantic.side_effect = fake_semantic

        document_results = _db_search_documents('Vector Guard 2026', self.user, 3)
        template_results = _db_search_templates('Vector Guard 2026', self.user, 3)

        self.assertEqual(len(document_results), 1)
        self.assertEqual(document_results[0]['citation']['title'], 'Van ban semantic duoc phep')
        self.assertIn('Allowed semantic Vector Guard 2026', document_results[0]['context'])
        self.assertNotIn('Forbidden semantic Vector Guard 2026', document_results[0]['context'])
        self.assertEqual(len(template_results), 1)
        self.assertEqual(template_results[0]['citation']['title'], 'Mau semantic duoc phep')
        self.assertIn('Allowed template semantic Vector Guard 2026', template_results[0]['context'])
        self.assertNotIn('Forbidden template semantic Vector Guard 2026', template_results[0]['context'])

    # [Web] `test_semantic_chunk_is_used_as_context_when_lexical_misses` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn AI và hỏi đáp tài liệu đang cần.

    @patch('ai_engine.rag_search._progressive_semantic_hits')
    def test_semantic_chunk_is_used_as_context_when_lexical_misses(self, mock_semantic):
        document = Document.objects.create(
            owner=self.user,
            title='Bao cao chi phi',
            content='Noi dung tong quat khong co cau tra loi o doan dau.',
            visibility='private',
            share_status='active',
        )
        mock_semantic.return_value = {
            document.pk: {
                'rank': 0,
                'metadata': {'id': document.pk},
                'chunk_text': 'Dieu 5 Thanh toan cong tac phi bang taxi duoc hoan ung.',
            }
        }

        results = _db_search_documents('thanh toan cong tac phi bang taxi', self.user, 1)
        self.assertTrue(results)
        self.assertIn('Dieu 5 Thanh toan cong tac phi bang taxi duoc hoan ung.', results[0]['context'])

    def test_document_semantic_search_uses_company_collection(self):
        company = Company.objects.create(code='acme-rag-doc', name='Acme RAG Doc')
        document = Document.objects.create(
            owner=self.user,
            company=company,
            title='Bao cao moi',
            content='Noi dung moi can hoi dap',
            visibility='private',
            share_status='active',
        )
        base_qs = Document.objects.filter(pk=document.pk)
        collection_names = _semantic_collection_names(
            base_qs,
            document_collection_names_for_companies,
        )

        self.assertEqual(collection_names[0], f'company_{company.pk}_document_rag_kb')
        self.assertEqual(collection_names[-1], 'document_rag_kb')

        def fake_semantic(_question, collection_name, *, fetch_k=64):
            if collection_name == f'company_{company.pk}_document_rag_kb':
                return {
                    document.pk: {
                        'rank': 0,
                        'metadata': {'id': document.pk},
                        'chunk_text': 'Can cu moi xuat hien trong van ban vua tao.',
                    }
                }
            return {}

        with patch('ai_engine.rag_search._semantic_rank_map', side_effect=fake_semantic):
            hits = _progressive_semantic_hits('can cu moi', collection_names, base_qs, 1)

        self.assertIn(document.pk, hits)
        self.assertEqual(hits[document.pk]['collection'], f'company_{company.pk}_document_rag_kb')
        self.assertIn('van ban vua tao', hits[document.pk]['chunk_text'])

    def test_template_semantic_search_prefers_company_collection_over_legacy_global(self):
        company = Company.objects.create(code='acme-rag-template', name='Acme RAG Template')
        template = DocumentTemplate.objects.create(
            owner=self.user,
            company=company,
            title='Mau quy dinh moi',
            description='Mo ta ngan',
            content='Noi dung mau moi can hoi dap',
        )
        base_qs = DocumentTemplate.objects.filter(pk=template.pk)
        collection_names = _semantic_collection_names(
            base_qs,
            template_collection_names_for_companies,
        )

        def fake_semantic(_question, collection_name, *, fetch_k=64):
            if collection_name == f'company_{company.pk}_template_rag_kb':
                return {
                    template.pk: {
                        'rank': 4,
                        'metadata': {'id': template.pk},
                        'chunk_text': 'Chunk moi dung cua mau vua tao.',
                    }
                }
            if collection_name == 'template_rag_kb':
                return {
                    template.pk: {
                        'rank': 0,
                        'metadata': {'id': template.pk},
                        'chunk_text': 'Chunk cu trong collection global.',
                    }
                }
            return {}

        with patch('ai_engine.rag_search._semantic_rank_map', side_effect=fake_semantic):
            hits = _progressive_semantic_hits('mau moi', collection_names, base_qs, 1)

        self.assertIn(template.pk, hits)
        self.assertEqual(hits[template.pk]['collection'], f'company_{company.pk}_template_rag_kb')
        self.assertIn('Chunk moi', hits[template.pk]['chunk_text'])

    def test_company_collections_are_prioritized_before_global_legacy_collection(self):
        self.assertEqual(
            document_collection_names_for_companies([None, 7, None, 7]),
            ['company_7_document_rag_kb', 'document_rag_kb'],
        )
        self.assertEqual(
            template_collection_names_for_companies([None, 9, None, 9]),
            ['company_9_template_rag_kb', 'template_rag_kb'],
        )

# [Web] `RagSignalLifecycleTests` gom một cụm xử lý backend dùng chung cho nhóm màn AI và hỏi đáp tài liệu.

class RagSignalLifecycleTests(TestCase):
    # [Web] `setUp` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn AI và hỏi đáp tài liệu đang cần.

    def setUp(self):
        self.user = User.objects.create_user(username='signal-user', password='secret')

    # [Web] `test_document_signal_keeps_index_in_sync` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn AI và hỏi đáp tài liệu đang cần.

    @patch('documents.signals.sync_document_index')
    @patch('documents.signals.purge_document_index')
    def test_document_signal_keeps_index_in_sync(self, mock_purge, mock_sync):
        with self.captureOnCommitCallbacks(execute=True):
            document = Document.objects.create(
                owner=self.user,
                title='Van ban 1',
                content='Noi dung 1',
                visibility='private',
                share_status='active',
            )
        mock_sync.assert_called_once_with(document.pk)

        mock_sync.reset_mock()
        with self.captureOnCommitCallbacks(execute=True):
            document.title = 'Van ban 1 sua'
            document.save(update_fields=['title'])
        mock_sync.assert_called_once_with(document.pk)

        mock_sync.reset_mock()
        company = Company.objects.create(code='signal-doc-company', name='Signal Doc Company')
        with self.captureOnCommitCallbacks(execute=True):
            document.company = company
            document.save(update_fields=['company'])
        mock_sync.assert_called_once_with(document.pk)

        mock_purge.reset_mock()
        with self.captureOnCommitCallbacks(execute=True):
            mark_deleted(document, self.user)
        mock_purge.assert_called_once_with(document.pk)

        mock_sync.reset_mock()
        document.refresh_from_db()
        with self.captureOnCommitCallbacks(execute=True):
            restore_deleted(document)
        mock_sync.assert_called_once_with(document.pk)

        mock_purge.reset_mock()
        document_id = document.pk
        with self.captureOnCommitCallbacks(execute=True):
            document.delete()
        mock_purge.assert_called_once_with(document_id)

    # [Web] `test_template_signal_keeps_index_in_sync` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn AI và hỏi đáp tài liệu đang cần.

    @patch('document_templates.signals.sync_template_index')
    @patch('document_templates.signals.purge_template_index')
    def test_template_signal_keeps_index_in_sync(self, mock_purge, mock_sync):
        with self.captureOnCommitCallbacks(execute=True):
            template = DocumentTemplate.objects.create(
                owner=self.user,
                title='Mau 1',
                description='Mo ta',
                content='Noi dung mau',
            )
        mock_sync.assert_called_once_with(template.pk)

        mock_purge.reset_mock()
        with self.captureOnCommitCallbacks(execute=True):
            mark_deleted(template, self.user)
        mock_purge.assert_called_once_with(template.pk)

        mock_sync.reset_mock()
        template.refresh_from_db()
        with self.captureOnCommitCallbacks(execute=True):
            restore_deleted(template)
        mock_sync.assert_called_once_with(template.pk)

        mock_purge.reset_mock()
        with self.captureOnCommitCallbacks(execute=True):
            template.status = 'rejected'
            template.save(update_fields=['status'])
        mock_purge.assert_called_once_with(template.pk)

        mock_sync.reset_mock()
        with self.captureOnCommitCallbacks(execute=True):
            template.status = 'draft'
            template.save(update_fields=['status'])
        mock_sync.assert_called_once_with(template.pk)

        mock_sync.reset_mock()
        company = Company.objects.create(code='signal-template-company', name='Signal Template Company')
        with self.captureOnCommitCallbacks(execute=True):
            template.company = company
            template.save(update_fields=['company'])
        mock_sync.assert_called_once_with(template.pk)

        mock_sync.reset_mock()
        with self.captureOnCommitCallbacks(execute=True):
            template.docx_file = 'templates/signal-template.docx'
            template.save(update_fields=['docx_file'])
        mock_sync.assert_called_once_with(template.pk)

        mock_purge.reset_mock()
        template_id = template.pk
        with self.captureOnCommitCallbacks(execute=True):
            template.delete()
        mock_purge.assert_called_once_with(template_id)

# [Web] `RebuildRagIndexCommandTests` gom một cụm xử lý backend dùng chung cho nhóm màn AI và hỏi đáp tài liệu.

class RebuildRagIndexCommandTests(TestCase):
    # [Web] `test_dry_run_only_prints_stats` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn AI và hỏi đáp tài liệu đang cần.

    @patch.object(rebuild_command, 'document_index_stats')
    @patch.object(rebuild_command, 'template_index_stats')
    @patch.object(rebuild_command, 'rebuild_document_index')
    @patch.object(rebuild_command, 'rebuild_template_index')
    def test_dry_run_only_prints_stats(
        self,
        mock_rebuild_templates,
        mock_rebuild_documents,
        mock_template_stats,
        mock_document_stats,
    ):
        mock_template_stats.return_value = {
            'total_rows': 10,
            'indexed_objects': 3,
            'live_objects': 3,
            'stale_objects': 0,
            'missing_objects': 1,
            'stale_ids': [],
            'missing_ids': [99],
        }
        mock_document_stats.return_value = {
            'total_rows': 20,
            'indexed_objects': 4,
            'live_objects': 4,
            'stale_objects': 0,
            'missing_objects': 0,
            'stale_ids': [],
            'missing_ids': [],
        }
        out = StringIO()

        call_command('rebuild_rag_index', '--dry-run', stdout=out)

        self.assertIn('Dry run only', out.getvalue())
        mock_rebuild_templates.assert_not_called()
        mock_rebuild_documents.assert_not_called()

    # [Web] `test_scope_templates_rebuilds_only_templates` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn AI và hỏi đáp tài liệu đang cần.

    @patch.object(rebuild_command, 'template_index_stats')
    @patch.object(rebuild_command, 'rebuild_template_index')
    def test_scope_templates_rebuilds_only_templates(self, mock_rebuild_templates, mock_template_stats):
        mock_template_stats.return_value = {
            'total_rows': 0,
            'indexed_objects': 0,
            'live_objects': 0,
            'stale_objects': 0,
            'missing_objects': 0,
            'stale_ids': [],
            'missing_ids': [],
        }
        mock_rebuild_templates.return_value = {
            'deleted_rows': 0,
            'indexed_objects': 2,
            'indexed_chunks': 5,
        }
        out = StringIO()

        call_command('rebuild_rag_index', '--scope', 'templates', stdout=out)

        mock_rebuild_templates.assert_called_once_with(company_id=None)
        self.assertIn('[templates] rebuilt', out.getvalue())

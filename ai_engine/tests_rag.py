# Chức năng web liên quan: Trợ lý AI, Hỏi đáp tài liệu và Sinh văn bản từ mẫu.
# Vai trò backend trong luồng: Tệp này giữ phần logic backend dùng chung cho trợ lý AI, RAG, OCR/prefill và sinh văn bản từ mẫu, để các flow ở màn Trợ lý AI, Hỏi đáp tài liệu, kết quả RAG và luồng Sinh văn bản từ mẫu không phải lặp lại cùng một rule ở nhiều nơi.
# Đầu vào/đầu ra chính: Giữ các helper, cấu hình và rule backend dùng lại ở nhiều flow khác nhau.
# Người dùng sẽ thấy trên web: Người dùng sẽ thấy dữ liệu, badge trạng thái, quyền nút và thông báo trên các chức năng Trợ lý AI, Hỏi đáp tài liệu và Sinh văn bản từ mẫu thay đổi đúng theo kết quả nghiệp vụ.

from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from ai_engine.management.commands import rebuild_rag_index as rebuild_command
from ai_engine.rag_search import _db_search_documents, _db_search_templates, _query_terms
from api.trash_services import mark_deleted, restore_deleted
from document_templates.models import DocumentTemplate, TemplateCategory
from documents.models import Document

# [Web] `RagSearchImprovementTests` gom một cụm xử lý backend dùng chung cho nhóm màn AI và hỏi đáp tài liệu.

class RagSearchImprovementTests(TestCase):
    # [Web] `setUp` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn AI và hỏi đáp tài liệu đang cần.

    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='secret')

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

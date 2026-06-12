import logging
import queue
import threading

from django.db import transaction

from documents.models import Document
from documents.preview_builder import DocumentPreviewUnavailable, build_document_preview_pdf


PREVIEW_LOGGER = logging.getLogger('documents.preview_pdf')


# class _PreviewRegenerationScheduler là lớp gom logic/dữ liệu liên quan.
# vd: gom các thuộc tính/method liên quan vào một nơi.
class _PreviewRegenerationScheduler:
    # def __init__ để khởi tạo đối tượng.
    # vd: khởi tạo với các tham số cần thiết.
    def __init__(self):
        self._queue = queue.Queue()
        self._pending_document_ids = set()
        self._lock = threading.Lock()
        self._worker_started = False

    # def enqueue_document để enqueue document.
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def enqueue_document(self, document_id):
        with self._lock:
            if document_id in self._pending_document_ids:
                return False
            self._pending_document_ids.add(document_id)
            self._ensure_worker_started()
            self._queue.put(document_id)
            return True

    # def _ensure_worker_started để đảm bảo worker started.
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def _ensure_worker_started(self):
        if self._worker_started:
            return
        worker = threading.Thread(
            target=self._run_forever,
            daemon=True,
            name='document-preview-regenerator',
        )
        worker.start()
        self._worker_started = True

    # def _run_forever để chạy forever.
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def _run_forever(self):
        while True:
            document_id = self._queue.get()
            try:
                self._build_document_preview(document_id)
            finally:
                with self._lock:
                    self._pending_document_ids.discard(document_id)
                self._queue.task_done()

    # def _build_document_preview để dựng document preview.
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def _build_document_preview(self, document_id):
        try:
            document = Document.objects.get(pk=document_id)
        except Document.DoesNotExist:
            PREVIEW_LOGGER.warning('preview warm skipped | document_id=%s | reason=document_missing', document_id)
            return

        if not getattr(document, 'output_file', None):
            PREVIEW_LOGGER.info('preview warm skipped | document_id=%s | reason=no_output_file', document_id)
            return

        try:
            pdf_path = build_document_preview_pdf(document)
        except DocumentPreviewUnavailable as exc:
            PREVIEW_LOGGER.warning(
                'preview warm failed | document_id=%s | code=%s | detail=%s',
                document_id,
                exc.code,
                exc.detail,
            )
        except Exception as exc:
            PREVIEW_LOGGER.warning(
                'preview warm failed | document_id=%s | code=unexpected | detail=%s',
                document_id,
                exc,
            )
        else:
            PREVIEW_LOGGER.info('preview warm ready | document_id=%s | pdf=%s', document_id, pdf_path)


_SCHEDULER = _PreviewRegenerationScheduler()


# def schedule_document_preview_regeneration để schedule document preview regeneration.
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def schedule_document_preview_regeneration(document):
    document_id = getattr(document, 'pk', None)
    if document_id is None:
        return False

    # def _enqueue để enqueue.
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def _enqueue():
        scheduled = _SCHEDULER.enqueue_document(document_id)
        if scheduled:
            PREVIEW_LOGGER.info('preview warm queued | document_id=%s', document_id)

    transaction.on_commit(_enqueue)
    return True

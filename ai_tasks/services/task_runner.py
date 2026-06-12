"""
task_runner.py:1 là file được sử dụng nhiều nhất.

  Nó phục vụ các tác vụ UI:

  - ChatAI.
  - Trợ lý AI.
  - Giọng nói AI.
  - Trích xuất PDF.
  - OCR ảnh.
  - Prefill từ hồ sơ.
  - Prefill từ công ty.
  - Tạo văn bản từ mẫu.
  - Tóm tắt văn bản.

  Luồng:

  API nhận request
  → create_task()
  → tạo AITaskProgress
  → run_in_thread()
  → chạy nghiệp vụ nền
  → update_progress()
  → append_stream_chunk()
  → mark_completed()/mark_failed()
  → Flutter polling kết quả

  Nó còn hỗ trợ:

  - Hủy mềm bằng check_cancel().
  - Hủy cứng bằng đóng HTTP session.
  - Streaming token.
  - Dọn kết nối database sau thread.
  - Ghi kết quả và lỗi.

  ai_tasks/services/task_runner.py:1 hiện là cơ chế chính giúp chạy một số tác vụ nặng dưới background thread, để request HTTP không phải chờ đến khi
  công việc hoàn thành.

  Luồng:

  Người dùng bấm thực hiện trên UI
  → API tạo AITaskProgress
  → run_in_thread() mở thread nền
  → API trả task_id ngay cho Flutter
  → Thread tiếp tục xử lý
  → Flutter dùng task_id để hỏi tiến độ
  → Hoàn thành thì nhận result

  Các tác vụ đang sử dụng nó gồm:

  - ChatAI.
  - Trợ lý AI và VoiceAI.
  - Tạo văn bản từ mẫu.
  - Trích xuất PDF.
  - OCR ảnh.
  - Prefill từ hồ sơ/công ty.
  - Tóm tắt văn bản.

  Ngoài chạy nền, nó còn hỗ trợ:

  - Cập nhật phần trăm và giai đoạn.
  - Streaming từng đoạn phản hồi AI.
  - Hủy tác vụ.
  - Ghi kết quả hoặc lỗi.
  - Đóng kết nối database sau khi thread kết thúc.

  Điểm cần lưu ý:

  > Đây là background thread chạy bên trong tiến trình Django,


"""

import logging
import threading
import time
from threading import Lock
from typing import Any, Callable, Iterable, Optional

from django.contrib.auth.models import User
from django.db import close_old_connections, transaction
from django.utils import timezone

from ai_tasks.models import (
    AITaskProgress,
    CANCEL_MODE_HARD, CANCEL_MODE_SOFT,
    STATUS_CANCELLED, STATUS_COMPLETED, STATUS_FAILED,
    STATUS_QUEUED, STATUS_RUNNING,
)

logger = logging.getLogger(__name__)


# class TaskCancelled là exception phát ra từ fn chính khi check_cancel phát hiện yêu cầu hủy, để runner đánh dấu tác vụ là 'đã dừng'.
# vd: giữa vòng OCR gọi check_cancel -> nếu user bấm Dừng thì ném TaskCancelled.
class TaskCancelled(Exception):
    """Goi tu fn chinh khi check_cancel phat hien cancel_requested."""
    pass


_hard_sessions: dict[str, list] = {}
_hard_sessions_lock = Lock()

_stream_buffers: dict[str, list[str]] = {}
_stream_last_flush: dict[str, float] = {}
_stream_lock = Lock()


# def create_task để tạo bản ghi AITaskProgress mới ở trạng thái 'queued' cho một loại tác vụ.
# vd: create_task(user=u, task_type='extract_pdf') -> task để chạy nền.
def create_task(
    *,
    user: User,
    task_type: str,
    cancel_mode: str = CANCEL_MODE_SOFT,
    related_entity_type: str = '',
    related_entity_id: Optional[int] = None,
) -> AITaskProgress:
    return AITaskProgress.objects.create(
        user=user,
        task_type=task_type,
        cancel_mode=cancel_mode,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        status=STATUS_QUEUED,
    )


# def update_progress để cập nhật % + bước + chi tiết và đặt trạng thái 'running' cho tác vụ.
# vd: update_progress(id, 60, 'Cloud OCR', 'trang 3/5').
def update_progress(task_id, percent: int, stage: str, detail: str = '') -> None:
    try:
        AITaskProgress.objects.filter(task_id=task_id).update(
            progress_percent=max(0, min(100, int(percent))),
            progress_stage=str(stage or '')[:64],
            progress_detail=str(detail or '')[:255],
            status=STATUS_RUNNING,
        )
    except Exception:
        logger.exception('[ai_tasks] update_progress failed task_id=%s', task_id)


# def _task_cancel_snapshot để đọc nhanh (cancel_requested, cancel_mode, status) hiện tại của tác vụ từ DB.
# vd: -> (True, 'hard', 'running') nếu user vừa bấm Dừng cứng.
def _task_cancel_snapshot(task_id) -> tuple[bool, str, str]:
    row = (
        AITaskProgress.objects
        .filter(task_id=task_id)
        .values_list('cancel_requested', 'cancel_mode', 'status')
        .first()
    )
    if not row:
        return False, CANCEL_MODE_SOFT, ''
    return bool(row[0]), str(row[1] or CANCEL_MODE_SOFT), str(row[2] or '')


# def _task_is_force_cancelled cho biết tác vụ có bị hủy cứng / đã ở trạng thái cancelled không.
# vd: cancel_mode='hard' + cancel_requested -> True.
def _task_is_force_cancelled(task_id) -> bool:
    cancel_requested, cancel_mode, current_status = _task_cancel_snapshot(task_id)
    return current_status == STATUS_CANCELLED or (
        cancel_requested and cancel_mode == CANCEL_MODE_HARD
    )


# def check_cancel để kiểm tra cờ hủy và ném TaskCancelled nếu cần (soft luôn dừng; hard chỉ khi include_hard).
# vd: gọi định kỳ trong vòng lặp dài; user bấm Dừng -> ném TaskCancelled để thoát.
def check_cancel(task_id, *, include_hard: bool = False) -> None:
    """Raise TaskCancelled neu DB co cancel_requested + cancel_mode='soft'."""
    try:
        cancel_requested, cancel_mode, current_status = _task_cancel_snapshot(task_id)
        if current_status == STATUS_CANCELLED and include_hard:
            raise TaskCancelled('Task cancelled by user')
        if cancel_requested and (
            cancel_mode == CANCEL_MODE_SOFT
            or (include_hard and cancel_mode == CANCEL_MODE_HARD)
        ):
            raise TaskCancelled('Task cancelled by user')
    except TaskCancelled:
        raise
    except Exception:
        logger.exception('[ai_tasks] check_cancel failed task_id=%s', task_id)


# def mark_completed để đánh dấu tác vụ hoàn tất 100% + lưu result, rồi flush stream và dọn tài nguyên (trừ khi đã bị cancel).
# vd: OCR xong -> mark_completed(id, {'variables':{...}}).
def mark_completed(task_id, result: Optional[dict] = None) -> None:
    AITaskProgress.objects.filter(task_id=task_id).exclude(status=STATUS_CANCELLED).update(
        status=STATUS_COMPLETED,
        progress_percent=100,
        progress_stage='Hoan tat',
        progress_detail='',
        result=result or {},
        completed_at=timezone.now(),
        error_message='',
    )
    _flush_stream_buffer(task_id, force=True)
    _cleanup_task_resources(task_id)


# def mark_failed để đánh dấu tác vụ thất bại + lưu thông báo lỗi, flush stream và dọn tài nguyên.
# vd: LLM lỗi -> mark_failed(id, 'TimeoutError: ...').
def mark_failed(task_id, error: str) -> None:
    AITaskProgress.objects.filter(task_id=task_id).exclude(status=STATUS_CANCELLED).update(
        status=STATUS_FAILED,
        error_message=str(error or 'Unknown error')[:2000],
        progress_detail=f'Loi: {error}'[:255],
        completed_at=timezone.now(),
    )
    _flush_stream_buffer(task_id, force=True)
    _cleanup_task_resources(task_id)


# def mark_cancelled để đánh dấu tác vụ đã dừng theo yêu cầu, flush stream và dọn tài nguyên.
# vd: user bấm Dừng -> mark_cancelled(id).
def mark_cancelled(task_id) -> None:
    AITaskProgress.objects.filter(task_id=task_id).update(
        status=STATUS_CANCELLED,
        progress_detail='Da dung theo yeu cau',
        completed_at=timezone.now(),
    )
    _flush_stream_buffer(task_id, force=True)
    _cleanup_task_resources(task_id)


# def append_stream_chunk để gom token stream vào buffer in-memory và chỉ ghi DB mỗi ~100ms, tránh ghi nóng liên tục.
# vd: LLM trả từng token -> gộp rồi flush ~10 lần/giây vào streaming_chunks.
def append_stream_chunk(task_id, chunk: str) -> None:
    """Buffer chunk in-memory, flush DB moi 100ms de tranh hot write."""
    if not chunk:
        return
    task_id_str = str(task_id)
    with _stream_lock:
        _stream_buffers.setdefault(task_id_str, []).append(chunk)
        last = _stream_last_flush.get(task_id_str, 0.0)
        now = time.monotonic()
        if (now - last) >= 0.1:
            buf = _stream_buffers.pop(task_id_str, [])
            _stream_last_flush[task_id_str] = now
        else:
            return
    _persist_chunks(task_id_str, buf)


# def _flush_stream_buffer để đẩy nốt buffer token còn lại vào DB (gọi khi kết thúc tác vụ).
# vd: tác vụ xong -> flush phần token chưa kịp ghi.
def _flush_stream_buffer(task_id, force: bool = False) -> None:
    task_id_str = str(task_id)
    with _stream_lock:
        buf = _stream_buffers.pop(task_id_str, [])
        _stream_last_flush.pop(task_id_str, None)
    if buf:
        _persist_chunks(task_id_str, buf)


# def _persist_chunks để nối các chunk token vào streaming_chunks của tác vụ trong DB (có khóa hàng select_for_update).
# vd: ghi thêm ['xin','chao'] vào streaming_chunks.
def _persist_chunks(task_id_str: str, chunks: list[str]) -> None:
    if not chunks:
        return
    try:
        with transaction.atomic():
            task = (
                AITaskProgress.objects
                .select_for_update()
                .filter(task_id=task_id_str)
                .first()
            )
            if not task:
                return
            current = list(task.streaming_chunks or [])
            current.extend(chunks)
            task.streaming_chunks = current
            task.save(update_fields=['streaming_chunks', 'updated_at'])
    except Exception:
        logger.exception('[ai_tasks] persist_chunks failed task_id=%s', task_id_str)


# def register_hard_session để đăng ký một requests.Session nhằm đóng cưỡng bức khi hủy cứng (cắt kết nối HTTP đang chạy).
# vd: trước khi gọi Ollama lâu -> đăng ký session để Dừng cứng đóng được ngay.
def register_hard_session(task_id, session) -> None:
    """Dang ky requests.Session de close tu cancel handler."""
    task_id_str = str(task_id)
    with _hard_sessions_lock:
        _hard_sessions.setdefault(task_id_str, []).append(session)


# def close_hard_session để đóng mọi session đã đăng ký của tác vụ (ngắt kết nối đang treo).
# vd: Dừng cứng -> close_hard_session(id) làm request OCR bị hủy ngay.
def close_hard_session(task_id) -> None:
    task_id_str = str(task_id)
    with _hard_sessions_lock:
        sessions = _hard_sessions.pop(task_id_str, [])
    for session in sessions:
        try:
            session.close()
        except Exception:
            pass


# def _cleanup_task_resources để dọn bộ nhớ tạm (hard session, buffer stream) của tác vụ sau khi kết thúc.
# vd: sau mark_completed/failed/cancelled -> xóa entry in-memory của task.
def _cleanup_task_resources(task_id) -> None:
    task_id_str = str(task_id)
    with _hard_sessions_lock:
        _hard_sessions.pop(task_id_str, None)
    with _stream_lock:
        _stream_buffers.pop(task_id_str, None)
        _stream_last_flush.pop(task_id_str, None)


# def request_cancel để đặt cờ hủy; nếu cancel_mode='hard' thì đóng session và set luôn trạng thái cancelled.
# vd: user bấm Dừng -> request_cancel(id); hard -> dừng ngay, soft -> đợi check_cancel.
def request_cancel(task_id) -> bool:
    """Set flag cancel + close hard session neu cancel_mode=hard."""
    updated = AITaskProgress.objects.filter(task_id=task_id).update(cancel_requested=True)
    if not updated:
        return False
    row = (
        AITaskProgress.objects
        .filter(task_id=task_id)
        .values_list('cancel_mode', 'status')
        .first()
    )
    if row and row[0] == CANCEL_MODE_HARD:
        close_hard_session(task_id)
        AITaskProgress.objects.filter(task_id=task_id).update(
            status=STATUS_CANCELLED,
            progress_detail='Da dung (hard) theo yeu cau',
            completed_at=timezone.now(),
        )
        _flush_stream_buffer(task_id, force=True)
    return True


# def run_in_thread để chạy fn(task_id, ...) trong 1 daemon thread; tự đánh dấu completed/failed/cancelled theo kết quả, có thể map kết quả qua on_success.
# vd: run_in_thread(task, _do_extract_pdf_task, user_id, tmp_path, name).
def run_in_thread(
    task: AITaskProgress,
    fn: Callable,
    *args,
    on_success: Optional[Callable[[Any], dict]] = None,
    **kwargs,
) -> None:
    """
    Spawn daemon thread chay fn(task_id, *args, **kwargs).
    fn co the raise TaskCancelled / Exception. Tu dong mark task accordingly.
    on_success(result_from_fn) -> dict de map ket qua thanh JSON luu vao task.result.
    """

    task_id = task.task_id
    AITaskProgress.objects.filter(task_id=task_id).update(status=STATUS_RUNNING)

    # def _worker là thân thread: gọi fn, map kết quả, rồi mark_completed/cancelled/failed và đóng kết nối DB cũ.
    # vd: fn ném TaskCancelled -> _worker gọi mark_cancelled.
    def _worker():
        try:
            ret = fn(task_id, *args, **kwargs)
            payload = on_success(ret) if on_success else (ret if isinstance(ret, dict) else {'result': ret})
            if _task_is_force_cancelled(task_id):
                mark_cancelled(task_id)
            else:
                mark_completed(task_id, payload)
        except TaskCancelled:
            mark_cancelled(task_id)
        except Exception as exc:
            if _task_is_force_cancelled(task_id):
                mark_cancelled(task_id)
            else:
                logger.exception('[ai_tasks] thread fn failed task_id=%s', task_id)
                mark_failed(task_id, f'{type(exc).__name__}: {exc}')
        finally:
            close_old_connections()

    thread = threading.Thread(
        target=_worker,
        daemon=True,
        name=f'ai_task_{task_id}',
    )
    thread.start()

"""
 > streaming.py là adapter giữa cơ chế streaming callback của LangChain và callback của hệ thống. Nó nhận từng token từ LLM rồi chuyển token đó cho task_runner.py lưu lại, giúp Flutter hiển thị phản hồi AI
  > dần trong khi task vẫn đang chạy.
"""

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:
    try:
        from langchain.callbacks.base import BaseCallbackHandler
    except ImportError:
        # class BaseCallbackHandler (fallback) là lớp rỗng dùng khi không import được BaseCallbackHandler của LangChain, để code vẫn chạy.
        # vd: môi trường thiếu langchain -> StreamingHandler kế thừa lớp rỗng này.
        class BaseCallbackHandler:
            pass


# class StreamingHandler là callback của LangChain để stream từng token LLM sang on_token; nuốt lỗi callback để không vỡ lời gọi LLM.
# vd: gắn vào llm.invoke -> mỗi token sinh ra được đẩy về frontend qua append_stream_chunk.
class StreamingHandler(BaseCallbackHandler):
    """
    LangChain callback stream tung token sang on_token callback.
    Tolerate exception trong callback de khong vo LLM call.
    """

    # def __init__ để lưu các callback on_token/on_finish/on_error và khởi tạo bộ đếm token.
    # vd: StreamingHandler(on_token=lambda t: append_stream_chunk(id, t)).
    def __init__(
        self,
        *,
        on_token: Callable[[str], None],
        on_finish: Callable[[], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ):
        super().__init__()
        self._on_token = on_token
        self._on_finish = on_finish
        self._on_error = on_error
        self.token_count = 0

    # def on_llm_new_token được gọi mỗi khi LLM sinh 1 token: tăng đếm và gọi on_token; nếu on_token ném TaskCancelled thì cho lan ra để dừng stream.
    # vd: token 'xin' -> gọi on_token('xin').
    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        if not token:
            return
        self.token_count += 1
        try:
            self._on_token(token)
        except Exception as exc:
            try:
                from ai_tasks.services.task_runner import TaskCancelled
            except Exception:
                TaskCancelled = None
            if TaskCancelled is not None and isinstance(exc, TaskCancelled):
                raise
            logger.exception('[streaming] on_token failed')

    # def on_llm_end được gọi khi LLM kết thúc: gọi on_finish nếu có.
    # vd: stream xong -> flush buffer token còn lại.
    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        if not self._on_finish:
            return
        try:
            self._on_finish()
        except Exception:
            logger.exception('[streaming] on_finish failed')

    # def on_llm_error được gọi khi LLM lỗi: gọi on_error nếu có.
    # vd: LLM timeout -> báo lỗi cho tác vụ.
    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        if not self._on_error:
            return
        try:
            self._on_error(error)
        except Exception:
            logger.exception('[streaming] on_error failed')

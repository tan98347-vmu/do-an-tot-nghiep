"""
LangChain BaseCallbackHandler de stream LLM token vao task_runner.
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
        class BaseCallbackHandler:
            pass


class StreamingHandler(BaseCallbackHandler):
    """
    LangChain callback stream tung token sang on_token callback.
    Tolerate exception trong callback de khong vo LLM call.
    """

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

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        if not self._on_finish:
            return
        try:
            self._on_finish()
        except Exception:
            logger.exception('[streaming] on_finish failed')

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        if not self._on_error:
            return
        try:
            self._on_error(error)
        except Exception:
            logger.exception('[streaming] on_error failed')

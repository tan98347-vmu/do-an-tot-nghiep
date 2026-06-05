import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkerSlotState:
    slot_number: int
    enabled: bool
    status: str = 'idle'
    current_job: dict[str, Any] | None = None
    last_error: str = ''
    disable_reason: str = ''
    failure_count: int = 0
    last_failure_category: str = ''
    metadata: dict[str, Any] = field(default_factory=dict)
    runner_thread: Any = field(default=None, repr=False, compare=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False, compare=False)

    @property
    def label(self):
        return f'slot-{self.slot_number}'

    @property
    def worker_key(self):
        return f'direct-host.{self.label}'

    def is_claim_enabled(self):
        with self._lock:
            return self.enabled and not self.disable_reason

    def snapshot(self):
        with self._lock:
            return {
                'slot': self.label,
                'status': self.status,
                'current_job': self.current_job,
                'last_error': self.last_error,
                'disable_reason': self.disable_reason,
                'failure_count': self.failure_count,
                'last_failure_category': self.last_failure_category,
                'metadata': dict(self.metadata),
                'enabled': self.enabled,
                'claim_enabled': self.enabled and not self.disable_reason,
                'has_runner': bool(self.runner_thread and self.runner_thread.is_alive()),
            }

    def attach_runner(self, runner_thread, job):
        with self._lock:
            self.runner_thread = runner_thread
            self.current_job = job
            self.status = 'claimed'
            self.last_error = ''

    def mark_editing(self):
        with self._lock:
            self.status = 'editing'

    def mark_uploading(self):
        with self._lock:
            self.status = 'uploading'

    def mark_paused(self, reason, metadata=None):
        with self._lock:
            self.status = 'paused'
            self.metadata = {'pause_reason': reason, **(metadata or {})}

    def mark_idle(self):
        with self._lock:
            self.current_job = None
            self.runner_thread = None
            self.status = 'paused' if self.disable_reason else 'idle'

    def mark_error(self, detail):
        with self._lock:
            self.last_error = str(detail)

    def register_success(self):
        with self._lock:
            self.failure_count = 0
            self.last_failure_category = ''
            if self.disable_reason == 'slot2_auto_fallback':
                self.disable_reason = ''
                self.metadata.pop('pause_reason', None)
                self.metadata.pop('slot2_fallback_reason', None)
                if self.current_job is None:
                    self.status = 'idle'

    def register_failure(self, *, detail, category, fallback_to_single_slot):
        with self._lock:
            self.last_error = str(detail)
            self.failure_count += 1
            self.last_failure_category = category
            self.metadata.update(
                {
                    'failure_count': self.failure_count,
                    'failure_category': category,
                }
            )
            if fallback_to_single_slot:
                self.disable_reason = 'slot2_auto_fallback'
                self.status = 'paused'
                self.metadata.update(
                    {
                        'pause_reason': 'slot2_auto_fallback',
                        'slot2_fallback_reason': category,
                    }
                )

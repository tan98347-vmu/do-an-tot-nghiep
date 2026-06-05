import socket
import time

from word_worker_agent.backend_client import BackendClient
from word_worker_agent.config import load_agent_config
from word_worker_agent.logging import configure_logging, log_event
from word_worker_agent.resource_guard import can_claim_slot
from word_worker_agent.slot_state import WorkerSlotState
from word_worker_agent.slot_runner import SlotRunner


class WordWorkerMaster:
    def __init__(self):
        configure_logging()
        self.config = load_agent_config()
        self.backend = BackendClient(
            base_url=self.config.backend_base_url,
            worker_token=self.config.worker_token,
        )
        self.host_name = socket.gethostname()
        self.slots = {
            slot_number: WorkerSlotState(
                slot_number=slot_number,
                enabled=slot_number <= self.config.enabled_worker_slots,
            )
            for slot_number in range(1, self.config.max_worker_slots + 1)
        }

    def resolve_slot(self, slot_number):
        return self.slots[slot_number]

    def poll_once(self):
        for slot_number, slot in self.slots.items():
            if not slot.enabled:
                continue
            if not slot.is_claim_enabled():
                slot.mark_paused(
                    slot.disable_reason,
                    {
                        **slot.metadata,
                        'disable_reason': slot.disable_reason,
                    },
                )
                self.backend.heartbeat(
                    worker_key=slot.worker_key,
                    slot_label=slot.label,
                    status=slot.snapshot()['status'],
                    metadata=slot.snapshot()['metadata'],
                    current_job_id=slot.current_job.get('id') if slot.current_job else None,
                )
                continue
            can_claim, snapshot, reason = can_claim_slot(self.config, slot_number)
            metadata = {'free_ram_mb': snapshot.free_ram_mb}
            if not can_claim:
                slot.mark_paused(reason, metadata)
                self.backend.heartbeat(
                    worker_key=slot.worker_key,
                    slot_label=slot.label,
                    status=slot.snapshot()['status'],
                    metadata=slot.snapshot()['metadata'],
                    current_job_id=slot.current_job.get('id') if slot.current_job else None,
                )
                continue
            if slot.current_job is None and not (slot.runner_thread and slot.runner_thread.is_alive()):
                slot.status = 'idle'
            slot.metadata = metadata
            self.backend.heartbeat(
                worker_key=slot.worker_key,
                slot_label=slot.label,
                status=slot.status,
                metadata=slot.metadata,
                current_job_id=slot.current_job.get('id') if slot.current_job else None,
            )
            if slot.current_job is not None:
                continue
            claim_response = self.backend.claim_job(
                worker_key=slot.worker_key,
                slot_label=slot.label,
                host_name=self.host_name,
                metadata=metadata,
            )
            claimed_job = claim_response.get('job')
            if claimed_job:
                SlotRunner(
                    config=self.config,
                    backend=self.backend,
                    slot=slot,
                    host_name=self.host_name,
                ).start(claimed_job)

    def run_forever(self, *, poll_interval_seconds=10):
        log_event(
            'info',
            component='word_worker_agent.master',
            step='startup',
            status='running',
            message='Word worker master loop started.',
            payload={
                'max_worker_slots': self.config.max_worker_slots,
                'enabled_worker_slots': self.config.enabled_worker_slots,
            },
        )
        while True:
            self.poll_once()
            time.sleep(poll_interval_seconds)

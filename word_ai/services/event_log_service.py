from word_ai.logging import log_structured
from word_ai.models import WordEditJobEvent


def append_job_event(
    job,
    *,
    step,
    status='',
    message='',
    payload=None,
    worker=None,
    level='info',
):
    event = WordEditJobEvent.objects.create(
        job=job,
        worker=worker,
        level=level,
        step=step,
        status=status,
        message=message,
        payload=payload or {},
    )
    log_structured(
        'info' if level not in {'warning', 'error'} else level,
        component='word_ai.backend',
        job_id=job.id,
        document_id=job.document_id,
        worker_id=getattr(worker, 'id', None),
        worker_slot=getattr(worker, 'slot_label', None),
        step=step,
        status=status,
        message=message,
        payload=payload or {},
    )
    return event

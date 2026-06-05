import json
import logging
from datetime import UTC, datetime


LOGGER = logging.getLogger('word_worker_agent')


def configure_logging():
    if LOGGER.handlers:
        return LOGGER
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False
    return LOGGER


def log_event(
    level,
    *,
    component,
    step='',
    status='',
    message='',
    job_id=None,
    document_id=None,
    worker_slot='',
    error_code='',
    payload=None,
):
    configure_logging()
    body = {
        'timestamp': datetime.now(UTC).isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
        'level': level,
        'component': component,
        'step': step,
        'status': status,
        'message': message,
        'job_id': job_id,
        'document_id': document_id,
        'worker_slot': worker_slot,
        'error_code': error_code or None,
        'payload': payload or {},
    }
    line = json.dumps({key: value for key, value in body.items() if value is not None}, ensure_ascii=True, sort_keys=True)
    getattr(LOGGER, level, LOGGER.info)(line)
    return body

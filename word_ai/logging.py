import json
import logging
from datetime import datetime


LOGGER = logging.getLogger('word_ai')


def build_log_payload(**kwargs):
    payload = {
        'timestamp': datetime.utcnow().isoformat(timespec='milliseconds') + 'Z',
        **{key: value for key, value in kwargs.items() if value is not None},
    }
    return payload


def log_structured(log_level, **kwargs):
    payload = build_log_payload(level=log_level, **kwargs)
    line = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    getattr(LOGGER, log_level, LOGGER.info)(line)
    return payload

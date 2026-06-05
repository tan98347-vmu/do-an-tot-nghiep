MODAL_DIALOG_MARKERS = (
    'modal',
    'dialog',
    'popup',
)

SHARED_SESSION_COLLISION_MARKERS = (
    'rpc_e_call_rejected',
    'call was rejected by callee',
    'server threw an exception',
    'word is busy',
    'application is busy',
    'another command is already in progress',
)


def classify_worker_failure(error_code, detail):
    text = f'{error_code}\n{detail}'.lower()
    if any(marker in text for marker in MODAL_DIALOG_MARKERS):
        return 'modal_dialog_interference'
    if any(marker in text for marker in SHARED_SESSION_COLLISION_MARKERS):
        return 'shared_session_collision'
    return 'runtime_failure'


def slot2_should_fallback(config, *, slot_number, failure_count, failure_category):
    if slot_number != 2:
        return False
    if failure_category in {'shared_session_collision', 'modal_dialog_interference'}:
        return True
    return failure_count >= config.slot2_failure_threshold

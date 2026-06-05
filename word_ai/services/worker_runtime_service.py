from datetime import timedelta

from django.utils import timezone

from word_ai.models import WordWorker


ACTIVE_WORKER_MAX_AGE_SECONDS = 60


def active_word_worker_count(*, max_age_seconds=ACTIVE_WORKER_MAX_AGE_SECONDS):
    cutoff = timezone.now() - timedelta(seconds=max_age_seconds)
    return WordWorker.objects.filter(last_seen_at__gte=cutoff).count()


def has_active_word_worker(*, max_age_seconds=ACTIVE_WORKER_MAX_AGE_SECONDS):
    return active_word_worker_count(max_age_seconds=max_age_seconds) > 0

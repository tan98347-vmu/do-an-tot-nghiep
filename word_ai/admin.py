from django.contrib import admin

from .models import WordEditJob, WordEditJobEvent, WordWorker


@admin.register(WordWorker)
class WordWorkerAdmin(admin.ModelAdmin):
    list_display = ('worker_key', 'slot_label', 'status', 'host_name', 'last_seen_at')
    search_fields = ('worker_key', 'slot_label', 'host_name')
    list_filter = ('status',)


class WordEditJobEventInline(admin.TabularInline):
    model = WordEditJobEvent
    extra = 0
    can_delete = False
    readonly_fields = ('created_at', 'worker', 'level', 'step', 'status', 'message', 'payload')


@admin.register(WordEditJob)
class WordEditJobAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'document',
        'status',
        'requested_by',
        'current_slot_label',
        'llm_model_name',
        'created_at',
    )
    list_filter = ('status', 'track_changes', 'current_slot_label')
    search_fields = ('document__title', 'requested_by__username', 'instruction', 'error_code')
    readonly_fields = ('created_at', 'updated_at', 'claimed_at', 'completed_at', 'failed_at', 'cancelled_at')
    inlines = [WordEditJobEventInline]

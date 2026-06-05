from django.contrib import admin

from .models import AITaskProgress


@admin.register(AITaskProgress)
class AITaskProgressAdmin(admin.ModelAdmin):
    list_display = (
        'task_id',
        'task_type',
        'title_summary',
        'status',
        'progress_percent',
        'user',
        'created_at',
    )
    list_filter = ('task_type', 'status', 'cancel_mode', 'user')
    search_fields = (
        'task_id',
        'title_summary',
        'client_request_id',
        'user__username',
        'progress_stage',
        'progress_detail',
    )
    readonly_fields = tuple(f.name for f in AITaskProgress._meta.fields)
    ordering = ('-created_at',)

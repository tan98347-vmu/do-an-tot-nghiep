from django.contrib import admin

from .models import ShareGrant


@admin.register(ShareGrant)
class ShareGrantAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'content_type',
        'object_id',
        'scope',
        'permission_level',
        'target_user',
        'target_group',
        'approval_status',
        'created_at',
    )
    list_filter = ('scope', 'permission_level', 'approval_status', 'content_type')
    search_fields = ('object_id', 'target_user__username', 'target_group__name')
    raw_id_fields = ('target_user', 'target_group', 'created_by', 'approved_by', 'submitted_by')
    readonly_fields = ('created_at', 'updated_at', 'submitted_at', 'approved_at')

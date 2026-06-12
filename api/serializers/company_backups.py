from rest_framework import serializers

from company_backups.models import CompanyBackup, CompanyBackupSettings


# class CompanyBackupSerializer là serializer định nghĩa dữ liệu vào/ra (CompanyBackup).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class CompanyBackupSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    restored_by_name = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    is_encrypted = serializers.SerializerMethodField()
    encryption_algorithm = serializers.SerializerMethodField()
    has_signature = serializers.SerializerMethodField()

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        model = CompanyBackup
        fields = (
            'id', 'name', 'kind', 'components',
            'size_bytes', 'status', 'manifest',
            'progress_percent', 'progress_stage', 'progress_detail',
            'created_by', 'created_by_name', 'created_at', 'completed_at',
            'downloaded_at', 'restored_at', 'restored_by', 'restored_by_name',
            'error_message', 'download_url',
            'signature_status', 'is_encrypted', 'encryption_algorithm', 'has_signature',
        )
        read_only_fields = fields

    # def get_created_by_name để lấy created by name (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_created_by_name(self, obj):
        u = obj.created_by
        if not u:
            return ''
        return u.get_full_name() or u.username

    # def get_restored_by_name để lấy restored by name (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_restored_by_name(self, obj):
        u = obj.restored_by
        if not u:
            return ''
        return u.get_full_name() or u.username

    # def get_download_url để lấy download url (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_download_url(self, obj):
        return f'/api/admin/backups/{obj.pk}/download/'

    # def get_is_encrypted để lấy is encrypted (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_is_encrypted(self, obj):
        return bool(obj.encryption_meta)

    # def get_encryption_algorithm để lấy encryption algorithm (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_encryption_algorithm(self, obj):
        if not obj.encryption_meta:
            return ''
        return obj.encryption_meta.get('alg', '')

    # def get_has_signature để lấy has signature (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_has_signature(self, obj):
        return bool(obj.signature_path)


# class CompanyBackupSettingsSerializer là serializer định nghĩa dữ liệu vào/ra (CompanyBackupSettings).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class CompanyBackupSettingsSerializer(serializers.ModelSerializer):
    has_password = serializers.SerializerMethodField()

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        model = CompanyBackupSettings
        fields = (
            'auto_enabled', 'auto_interval_days', 'retention_count',
            'notify_admin_email', 'last_auto_run_at',
            'has_password', 'created_at', 'updated_at',
        )
        read_only_fields = ('last_auto_run_at', 'has_password', 'created_at', 'updated_at')

    # def get_has_password để lấy has password (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_has_password(self, obj):
        return bool(obj.backup_password_hash)

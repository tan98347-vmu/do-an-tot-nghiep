from rest_framework import serializers


# class DocumentSummaryRequestSerializer là serializer định nghĩa dữ liệu vào/ra (DocumentSummaryRequest).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class DocumentSummaryRequestSerializer(serializers.Serializer):
    options = serializers.JSONField(required=False)
    user_extra_rules = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
    )
    preview_token = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
    )
    prompt_check_token = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
    )
    prompt_id = serializers.IntegerField(required=False, min_value=1)


# class DocumentSummaryDownloadQuerySerializer là serializer định nghĩa dữ liệu vào/ra (DocumentSummaryDownloadQuery).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class DocumentSummaryDownloadQuerySerializer(serializers.Serializer):
    format = serializers.CharField(required=True)

    # def validate_format để kiểm tra hợp lệ format (trong serializer).
    # vd: nhận tham số đầu vào -> trả cấu trúc dữ liệu/chuỗi đã dựng.
    def validate_format(self, value):
        normalized = str(value or '').strip().lower()
        if not normalized:
            raise serializers.ValidationError('format is required')
        if normalized not in {'docx', 'md'}:
            raise serializers.ValidationError("format must be 'docx' or 'md'.")
        return normalized

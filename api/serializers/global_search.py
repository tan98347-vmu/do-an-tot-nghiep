from rest_framework import serializers

ALL_SEARCH_TYPES = (
    'template',
    'document',
    'prompt',
    'summary',
    'conversation',
)


class GlobalSearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(max_length=200, trim_whitespace=True)
    types = serializers.CharField(required=False, allow_blank=True)

    def validate_q(self, value):
        query = str(value or '').strip()
        if not query:
            raise serializers.ValidationError('Tham so q bat buoc.')
        if len(query) < 2:
            raise serializers.ValidationError('q phai co it nhat 2 ky tu.')
        return query[:200]

    def validate_types(self, value):
        raw = str(value or '').strip().lower()
        if not raw:
            return []

        parsed = []
        invalid = []
        for item in raw.split(','):
            search_type = item.strip()
            if not search_type:
                continue
            if search_type not in ALL_SEARCH_TYPES:
                invalid.append(search_type)
                continue
            if search_type not in parsed:
                parsed.append(search_type)
        if invalid:
            raise serializers.ValidationError(
                f'types khong hop le: {", ".join(invalid)}'
            )
        return parsed

    def validate(self, attrs):
        attrs['types'] = attrs.get('types') or list(ALL_SEARCH_TYPES)
        return attrs


class GlobalSearchItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    type = serializers.ChoiceField(choices=ALL_SEARCH_TYPES)
    title = serializers.CharField()
    snippet = serializers.CharField(allow_blank=True)
    deeplink = serializers.CharField()
    updated_at = serializers.DateTimeField()


class GlobalSearchResultsSerializer(serializers.Serializer):
    template = GlobalSearchItemSerializer(many=True, required=False)
    document = GlobalSearchItemSerializer(many=True, required=False)
    prompt = GlobalSearchItemSerializer(many=True, required=False)
    summary = GlobalSearchItemSerializer(many=True, required=False)
    conversation = GlobalSearchItemSerializer(many=True, required=False)


class GlobalSearchResponseSerializer(serializers.Serializer):
    results = GlobalSearchResultsSerializer()
    took_ms = serializers.IntegerField(min_value=0)

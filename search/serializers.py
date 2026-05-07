# search/serializers.py

from rest_framework import serializers
from .models import SearchResult


class WebhookPayloadSerializer(serializers.Serializer):
    """Validates incoming webhook from Azure."""

    batch_id = serializers.UUIDField()
    status = serializers.ChoiceField(
        choices=['complete', 'failed']
    )
    error_message = serializers.CharField(
        required=False,
        allow_blank=True,
        default=''
    )
    results = serializers.ListField(
        required=False,
        child=serializers.DictField(),
        allow_empty=True,
        default=[]
    )

    def validate_results(self, results):
        if not results:
            return results

        errors = []
        for index, result in enumerate(results):
            result_errors = []

            if 'candidate_id' not in result:
                result_errors.append('Missing candidate_id.')

            if 'score' not in result:
                result_errors.append('Missing score.')
            else:
                try:
                    score = float(result['score'])
                    if not (0 <= score <= 1):
                        result_errors.append('Score must be between 0 and 1.')
                except (ValueError, TypeError):
                    result_errors.append('Score must be a number.')

            if result_errors:
                errors.append({
                    'index': index,
                    'errors': result_errors,
                })

        if errors:
            raise serializers.ValidationError(errors)

        return results


class SearchResultSerializer(serializers.ModelSerializer):
    """List view — compact."""

    batch_id = serializers.UUIDField(
        source='batch.id',
        read_only=True
    )

    class Meta:
        model = SearchResult
        fields = [
            'id',
            'batch_id',
            'candidate_id',
            'score',
            'rank',
            'received_at',
        ]
        read_only_fields = fields


class SearchResultDetailSerializer(serializers.ModelSerializer):
    """Detail view — includes batch info."""

    batch_id = serializers.UUIDField(
        source='batch.id',
        read_only=True
    )
    job_description = serializers.CharField(
        source='batch.job_description',
        read_only=True
    )
    search_all = serializers.BooleanField(
        source='batch.search_all',
        read_only=True
    )

    class Meta:
        model = SearchResult
        fields = [
            'id',
            'batch_id',
            'job_description',
            'search_all',
            'candidate_id',
            'score',
            'rank',
            'received_at',
        ]
        read_only_fields = fields
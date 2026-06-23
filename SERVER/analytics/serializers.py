from rest_framework import serializers

from knowledge_base.models import KnowledgeBase

from .models import ConversationMetrics, UnansweredQuestion


class ConversationMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationMetrics
        fields = [
            "date",
            "total_conversations",
            "resolved_by_ai",
            "resolved_by_agent",
            "escalated_chats",
            "avg_response_time",
            "avg_resolution_time",
            "top_questions",
            "unanswered_questions",
        ]
        read_only_fields = fields


class UnansweredQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnansweredQuestion
        fields = [
            "uuid",
            "question",
            "occurrence_count",
            "is_resolved",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ConvertToFaqSerializer(serializers.Serializer):
    knowledge_base = serializers.SlugRelatedField(
        slug_field="uuid", queryset=KnowledgeBase.objects.all()
    )
    answer = serializers.CharField()

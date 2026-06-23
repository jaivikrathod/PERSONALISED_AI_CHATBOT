from rest_framework import serializers

from .models import KnowledgeBase, QuestionAnswer


class KnowledgeBaseSerializer(serializers.ModelSerializer):
    qa_count = serializers.IntegerField(source="qa_pairs.count", read_only=True)

    class Meta:
        model = KnowledgeBase
        fields = [
            "uuid",
            "title",
            "description",
            "is_active",
            "qa_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["uuid", "qa_count", "created_at", "updated_at"]


class QuestionAnswerSerializer(serializers.ModelSerializer):
    knowledge_base = serializers.SlugRelatedField(
        slug_field="uuid", queryset=KnowledgeBase.objects.all()
    )

    class Meta:
        model = QuestionAnswer
        fields = [
            "uuid",
            "knowledge_base",
            "question",
            "answer",
            "embedding_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["uuid", "embedding_status", "created_at", "updated_at"]


class FaqSerializer(serializers.ModelSerializer):
    """Flat FAQ representation for the dashboard.

    Hides the parent KnowledgeBase entirely and exposes the integer ``id`` the
    frontend uses for row keys and edit/delete URLs.
    """

    class Meta:
        model = QuestionAnswer
        fields = ["id", "question", "answer", "embedding_status", "created_at", "updated_at"]
        read_only_fields = ["id", "embedding_status", "created_at", "updated_at"]


class BulkUploadSerializer(serializers.Serializer):
    knowledge_base = serializers.SlugRelatedField(
        slug_field="uuid", queryset=KnowledgeBase.objects.all()
    )
    file = serializers.FileField()

    def validate_file(self, value):
        if not value.name.lower().endswith((".csv", ".xlsx", ".xls")):
            raise serializers.ValidationError("Only CSV or Excel files are accepted.")
        return value


class SearchSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=1000)
    top_k = serializers.IntegerField(required=False, min_value=1, max_value=20, default=5)

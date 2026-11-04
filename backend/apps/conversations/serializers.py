from rest_framework import serializers

from apps.matters.models import Matter

from .models import Citation, Conversation, Message


class CitationSerializer(serializers.ModelSerializer):
    excerpt = serializers.SerializerMethodField()

    class Meta:
        model = Citation
        fields = ["number", "used", "document", "document_title", "page_number", "score", "excerpt"]

    def get_excerpt(self, obj):
        if obj.chunk is None:
            return None  # source document was deleted
        return obj.chunk.content  # bounded by RAG_CHUNK_SIZE


class MessageSerializer(serializers.ModelSerializer):
    citations = CitationSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = [
            "id",
            "role",
            "content",
            "insufficient_context",
            "model_name",
            "latency_ms",
            "created_at",
            "citations",
        ]


class ConversationSerializer(serializers.ModelSerializer):
    matter = serializers.PrimaryKeyRelatedField(
        queryset=Matter.objects.none(), allow_null=True, required=False
    )
    matter_name = serializers.CharField(source="matter.name", read_only=True, default=None)

    class Meta:
        model = Conversation
        fields = ["id", "title", "matter", "matter_name", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["matter"].queryset = self.context.get("matter_queryset", Matter.objects.none())


class ConversationDetailSerializer(ConversationSerializer):
    messages = serializers.SerializerMethodField()

    class Meta(ConversationSerializer.Meta):
        fields = [*ConversationSerializer.Meta.fields, "messages"]

    def get_messages(self, obj):
        qs = obj.messages.prefetch_related("citations__chunk")
        return MessageSerializer(qs, many=True).data


class AskSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=4000, trim_whitespace=True)

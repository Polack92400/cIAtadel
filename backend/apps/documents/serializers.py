from rest_framework import serializers

from apps.matters.models import Matter

from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    matter_name = serializers.CharField(source="matter.name", read_only=True, default=None)
    uploaded_by_email = serializers.EmailField(
        source="uploaded_by.email", read_only=True, default=None
    )
    matter = serializers.PrimaryKeyRelatedField(
        queryset=Matter.objects.none(), allow_null=True, required=False
    )

    class Meta:
        model = Document
        # storage_key and sha256 are deliberately absent.
        fields = [
            "id",
            "title",
            "original_filename",
            "size_bytes",
            "status",
            "error_code",
            "error_message",
            "page_count",
            "chunk_count",
            "matter",
            "matter_name",
            "uploaded_by_email",
            "created_at",
            "processed_at",
        ]
        read_only_fields = [f for f in fields if f not in ("title", "matter")]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["matter"].queryset = self.context.get("matter_queryset", Matter.objects.none())


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    matter = serializers.PrimaryKeyRelatedField(
        queryset=Matter.objects.none(), allow_null=True, required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["matter"].queryset = self.context.get("matter_queryset", Matter.objects.none())

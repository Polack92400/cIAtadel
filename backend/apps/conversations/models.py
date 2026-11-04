import uuid

from django.db import models

from apps.core.models import TenantOwnedModel


class Conversation(TenantOwnedModel):
    """Private to its creator within the firm."""

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="+")
    title = models.CharField(max_length=200, default="New conversation")
    matter = models.ForeignKey(
        "matters.Matter", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["tenant", "user", "-updated_at"])]


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user"
        ASSISTANT = "assistant"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="+")
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    insufficient_context = models.BooleanField(default=False)
    model_name = models.CharField(max_length=100, blank=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.role}: {self.content[:40]}"


class Citation(models.Model):
    """Link from an answer to a source passage. Only a title snapshot is
    stored: if the document is deleted its text disappears with it."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="+")
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="citations")
    number = models.PositiveSmallIntegerField()
    used = models.BooleanField(default=False)
    document = models.ForeignKey(
        "documents.Document", null=True, on_delete=models.SET_NULL, related_name="+"
    )
    chunk = models.ForeignKey(
        "rag.DocumentChunk", null=True, on_delete=models.SET_NULL, related_name="+"
    )
    document_title = models.CharField(max_length=255)
    page_number = models.PositiveIntegerField(null=True, blank=True)
    score = models.FloatField(null=True)

    class Meta:
        ordering = ["number"]

    def __str__(self) -> str:
        return f"[{self.number}] {self.document_title}"

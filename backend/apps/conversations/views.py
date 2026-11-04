from rest_framework import exceptions, generics, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.ai_engine.providers import ProviderError
from apps.audit import service as audit
from apps.audit.models import AuditEvent
from apps.core.exceptions import ServiceUnavailable
from apps.core.permissions import TenantScopedMixin
from apps.matters.models import accessible_matters

from . import assistant
from .models import Conversation
from .serializers import (
    AskSerializer,
    ConversationDetailSerializer,
    ConversationSerializer,
    MessageSerializer,
)

CONV = AuditEvent.Category.CONVERSATION


class ConversationScopeMixin(TenantScopedMixin):
    def my_conversations(self):
        # Tenant AND owner: colleagues cannot read each other's chats.
        return (
            Conversation.objects.for_tenant(self.tenant)
            .filter(user=self.request.user)
            .select_related("matter")
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["matter_queryset"] = accessible_matters(self.membership)
        return ctx


class ConversationListCreateView(ConversationScopeMixin, generics.ListCreateAPIView):
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return self.my_conversations()

    def perform_create(self, serializer):
        conv = serializer.save(tenant=self.tenant, user=self.request.user)
        audit.record("conversation.created", category=CONV, request=self.request, target=conv)


class ConversationDetailView(ConversationScopeMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ConversationDetailSerializer
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self):
        return self.my_conversations()

    def perform_destroy(self, instance):
        audit.record(
            "conversation.deleted",
            category=CONV,
            request=self.request,
            target=instance,
            target_label=instance.title,
        )
        instance.delete()


class AskView(ConversationScopeMixin, APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ask"

    def post(self, request, pk):
        conv = generics.get_object_or_404(self.my_conversations(), pk=pk)
        if (
            conv.matter_id
            and not accessible_matters(self.membership).filter(pk=conv.matter_id).exists()
        ):
            raise exceptions.NotFound()
        ser = AskSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            msg = assistant.answer(
                conversation=conv,
                membership=self.membership,
                question=ser.validated_data["content"],
            )
        except ProviderError as exc:
            raise ServiceUnavailable(
                "The AI service is unavailable. Please try again in a moment."
            ) from exc
        audit.record(
            "assistant.question",
            category=CONV,
            request=request,
            target=conv,
            sources=[str(c.document_id) for c in msg.citations.all() if c.used],
        )
        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)

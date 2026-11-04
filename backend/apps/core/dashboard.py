from django.db.models import Count
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.conversations.models import Conversation
from apps.conversations.serializers import ConversationSerializer
from apps.documents.models import Document
from apps.documents.serializers import DocumentSerializer
from apps.matters.models import accessible_matters, matter_scope_q

from .permissions import TenantScopedMixin


class DashboardView(TenantScopedMixin, APIView):
    def get(self, request):
        docs = Document.objects.for_tenant(self.tenant).filter(matter_scope_q(self.membership))
        by_status = {s: 0 for s in Document.Status.values}
        for row in docs.values("status").annotate(n=Count("id")):
            by_status[row["status"]] = row["n"]
        recent_docs = docs.select_related("matter", "uploaded_by")[:6]
        convs = Conversation.objects.for_tenant(self.tenant).filter(user=request.user)
        ctx = {"request": request, "matter_queryset": accessible_matters(self.membership)}
        return Response(
            {
                "tenant": {"id": str(self.tenant.id), "name": self.tenant.name},
                "role": self.membership.role,
                "documents_by_status": by_status,
                "document_total": sum(by_status.values()),
                "matter_count": accessible_matters(self.membership).count(),
                "conversation_count": convs.count(),
                "recent_documents": DocumentSerializer(recent_docs, many=True, context=ctx).data,
                "recent_conversations": ConversationSerializer(
                    convs.select_related("matter")[:6], many=True, context=ctx
                ).data,
            }
        )

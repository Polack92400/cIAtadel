from django.db.models import Q
from django.http import StreamingHttpResponse
from rest_framework import exceptions, generics, status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.roles import Role, role_at_least
from apps.audit import service as audit
from apps.audit.models import AuditEvent
from apps.core.permissions import TenantScopedMixin
from apps.matters.models import accessible_matters, matter_scope_q

from . import services
from .models import Document
from .serializers import DocumentSerializer, DocumentUploadSerializer
from .storage import get_storage
from .validation import read_and_validate_pdf, safe_display_name

DOC = AuditEvent.Category.DOCUMENT


class DocumentScopeMixin(TenantScopedMixin):
    def visible_documents(self):
        """Tenant filter + matter-level restrictions. Single source of truth
        for every document endpoint (list, detail, download, delete)."""
        return (
            Document.objects.for_tenant(self.tenant)
            .filter(matter_scope_q(self.membership))
            .select_related("matter", "uploaded_by")
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["matter_queryset"] = accessible_matters(self.membership)
        return ctx


class DocumentListCreateView(DocumentScopeMixin, generics.ListAPIView):
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser]

    def get_queryset(self):
        qs = self.visible_documents()
        params = self.request.query_params
        if q := params.get("search", "").strip():
            qs = qs.filter(Q(title__icontains=q) | Q(original_filename__icontains=q))
        if st := params.get("status"):
            qs = qs.filter(status=st)
        if matter := params.get("matter"):
            if matter == "none":
                qs = qs.filter(matter__isnull=True)
            elif _is_uuid(matter):
                qs = qs.filter(matter_id=matter)
            else:
                qs = qs.none()
        return qs

    def post(self, request):
        ser = DocumentUploadSerializer(data=request.data, context=self.get_serializer_context())
        ser.is_valid(raise_exception=True)
        upload = ser.validated_data["file"]
        data, sha = read_and_validate_pdf(upload)
        filename = safe_display_name(upload.name)
        title = (ser.validated_data.get("title") or "").strip() or filename.rsplit(".", 1)[0]
        try:
            doc = services.create_document(
                tenant=self.tenant,
                user=request.user,
                matter=ser.validated_data.get("matter"),
                title=title,
                filename=filename,
                data=data,
                sha256=sha,
            )
        except services.DuplicateDocument as dup:
            visible = self.visible_documents().filter(pk=dup.existing.pk).exists()
            return Response(
                {
                    "error": {
                        "status": 409,
                        "detail": "This file already exists in your firm.",
                        "existing_id": str(dup.existing.pk) if visible else None,
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )
        audit.record(
            "document.uploaded",
            category=DOC,
            request=request,
            target=doc,
            target_label=doc.title,
            size_bytes=doc.size_bytes,
        )
        return Response(
            DocumentSerializer(doc, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )


class DocumentDetailView(DocumentScopeMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DocumentSerializer
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self):
        return self.visible_documents()

    def perform_update(self, serializer):
        doc = serializer.save()
        # Keep denormalised matter on chunks in sync for retrieval filtering.
        doc.chunks.update(matter=doc.matter)
        audit.record(
            "document.updated",
            category=DOC,
            request=self.request,
            target=doc,
            target_label=doc.title,
        )

    def perform_destroy(self, instance):
        is_admin = role_at_least(self.membership.role, Role.ADMIN)
        if not is_admin and instance.uploaded_by_id != self.request.user.id:
            raise exceptions.PermissionDenied("Only the uploader or an admin can delete this.")
        audit.record(
            "document.deleted",
            category=DOC,
            request=self.request,
            target=instance,
            target_label=instance.title,
        )
        services.delete_document(instance)


class DocumentDownloadView(DocumentScopeMixin, APIView):
    def get(self, request, pk):
        doc = generics.get_object_or_404(self.visible_documents(), pk=pk)
        audit.record(
            "document.downloaded", category=DOC, request=request, target=doc, target_label=doc.title
        )
        response = StreamingHttpResponse(
            get_storage().stream(doc.storage_key), content_type="application/pdf"
        )
        filename = doc.original_filename.replace('"', "")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Content-Length"] = str(doc.size_bytes)
        response["Cache-Control"] = "private, no-store"
        return response


class DocumentReprocessView(DocumentScopeMixin, APIView):
    min_role_write = Role.ADMIN

    def post(self, request, pk):
        doc = generics.get_object_or_404(self.visible_documents(), pk=pk)
        doc.status = Document.Status.PENDING
        doc.error_code = doc.error_message = ""
        doc.save(update_fields=["status", "error_code", "error_message", "updated_at"])
        services.queue_processing(doc)
        audit.record(
            "document.reprocess", category=DOC, request=request, target=doc, target_label=doc.title
        )
        return Response(
            DocumentSerializer(doc, context=self.get_serializer_context()).data,
            status=status.HTTP_202_ACCEPTED,
        )


def _is_uuid(value: str) -> bool:
    import uuid

    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False

from django.urls import path

from . import views

urlpatterns = [
    path("documents", views.DocumentListCreateView.as_view(), name="document-list"),
    path("documents/<uuid:pk>", views.DocumentDetailView.as_view(), name="document-detail"),
    path(
        "documents/<uuid:pk>/download",
        views.DocumentDownloadView.as_view(),
        name="document-download",
    ),
    path(
        "documents/<uuid:pk>/reprocess",
        views.DocumentReprocessView.as_view(),
        name="document-reprocess",
    ),
]

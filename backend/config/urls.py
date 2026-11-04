from django.urls import include, path

# All application routes live under /api/v1/. The Next.js frontend reaches
# them through its own server-side rewrite so that auth cookies stay
# same-origin; nothing else (PostgreSQL, MinIO, Ollama) is reachable from it.
api_v1 = [
    path("", include("apps.core.urls")),
    path("", include("apps.accounts.urls")),
    path("", include("apps.tenants.urls")),
    path("", include("apps.matters.urls")),
    path("", include("apps.documents.urls")),
    path("", include("apps.conversations.urls")),
    path("", include("apps.audit.urls")),
]

urlpatterns = [
    path("api/v1/", include(api_v1)),
]

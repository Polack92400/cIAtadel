from django.urls import include, path

# All application routes live under /api/v1/. The Next.js frontend reaches
# them through its own server-side rewrite so that auth cookies stay
# same-origin; nothing else (PostgreSQL, MinIO, Ollama) is reachable from it.
api_v1 = [
    path("", include("apps.core.urls")),
]

urlpatterns = [
    path("api/v1/", include(api_v1)),
]

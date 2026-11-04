from django.urls import path

from . import views
from .dashboard import DashboardView

urlpatterns = [
    path("health/live", views.liveness, name="health-live"),
    path("health/ready", views.readiness, name="health-ready"),
    path("dashboard", DashboardView.as_view(), name="dashboard"),
]

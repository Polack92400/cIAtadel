from django.urls import path

from . import views

urlpatterns = [
    path("health/live", views.liveness, name="health-live"),
    path("health/ready", views.readiness, name="health-ready"),
]

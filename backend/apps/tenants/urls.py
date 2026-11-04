from django.urls import path

from . import views

urlpatterns = [path("tenant", views.CurrentTenantView.as_view(), name="tenant-current")]

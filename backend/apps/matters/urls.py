from django.urls import path

from . import views

urlpatterns = [
    path("matters", views.MatterListCreateView.as_view(), name="matter-list"),
    path("matters/<uuid:pk>", views.MatterDetailView.as_view(), name="matter-detail"),
]

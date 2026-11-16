from django.urls import path

from . import views

urlpatterns = [
    path("services/", views.ServiceListView.as_view(), name="service-list"),
    path("providers/", views.ProviderListView.as_view(), name="provider-list"),
    path("slots/", views.FreeSlotsView.as_view(), name="free-slots"),
]
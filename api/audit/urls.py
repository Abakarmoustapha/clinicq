from django.urls import path

from . import views

urlpatterns = [
    path("activity/", views.ActivityListView.as_view(), name="staff-activity"),
]
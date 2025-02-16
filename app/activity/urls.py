"""
URL Mapping for Activity Sync.
"""
from django.urls import path
from activity import views

app_name = "activity"


urlpatterns = [
    path("sync", views.ActivitySynciew.as_view(), name="sync_activity"),
]

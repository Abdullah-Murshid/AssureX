"""Root URL configuration: everything lives under /api/."""

from django.urls import path

from restapi.api import api

urlpatterns = [
    path("api/", api.urls),
]

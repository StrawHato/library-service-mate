import debug_toolbar
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/users/", include("user.urls", namespace="users")),
    path("__debug__", include(debug_toolbar.urls)),
]

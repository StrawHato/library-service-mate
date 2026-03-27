import debug_toolbar
from django.contrib import admin
from django.urls import path, include

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/users/", include("user.urls", namespace="users")),
    path("api/books/", include("books.urls", namespace="books")),
    path("api/borrowings/", include("borrowings.urls", namespace="borrowings")),
    path("api/payments/", include("payments.urls", namespace="payments")),
    path("api/schema/",SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui"
    ),
    path("__debug__", include(debug_toolbar.urls)),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from payments.views import (
    PaymentsViewSet,
    SuccessView,
)

router = DefaultRouter()
router.register("", PaymentsViewSet, basename="payments")

urlpatterns = [
    path("success/", SuccessView.as_view(), name="success"),
    path("", include(router.urls)),
]

app_name = "payments"

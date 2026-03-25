from django.urls import path

from user.views import CreateUserAPIView


urlpatterns = [
    path("", CreateUserAPIView.as_view(), name="create"),
]

app_name = "user"

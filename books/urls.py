from django.urls import path, include
from rest_framework import routers

from books.views import BooksViewSet

router = routers.DefaultRouter()

router.register("", BooksViewSet)

urlpatterns = [
    path("", include(router.urls)),
]

app_name = "books"

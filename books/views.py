from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination

from books.models import Book
from books.permissions import IsAdminOrReadOnly
from books.serializers import BookSerializer


class BookPagination(PageNumberPagination):
    page_size = 5
    max_page_size = 10
    page_size_query_param = "page_size"


class BooksViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = BookPagination

from rest_framework import viewsets, mixins
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from borrowings.models import Borrowing
from borrowings.serializers import (
    BorrowingReadSerializer,
    BorrowingCreateSerializer
)


class BorrowingPagination(PageNumberPagination):
    page_size = 5
    max_page_size = 10
    page_size_query_param = "page_size"

class BorrowingsViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = Borrowing.objects.all()
    serializer_class = BorrowingReadSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = BorrowingPagination

    def get_queryset(self):
        user = self.request.user
        if not user.is_staff:
            return self.queryset.filter(user=user)

        return self.queryset

    def get_serializer_class(self):
        if self.action == "create":
            return BorrowingCreateSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

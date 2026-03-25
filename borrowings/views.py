from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

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

    @action(detail=True, methods=["POST"])
    def return_borrowing(self, request, pk=None):
        borrowing = self.get_object()
        if borrowing.is_active:
            with transaction.atomic():
                book = borrowing.book

                book.inventory += 1
                book.save()

                borrowing.actual_return_date = timezone.now().date()
                borrowing.save()

                return Response(
                    {"Success": "Borrowed book was returned"},
                    status=status.HTTP_200_OK
                )
        return Response(
            {"Error": "You can't return a borrowed book twice"},
        )

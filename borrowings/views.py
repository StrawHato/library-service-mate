from django.db import transaction
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
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
from payments.services import create_fine_checkout_session


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
    queryset = (
        Borrowing.objects
        .select_related("book", "user")
        .prefetch_related("payments")
    )
    serializer_class = BorrowingReadSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = BorrowingPagination

    def get_queryset(self):
        queryset = self.queryset
        user = self.request.user

        if not user.is_staff:
            queryset = queryset.filter(user=user)

        is_active = self.request.query_params.get("is_active")
        user_id = self.request.query_params.get("user_id")

        if user_id and user.is_staff:
            queryset = self.queryset.filter(user__id=user_id)

        if is_active:
            if is_active.lower() == "true":
                queryset = queryset.filter(actual_return_date__isnull=True)
            elif is_active.lower() == "false":
                queryset = queryset.filter(actual_return_date__isnull=False)

        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return BorrowingCreateSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        description="Return a borrowed book. Marks borrowing as returned and creates a fine if overdue.",
        responses={200: BorrowingReadSerializer}
    )
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

                if borrowing.actual_return_date > borrowing.expected_return_date:
                    checkout_url = create_fine_checkout_session(borrowing, request)
                    return Response(
                        {
                            "Success": "Borrowed book was returned, "
                                       "but You returned the book late. "
                                       "You must pay a fine.",
                            "checkout_url": checkout_url,
                        },
                        status=status.HTTP_200_OK,
                    )

                return Response(
                    {"Success": "Borrowed book was returned"},
                    status=status.HTTP_200_OK
                )
        return Response(
            {"Error": "You can't return a borrowed book twice"},
            status=status.HTTP_400_BAD_REQUEST
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="is_active",
                type=OpenApiTypes.STR,
                description="Filter only by two strings: true or false(ex. ?is_active=true)",
            ),
            OpenApiParameter(
                name="user_id",
                type=OpenApiTypes.NUMBER,
                description="Filter by user ID. Works only for admin users(ex. ?user_id=1)",
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        """
        Returns filtered list of borrowings.
        """
        return super(BorrowingsViewSet, self).list(request, *args, **kwargs)

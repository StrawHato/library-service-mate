import stripe
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.models import Payment
from payments.serializers import PaymentSerializer


class PaymentsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.select_related("borrowing")
    serializer_class = PaymentSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = self.queryset
        user = self.request.user
        user_id = self.request.query_params.get("user_id")

        if not user.is_staff:
            queryset = queryset.filter(borrowing__user__id=user.id)

        if user_id:
            queryset = queryset.filter(borrowing__user__id=user_id)

        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=OpenApiTypes.NUMBER,
                description="Filter by user ID. Works only for admin users(ex. ?user_id=1)",
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        """
        Returns list of user payments for non-admin users.
        Returns filtered list of all users payments for admins.
        """
        return super(PaymentsViewSet, self).list(request, *args, **kwargs)


class SuccessView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        """Handle successful payment"""

        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response(
                {"detail": "Session id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            payment = Payment.objects.select_related("borrowing__book", "borrowing__user").get(
                session_id=session_id
            )
        except Payment.DoesNotExist:
            return Response(
                {"detail": "Payment not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        borrowing = payment.borrowing

        if request.user != borrowing.user:
            return Response(
                {"detail": "You do not have permission to access this payment"},
                status=status.HTTP_403_FORBIDDEN
            )

        if payment.status == Payment.StatusChoices.PAID:
            return Response(
                {"detail": "You have already paid for this borrowing"},
                status=status.HTTP_200_OK
            )

        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status != "paid":
            return Response(
                {"detail": "Payment has not been completed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment.status = Payment.StatusChoices.PAID
        payment.save(update_fields=["status"])

        return Response(
            {
                "success": f"You have successfully paid for "
                           f"{borrowing.book.title} "
                           f"for {payment.money_to_pay}"
            },
            status=status.HTTP_200_OK
        )


class CancelView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        """Handle cancellation"""
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response(
                {"detail": "Session id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            payment = Payment.objects.select_related("borrowing__book", "borrowing__user").get(
                session_id=session_id
            )
        except Payment.DoesNotExist:
            return Response(
                {"detail": "Payment not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        checkout_url = payment.session_url

        return Response(
            {
                "detail": "Payment was canceled. You can complete it within 24 hours.",
                "checkout_url": checkout_url
            },
            status=status.HTTP_200_OK
        )

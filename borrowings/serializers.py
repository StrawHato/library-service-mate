from django.db import transaction
from rest_framework import serializers

from books.models import Book
from books.serializers import BookSerializer
from borrowings.models import Borrowing
from payments.models import Payment
from payments.serializers import PaymentSerializer
from payments.services import create_checkout_session


class BorrowingReadSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True, many=False)
    payments = PaymentSerializer(read_only=True, many=True)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
            "payments",
            "user",
            "is_active"
        )


class BorrowingCreateSerializer(serializers.ModelSerializer):
    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())
    checkout_url = serializers.SerializerMethodField()

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "expected_return_date",
            "book",
            "checkout_url"
        )

    def create(self, validated_data):
        with transaction.atomic():
            book = validated_data.pop("book")

            if book.inventory == 0:
                raise serializers.ValidationError("Book is not available")

            book.inventory -= 1
            book.save()

            borrowing = Borrowing.objects.create(book=book, **validated_data)
            request = self.context.get("request")
            create_checkout_session(borrowing, request)

        return borrowing

    @staticmethod
    def get_checkout_url(obj):
        payment = obj.payments.filter(status=Payment.StatusChoices.PENDING).first()

        return payment.session_url

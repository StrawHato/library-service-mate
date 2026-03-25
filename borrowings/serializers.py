from rest_framework import serializers

from books.models import Book
from books.serializers import BookSerializer
from borrowings.models import Borrowing


class BorrowingReadSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True, many=False)
    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
            "user",
            "is_active"
        )


class BorrowingCreateSerializer(serializers.ModelSerializer):
    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())
    class Meta:
        model = Borrowing
        fields = (
            "id",
            "expected_return_date",
            "book"
        )

    def create(self, validated_data):
        book = validated_data.pop("book")

        if book.inventory == 0:
            raise serializers.ValidationError("Book is not available")

        book.inventory -= 1
        book.save()

        return Borrowing.objects.create(book=book, **validated_data)

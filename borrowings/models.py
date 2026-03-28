from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q, F

from books.models import Book


class Borrowing(models.Model):
    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="borrowings")
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="borrowings"
    )

    @property
    def is_active(self):
        return self.actual_return_date is None

    class Meta:
        ordering = ["-borrow_date"]
        constraints = [
            models.CheckConstraint(
                condition=Q(expected_return_date__gt=F("borrow_date")),
                name="expected_return_date_greater_than_borrow_date",
            ),
            models.CheckConstraint(
                condition=Q(actual_return_date__isnull=True) |
                      Q(actual_return_date__gte=F("borrow_date")),
                name="actual_return_date_valid",
            ),
        ]

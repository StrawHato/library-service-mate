from decimal import Decimal

from django.db import models

from borrowings.models import Borrowing


def calculate_money(borrowing) -> Decimal:
    days = (borrowing.expected_return_date - borrowing.borrow_date).days
    return Decimal(days) * borrowing.book.daily_fee


class Payment(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "Pending"
        PAID = "Paid"

    class TypeChoices(models.TextChoices):
        PAYMENT = "Payment"
        FINE = "Fine"

    status = models.CharField(max_length=8, choices=StatusChoices.choices)
    type = models.CharField(max_length=8, choices=TypeChoices.choices)
    borrowing = models.ForeignKey(
        Borrowing,
        on_delete=models.PROTECT,
        related_name="payments"
    )
    session_url = models.URLField()
    session_id = models.CharField(max_length=36, null=True, blank=True)
    money_to_pay = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session_url", "session_id"],
                name="session_url_session_id_unique"
            )
        ]

    def __str__(self):
        return f"{self.type} - {self.status}"

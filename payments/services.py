from decimal import Decimal

import stripe
from django.conf import settings
from django.urls import reverse

from payments.models import calculate_money, Payment

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_checkout_session(borrowing, request):
    amount = calculate_money(borrowing)
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Book borrowing",
                    },
                    "unit_amount": int(amount * 100)
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=request.build_absolute_uri(reverse("payments:success"))+"?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=request.build_absolute_uri(reverse("payments:cancel"))+"?session_id={CHECKOUT_SESSION_ID}",
        customer_email=borrowing.user.email,
        metadata={
            "user_id": borrowing.user.id,
            "borrowing_id": borrowing.id,
        }
    )
    Payment.objects.create(
        borrowing=borrowing,
        session_url=session.url,
        session_id=session.id,
        money_to_pay=amount,
    )
    return session.url


def calculate_fine_amount(borrowing):
    if not hasattr(borrowing, "expected_return_date"):
        raise ValueError("Invalid borrowing object passed")

    if not borrowing.actual_return_date:
        return Decimal("0.00")

    days = (borrowing.actual_return_date - borrowing.expected_return_date).days

    if days <= 0:
        return Decimal("0.00")

    fine_multiplier = 2
    return Decimal(fine_multiplier) * Decimal(days) * borrowing.book.daily_fee


def create_fine_checkout_session(borrowing, request):
    amount = calculate_fine_amount(borrowing)
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Book borrowing",
                    },
                    "unit_amount": int(amount * 100)
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=request.build_absolute_uri(reverse("payments:success"))+"?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=request.build_absolute_uri(reverse("payments:cancel"))+"?session_id={CHECKOUT_SESSION_ID}",
        customer_email=borrowing.user.email,
        metadata={
            "user_id": borrowing.user.id,
            "borrowing_id": borrowing.id,
        }
    )
    Payment.objects.create(
        type=Payment.TypeChoices.FINE,
        borrowing=borrowing,
        session_url=session.url,
        session_id=session.id,
        money_to_pay=amount,
    )
    return session.url

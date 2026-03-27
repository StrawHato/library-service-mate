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

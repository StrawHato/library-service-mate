from unittest.mock import patch
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework import status

from datetime import date, timedelta

from books.models import Book
from borrowings.models import Borrowing
from payments.models import Payment
from payments.services import (
    create_fine_checkout_session,
    create_checkout_session,
)


PAYMENTS_URL = reverse("payments:payments-list")


def get_results(response):
    return response.data["results"] if "results" in response.data else response.data


def create_user(**params):
    return get_user_model().objects.create_user(**params)


def create_book(**params):
    defaults = {
        "title": "Test Book",
        "author": "Author",
        "cover": Book.CoverChoices.SOFT,
        "inventory": 5,
        "daily_fee": Decimal("1.00"),
    }
    defaults.update(params)
    return Book.objects.create(**defaults)


def create_borrowing(user, book, overdue=True, returned=True):
    borrowing = Borrowing.objects.create(
        user=user,
        book=book,
        expected_return_date=date.today() + timedelta(days=2),
    )

    if overdue:
        borrowing.borrow_date = date.today() - timedelta(days=5)
        borrowing.expected_return_date = date.today() - timedelta(days=2)

        if returned:
            borrowing.actual_return_date = date.today()

        borrowing.save(update_fields=[
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
        ])

    return borrowing


def get_request(user):
    factory = APIRequestFactory()
    request = factory.get("/")
    request.user = user
    return request


def handle_successful_payment(payment):
    payment.status = "paid"
    payment.save(update_fields=["status"])
    return payment


# =========================
# API TESTS
# =========================

class PaymentApiTests(APITestCase):
    def setUp(self):
        self.user = create_user(email="user@test.com", password="pass123")
        self.admin = create_user(
            email="admin@test.com",
            password="pass123",
            is_staff=True,
        )
        self.book = create_book()

    def test_auth_required(self):
        res = self.client.get(PAYMENTS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("payments.services.stripe.checkout.Session.create")
    def test_user_sees_only_own_payments(self, mock_stripe):
        mock_stripe.side_effect = [
            type("obj", (), {"id": "sess_1", "url": "http://stripe/1"})(),
            type("obj", (), {"id": "sess_2", "url": "http://stripe/2"})(),
        ]

        self.client.force_authenticate(self.user)

        request = get_request(self.user)

        borrowing = create_borrowing(self.user, self.book, overdue=True, returned=True)
        create_fine_checkout_session(borrowing, request)

        other_user = create_user(email="other@test.com", password="pass123")
        other_request = get_request(other_user)
        other_borrowing = create_borrowing(other_user, self.book, overdue=True, returned=True)
        create_fine_checkout_session(other_borrowing, other_request)

        res = self.client.get(PAYMENTS_URL)

        results = get_results(res)
        self.assertEqual(len(results), 1)

    def test_user_cannot_post(self):
        self.client.force_authenticate(self.user)

        res = self.client.post(PAYMENTS_URL, {})
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @patch("payments.services.stripe.checkout.Session.create")
    def test_user_cannot_delete(self, mock_stripe):
        mock_stripe.return_value = type("obj", (), {
            "id": "sess_123",
            "url": "http://stripe"
        })()

        self.client.force_authenticate(self.user)

        request = get_request(self.user)
        borrowing = create_borrowing(self.user, self.book, overdue=True, returned=True)

        create_fine_checkout_session(borrowing, request)

        payment = Payment.objects.first()

        url = reverse("payments:payments-detail", args=[payment.id])
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @patch("payments.services.stripe.checkout.Session.create")
    def test_admin_sees_all_payments(self, mock_stripe):
        mock_stripe.return_value = type("obj", (), {
            "id": "sess_123",
            "url": "http://stripe"
        })()

        self.client.force_authenticate(self.admin)

        request = get_request(self.user)
        borrowing = create_borrowing(self.user, self.book, overdue=True, returned=True)

        create_fine_checkout_session(borrowing, request)

        res = self.client.get(PAYMENTS_URL)

        results = get_results(res)
        self.assertEqual(len(results), 1)

    @patch("payments.services.stripe.checkout.Session.create")
    def test_admin_can_filter_by_user_id(self, mock_stripe):
        mock_stripe.return_value = type("obj", (), {
            "id": "sess_123",
            "url": "http://stripe"
        })()

        self.client.force_authenticate(self.admin)

        request = get_request(self.user)
        borrowing = create_borrowing(self.user, self.book, overdue=True, returned=True)

        create_fine_checkout_session(borrowing, request)

        res = self.client.get(PAYMENTS_URL, {"user_id": self.user.id})

        results = get_results(res)
        self.assertEqual(len(results), 1)


# =========================
# SERVICE TESTS
# =========================

class PaymentServiceTests(TestCase):
    def setUp(self):
        self.user = create_user(email="user@test.com", password="pass123")
        self.book = create_book()
        self.borrowing = create_borrowing(self.user, self.book, overdue=True, returned=True)
        self.request = get_request(self.user)

    def test_create_fine_checkout_session_sets_correct_fields(self):
        create_fine_checkout_session(self.borrowing, self.request)

        payment = Payment.objects.first()

        self.assertEqual(payment.borrowing, self.borrowing)
        self.assertGreater(payment.money_to_pay, 0)

    def test_no_fine_if_not_returned(self):
        borrowing = create_borrowing(self.user, self.book, overdue=True, returned=False)

        create_fine_checkout_session(borrowing, self.request)

        payment = Payment.objects.first()
        self.assertTrue(payment is None or payment.money_to_pay == 0)

    def test_no_fine_if_returned_on_time(self):
        borrowing = create_borrowing(self.user, self.book, overdue=False, returned=True)

        create_fine_checkout_session(borrowing, self.request)

        payment = Payment.objects.first()
        self.assertTrue(payment is None or payment.money_to_pay == 0)

    @patch("payments.services.stripe.checkout.Session.create")
    def test_checkout_session_created(self, mock_stripe):
        mock_stripe.return_value = type("obj", (), {
            "id": "sess_123",
            "url": "http://stripe"
        })()

        url = create_checkout_session(self.borrowing, self.request)

        self.assertEqual(url, "http://stripe")
        mock_stripe.assert_called_once()

    def test_payment_status_flow_pending_to_paid(self):
        create_fine_checkout_session(self.borrowing, self.request)

        payment = Payment.objects.first()

        self.assertEqual(payment.status, "Pending")

        handle_successful_payment(payment)

        payment.refresh_from_db()
        self.assertEqual(payment.status, "paid")

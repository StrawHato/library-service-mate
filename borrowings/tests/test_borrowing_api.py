from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from books.models import Book
from borrowings.models import Borrowing


BORROWINGS_URL = reverse("borrowings:borrowing-list")


def detail_url(borrowing_id):
    return reverse("borrowings:borrowing-detail", args=[borrowing_id])


def return_url(borrowing_id):
    return reverse("borrowings:borrowing-return-borrowing", args=[borrowing_id])


def create_user(**params):
    return get_user_model().objects.create_user(**params)


def create_book(**params):
    defaults = {
        "title": "Test Book",
        "author": "Author",
        "cover": Book.CoverChoices.HARD,
        "inventory": 5,
        "daily_fee": 1.00,
    }
    defaults.update(params)
    return Book.objects.create(**defaults)


def create_borrowing(user, book, **params):
    defaults = {
        "borrow_date": date.today(),
        "expected_return_date": date.today() + timedelta(days=5),
    }
    defaults.update(params)
    return Borrowing.objects.create(user=user, book=book, **defaults)


class PublicBorrowingApiTests(APITestCase):
    def test_auth_required(self):
        res = self.client.get(BORROWINGS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateBorrowingApiTests(APITestCase):
    def setUp(self):
        self.user = create_user(email="user@test.com", password="testpass123")
        self.client.force_authenticate(self.user)

        self.book = create_book(inventory=5)

    def test_user_can_see_only_own_borrowings(self):
        other_user = create_user(email="other@test.com", password="pass123")

        create_borrowing(user=self.user, book=self.book)
        create_borrowing(user=other_user, book=self.book)

        res = self.client.get(BORROWINGS_URL)

        self.assertEqual(len(res.data["results"]), 1)

    def test_create_borrowing_decreases_inventory(self):
        payload = {
            "book": self.book.id,
            "expected_return_date": date.today() + timedelta(days=5),
        }

        res = self.client.post(BORROWINGS_URL, payload)

        self.book.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.book.inventory, 4)

    def test_cannot_borrow_if_no_inventory(self):
        self.book.inventory = 0
        self.book.save()

        payload = {
            "book": self.book.id,
            "expected_return_date": date.today() + timedelta(days=5),
        }

        res = self.client.post(BORROWINGS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expected_return_date_cannot_be_in_past(self):
        payload = {
            "book": self.book.id,
            "expected_return_date": date.today() - timedelta(days=1),
        }

        res = self.client.post(BORROWINGS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_is_active(self):
        create_borrowing(user=self.user, book=self.book)
        create_borrowing(
            user=self.user,
            book=self.book,
            actual_return_date=date.today() + timedelta(days=1),
        )

        res = self.client.get(BORROWINGS_URL, {"is_active": True})

        self.assertEqual(len(res.data["results"]), 1)

    def test_user_cannot_return_others_borrowing(self):
        other_user = create_user(email="other@test.com", password="pass123")
        borrowing = create_borrowing(user=other_user, book=self.book)

        res = self.client.post(return_url(borrowing.id))

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class AdminBorrowingApiTests(APITestCase):
    def setUp(self):
        self.admin = create_user(
            email="admin@test.com",
            password="adminpass123",
            is_staff=True,
        )
        self.client.force_authenticate(self.admin)

        self.user = create_user(email="user@test.com", password="testpass123")
        self.book = create_book()

    def test_admin_can_see_all_borrowings(self):
        create_borrowing(user=self.user, book=self.book)
        create_borrowing(user=self.admin, book=self.book)

        res = self.client.get(BORROWINGS_URL)

        self.assertEqual(len(res.data["results"]), 2)

    def test_admin_filter_by_user_id(self):
        create_borrowing(user=self.user, book=self.book)

        res = self.client.get(BORROWINGS_URL, {"user_id": self.user.id})

        self.assertEqual(len(res.data["results"]), 1)


class BorrowingReturnTests(APITestCase):
    def setUp(self):
        self.user = create_user(email="user@test.com", password="testpass123")
        self.client.force_authenticate(self.user)

        self.book = create_book(inventory=3)
        self.borrowing = create_borrowing(user=self.user, book=self.book)

    def test_return_book_success(self):
        res = self.client.post(return_url(self.borrowing.id))

        self.borrowing.refresh_from_db()
        self.book.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(self.borrowing.actual_return_date)
        self.assertEqual(self.book.inventory, 4)

    def test_cannot_return_twice(self):
        self.borrowing.actual_return_date = date.today() + timedelta(days=2)
        self.borrowing.save()

        res = self.client.post(return_url(self.borrowing.id))

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_return_on_time(self):
        self.borrowing.expected_return_date = date.today() + timedelta(days=2)
        self.borrowing.save()
        res = self.client.post(return_url(self.borrowing.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)

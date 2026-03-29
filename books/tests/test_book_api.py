from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from books.models import Book


BOOKS_URL = reverse("books:book-list")


def detail_url(book_id):
    return reverse("books:book-detail", args=[book_id])


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


class PublicBookApiTests(APITestCase):
    """Unauthenticated users"""

    def test_auth_required(self):
        res = self.client.get(BOOKS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)


class PrivateBookApiTests(APITestCase):
    """Authenticated users (non-admin)"""

    def setUp(self):
        self.user = create_user(
            email="user@test.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

    def test_list_books(self):
        create_book()
        create_book(title="Another Book")

        res = self.client.get(BOOKS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)

    def test_retrieve_book(self):
        book = create_book()

        res = self.client.get(detail_url(book.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], book.id)

    def test_non_admin_cannot_create_book(self):
        payload = {
            "title": "New Book",
            "author": "Author",
            "inventory": 5,
            "daily_fee": 2.00,
        }

        res = self.client.post(BOOKS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_admin_cannot_update_book(self):
        book = create_book()

        res = self.client.patch(detail_url(book.id), {"title": "Updated"})

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_admin_cannot_delete_book(self):
        book = create_book()

        res = self.client.delete(detail_url(book.id))

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminBookApiTests(APITestCase):
    """Admin users"""

    def setUp(self):
        self.admin = create_user(
            email="admin@test.com",
            password="adminpass123",
            is_staff=True,
        )
        self.client.force_authenticate(self.admin)

    def test_admin_can_create_book(self):
        payload = {
            "title": "Admin Book",
            "author": "Admin Author",
            "cover": Book.CoverChoices.HARD,
            "inventory": 10,
            "daily_fee": 0.40,
        }

        res = self.client.post(BOOKS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Book.objects.count(), 1)

    def test_admin_can_update_book(self):
        book = create_book()

        res = self.client.patch(detail_url(book.id), {"title": "Updated"})

        book.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(book.title, "Updated")

    def test_admin_can_delete_book(self):
        book = create_book()

        res = self.client.delete(detail_url(book.id))

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Book.objects.count(), 0)

    def test_inventory_cannot_be_negative(self):
        payload = {
            "title": "Bad Book",
            "author": "Author",
            "inventory": -1,
            "daily_fee": 1.00,
        }

        res = self.client.post(BOOKS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_fields(self):
        payload = {
            "title": "Incomplete Book"
        }

        res = self.client.post(BOOKS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

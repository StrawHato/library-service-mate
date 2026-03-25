from rest_framework import viewsets

from borrowings.models import Borrowing
from borrowings.serializers import BorrowingReadSerializer


class BorrowingsViewSet(
    viewsets.ReadOnlyModelViewSet
):
    queryset = Borrowing.objects.all()
    serializer_class = BorrowingReadSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            return self.queryset.filter(expected_return_date__isnull=True)

        return self.queryset.filter(user=self.request.user)

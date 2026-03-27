from rest_framework import serializers

from payments.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True, source="borrowing.user.id")

    class Meta:
        model = Payment
        fields = (
            "id", "status", "type", "borrowing",
            "session_url", "session_id", "money_to_pay", "user_id"
        )

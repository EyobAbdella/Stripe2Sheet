from django.db import models
from django.conf import settings
import random
import string


def generate_random_string():
    return "".join(random.choices(string.ascii_letters + string.digits, k=50))


class Event(models.Model):
    id = models.CharField(
        max_length=50, unique=True, default=generate_random_string, primary_key=True
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    triggerEvent = models.CharField(
        max_length=30,
        choices=[
            ("customer.created", "NEW_CUSTOMER"),
            ("charge.succeeded", "PAYMENT_SUCCESS"),
            ("payment_intent.created", "PAYMENT_CREATED"),
        ],
    )
    sheet_id = models.CharField(max_length=255, blank=True, null=True)

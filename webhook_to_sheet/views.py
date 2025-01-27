from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.mixins import CreateModelMixin
from rest_framework.viewsets import GenericViewSet
from googleapiclient.discovery import build
from webhook_to_sheet.utils import google_credentials
from .serializers import EventSerializer
from .models import Event
import json


class CreateEvent(CreateModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = EventSerializer

    def get_queryset(self):
        user_id = self.request.user.id
        return Event.objects.filter(user_id=user_id)

    def get_serializer_context(self):
        return {"request": self.request}

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = serializer.save()
        webhook_url = request.build_absolute_uri(f"/send-webhook/{event.id}")
        return Response({"webhook_URL": webhook_url}, status=status.HTTP_201_CREATED)


def write_sheet(user, sheet_id, values, range_name):
    credentials = get_credentials(user)
    if not credentials:
        return None

    service = build("sheets", "v4", credentials=credentials)
    sheet = service.spreadsheets()

    body = {"values": values}

    result = (
        sheet.values()
        .append(
            spreadsheetId=sheet_id,
            range="Sheet1",
            valueInputOption="RAW",
            body=body,
            insertDataOption="INSERT_ROWS",
        )
        .execute()
    )

    return result


@csrf_exempt
def stripe_webhook(request, id):
    try:
        payload = json.loads(request.body)
        event_type = payload.get("type")
        queryset = Event.objects.get(id=id)
        sheet_id = queryset.sheet_id
        email = None
        name = None
        status = None
        amount = None
        currency = None
        if event_type in [queryset.triggerEvent, "charge.succeeded"]:

            if payload.get("data") and payload["data"].get("object"):
                billing_details = payload["data"]["object"].get("billing_details")

                if billing_details:
                    email = billing_details.get("email")
                    name = billing_details.get("name")

                status = payload["data"]["object"].get("status")
                amount = payload["data"]["object"].get("amount")
                currency = payload["data"]["object"].get("currency")

            values = [email, name, amount, currency, status]

            tokens = {
                "google_sheet_access_token": queryset.user.google_access_token,
                "google_sheet_refresh_token": queryset.user.google_refresh_token,
            }

            if status == "succeeded":
                credentials = google_credentials(tokens)
                if not credentials:
                    return None

                service = build("sheets", "v4", credentials=credentials)
                sheet = service.spreadsheets()

                body = {"values": [values]}

                result = (
                    sheet.values()
                    .append(
                        spreadsheetId=sheet_id,
                        range="Sheet1",
                        valueInputOption="RAW",
                        body=body,
                        insertDataOption="INSERT_ROWS",
                    )
                    .execute()
                )

        return HttpResponse(status=200)
    except json.JSONDecodeError as e:
        return HttpResponse(status=400)

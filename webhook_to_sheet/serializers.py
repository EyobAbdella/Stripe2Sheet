from rest_framework import serializers
from googleapiclient.discovery import build
from webhook_to_sheet.utils import google_credentials
from .models import Event
from account.models import User


def list_all_spreadsheets(tokens):
    credentials = google_credentials(tokens)
    if not credentials:
        return None

    service = build("drive", "v3", credentials=credentials)

    query = "mimeType='application/vnd.google-apps.spreadsheet'"
    results = service.files().list(q=query, fields="files(id, name)").execute()

    spreadsheets = results.get("files", [])
    return spreadsheets


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = "__all__"
        read_only_fields = ["id", "user"]

    def __init__(self, *args, **kwargs):
        request = kwargs["context"].get("request")
        super().__init__(*args, **kwargs)

        user = User.objects.get(id=request.user.id)
        tokens = {
            "google_sheet_access_token": user.google_access_token,
            "google_sheet_refresh_token": user.google_refresh_token,
        }
        spreadsheets = list_all_spreadsheets(tokens)
        if spreadsheets:
            self.sheet_choices = {sheet["name"]: sheet["id"] for sheet in spreadsheets}
            self.fields["sheet_id"] = serializers.ChoiceField(
                choices=[(name, name) for name in self.sheet_choices.keys()]
            )

    def create(self, validated_data):
        sheet_name = validated_data.get("sheet_id")
        sheet_id = self.sheet_choices.get(sheet_name)
        validated_data["sheet_id"] = sheet_id

        request = self.context.get("request")
        user = request.user

        event = Event.objects.create(user=user, **validated_data)
        return event

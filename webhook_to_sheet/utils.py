from django.conf import settings
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


def google_credentials(tokens):

    credentials = Credentials(
        token=tokens.get("google_sheet_access_token"),
        refresh_token=tokens.get("google_sheet_refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    return credentials

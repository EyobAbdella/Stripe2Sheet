from django.conf import settings
from django.contrib.auth import login
from django.core.cache import cache
from django.shortcuts import redirect
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from urllib.parse import urlencode
from oauthlib.common import UNICODE_ASCII_CHARACTER_SET
from random import SystemRandom
from .models import User
import requests
import jwt


@api_view(["GET"])
def handle_google_redirect(request):
    SCOPES = [
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "openid",
    ]

    rand = SystemRandom()
    state = "".join(rand.choice(UNICODE_ASCII_CHARACTER_SET) for _ in range(30))

    cache.set(state, True, timeout=300)

    redirect_uri = "http://127.0.0.1:8000/oauth/callback"

    params = {
        "response_type": "code",
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": " ".join(SCOPES),
        "state": state,
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
    }

    query_params = urlencode(params)
    authorization_url = f"https://accounts.google.com/o/oauth2/auth?{query_params}"

    return redirect(authorization_url)


@api_view(["GET"])
def handle_google_callback(request):
    code = request.GET.get("code")
    state = request.GET.get("state")
    error = request.GET.get("error")

    print(code)

    if error:
        return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

    if not code or not state:
        return Response(
            {"error": "code and state are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not cache.get(state):
        return Response(
            {"error": "Invalid or expired state."}, status=status.HTTP_400_BAD_REQUEST
        )

    cache.delete(state)

    redirect_uri = "http://127.0.0.1:8000/oauth/callback"
    token_endpoint = "https://oauth2.googleapis.com/token"

    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    response = requests.post(token_endpoint, data=data)
    if not response.ok:
        return Response(
            {"error": "Failed to exchange authorization code for tokens."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    tokens = response.json()

    id_token = tokens.get("id_token")

    if not id_token:
        return Response(
            {"error": "ID token is missing in the response."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    decoded_id_token = jwt.decode(id_token, options={"verify_signature": False})
    email = decoded_id_token.get("email")
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    user = User.objects.filter(email=email).first()

    if user is None:
        user = User.objects.create(
            email=email,
            google_access_token=access_token,
            google_refresh_token=refresh_token,
        )

    login(request, user)

    refresh = RefreshToken.for_user(user)
    token = TokenObtainPairSerializer().get_token(user)

    return Response(
        {
            "access_token": str(token.access_token),
            "refresh_token": str(refresh),
        }
    )

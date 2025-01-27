from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import CreateEvent, stripe_webhook

router = DefaultRouter()
router.register(r"create/event", CreateEvent, basename="Create Event")

urlpatterns = [
    path("send-webhook/<str:id>", stripe_webhook),
] + router.urls

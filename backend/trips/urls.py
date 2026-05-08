from django.urls import path
from .views import StartTripView, ActiveTripView

urlpatterns = [
    path('start/', StartTripView.as_view(), name='start-trip'),
    path('active/', ActiveTripView.as_view(), name='active-trip'),
]
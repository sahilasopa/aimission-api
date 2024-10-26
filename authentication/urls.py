from django.urls import path
from .views import SendOtpAPIView, VerifyOtpAPIView, StartJourneyAPIView, EndJourneyAPIView, StationProfileAPIView, EstimatedDistanceAPIView, \
    AddTripsAPIView, call_bedrock, TicketScanAPIView

urlpatterns = [
    path('send/otp', SendOtpAPIView.as_view()),
    path('verify/otp', VerifyOtpAPIView.as_view()),
    path('start/journey', StartJourneyAPIView.as_view()),
    path('end/journey', EndJourneyAPIView.as_view()),
    path('stations/list', StationProfileAPIView.as_view()),
    path('estimate/distance', EstimatedDistanceAPIView.as_view()),
    path('trips/all', AddTripsAPIView.as_view()),
    path('bedrock', call_bedrock, name='call_bedrock'),
    path('ticket/analyize', TicketScanAPIView.as_view()),
]

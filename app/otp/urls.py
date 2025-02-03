"""
URL Mapping for OTP API.
"""
from django.urls import path
from otp import views

app_name = "otp"

urlpatterns = [
    path("request-otp", views.OTPRequestView.as_view(), name="request_otp"),
    path("validate-otp", views.OTPValidateView.as_view(), name="validate_otp"),
]

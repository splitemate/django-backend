from django.apps import AppConfig


class OTPConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'otp'
    verbose_name = 'One-Time Password'
import string
import secrets
from otp.exceptions import OTPCreationLimitExceeded
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from otp.tasks import send_otp_email


class OTPRequestReason(models.TextChoices):
    EMAIL_VERIFICATION = 'EV', 'Email Verification'
    PASSWORD_RESET = 'PR', 'Password Reset'


class OTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='User')
    code = models.CharField(max_length=4, verbose_name='OTP Code')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    expires_at = models.DateTimeField(verbose_name='Expires At')
    reason = models.CharField(max_length=2, choices=OTPRequestReason.choices, verbose_name='Reason')
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def is_valid(self):
        """Check if the OTP is valid and not expired."""
        return not self.is_expired()

    @staticmethod
    def generate_otp():
        digits = string.digits
        otp = ''.join(secrets.choice(digits) for _ in range(4))
        return otp

    @staticmethod
    def get_otp_lifespan():
        return getattr(settings, 'OTP_LIFESPAN', 10)

    @staticmethod
    def get_hourly_limit():
        return getattr(settings, 'OTP_HOURLY_LIMIT', 10)

    @staticmethod
    def clean_old_otps(user):
        one_hour_ago = timezone.now() - timedelta(hours=1)
        OTP.objects.filter(user=user, expires_at__lt=timezone.now(), created_at__lt=one_hour_ago).delete()

    @staticmethod
    def can_request_otp(user):
        last_hour = timezone.now() - timedelta(hours=1)
        otp_count = OTP.objects.filter(user=user, created_at__gte=last_hour).count()
        return otp_count < OTP.get_hourly_limit()

    @staticmethod
    def queue_send_otp_email(user, otp):
        subject = 'Verification Code for Splitemate'
        context = {
            'user': user,
            'otp_code': otp.code,
            'otp_expiry': OTP.get_otp_lifespan()
        }
        html_message = render_to_string('emails/otp_email.html', context)
        plain_message = strip_tags(html_message)
        recipient_list = [user.email]
        send_otp_email.delay(subject, plain_message, html_message, recipient_list)

    @staticmethod
    def create_or_resend_otp(user, reason):
        OTP.clean_old_otps(user)
        if not OTP.can_request_otp(user):
            raise OTPCreationLimitExceeded

        latest_otp = OTP.objects.filter(user=user, reason=reason, is_used=False).order_by('-created_at').first()
        if latest_otp and not latest_otp.is_expired():
            code = latest_otp.code
        else:
            code = OTP.generate_otp()
        expires_at = timezone.now() + timedelta(minutes=OTP.get_otp_lifespan())
        otp = OTP.objects.create(
            user=user,
            reason=reason,
            code=code,
            expires_at=expires_at
        )
        OTP.queue_send_otp_email(user, otp)
        return otp

    def __str__(self):
        return self.code

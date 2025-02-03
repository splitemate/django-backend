from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task(bind=True)
def send_otp_email(self, subject, plain_message, html_message, recipient_list):
    from_email = f"Splitemate <{settings.DEFAULT_FROM_EMAIL}>"
    send_mail(
        subject,
        plain_message,
        from_email,
        recipient_list,
        html_message=html_message
    )

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_payment_confirmation_email(user_email, booking_id):
    send_mail(
        subject="Booking Payment Successful",
        message=f"Your payment for booking {booking_id} was successful.",
        from_email="no-reply@example.com",
        recipient_list=[user_email]
    )

@shared_task
def send_booking_confirmation_email(to_email, booking_id):
    subject = 'Booking Confirmation'
    message = f'Thank you for your booking! Your booking ID is {booking_id}.'
    from_email = settings.DEFAULT_FROM_EMAIL

    send_mail(subject, message, from_email, [to_email])

    return f"Email sent to {to_email}"
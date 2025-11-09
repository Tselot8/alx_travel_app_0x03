import requests
import logging
from django.conf import settings
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Payment, Booking
from django.utils import timezone

from rest_framework import viewsets, status
from .models import Listing, Booking
from .serializers import ListingSerializer, BookingSerializer
from django.http import JsonResponse
from .tasks import send_booking_confirmation_email

def index(request):
    return JsonResponse({'message': 'Listings app is working!'})


class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

@api_view(['POST'])
def initiate_payment(request, booking_id):
    booking = Booking.objects.get(id=booking_id)
    amount = booking.total_price  # Assuming booking has total_amount field

    headers = {
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "amount": str(amount),
        "currency": "ETB",
        "email": booking.user.email,  # Assuming Booking has user with email
        "tx_ref": f"booking_{booking.id}_{timezone.now().timestamp()}",
        "callback_url": request.build_absolute_uri(f"/api/verify-payment/{booking.id}/"),
        "first_name": booking.user.first_name,
        "last_name": booking.user.last_name,
    }

    response = requests.post("https://api.chapa.co/v1/transaction/initialize", json=data, headers=headers)
    res_data = response.json()

    if res_data.get("status") == "success":
        Payment.objects.create(
            booking=booking,
            transaction_id=res_data["data"]["id"],
            amount=amount,
            status="Pending"
        )
        return Response({"payment_url": res_data["data"]["checkout_url"]})
    else:
        return Response({"error": res_data.get("message", "Failed to initiate payment")}, status=400)

logger = logging.getLogger(__name__)

@api_view(['POST'])
def initiate_payment(request, booking_id):
    booking = Booking.objects.get(id=booking_id)
    amount = booking.total_price  # ensure correct field

    headers = {
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    tx_ref = f"booking_{booking.id}_{int(timezone.now().timestamp())}"

    data = {
        "amount": str(amount),
        "currency": "ETB",
        "email": booking.user.email,
        "tx_ref": tx_ref,
        "callback_url": request.build_absolute_uri(f"/api/verify-payment/{booking.id}/"),
        "return_url": request.build_absolute_uri(f"/"),  # optional
        "first_name": booking.user.first_name or "",
        "last_name": booking.user.last_name or "",
    }

    try:
        response = requests.post("https://api.chapa.co/v1/transaction/initialize", json=data, headers=headers, timeout=10)
        res_data = response.json()
    except Exception as e:
        logger.exception("Error calling Chapa initialize API")
        return Response({"error": "Payment provider error"}, status=status.HTTP_502_BAD_GATEWAY)

    logger.info("Chapa init response: %s", res_data)

    if res_data.get("status") == "success" and isinstance(res_data.get("data"), dict):
        data_obj = res_data["data"]
        # Chapa may not return an `id` in all responses (your curl shows only checkout_url).
        # We'll store whichever identifier is available: id, tx_ref, or checkout_url as fallback.
        transaction_id = data_obj.get("id") or data_obj.get("tx_ref") or tx_ref or data_obj.get("checkout_url")

        # store checkout_url separately if available
        checkout_url = data_obj.get("checkout_url") or data_obj.get("hosted_url") or None

        Payment.objects.create(
            booking=booking,
            transaction_id=transaction_id,
            amount=amount,
            status="Pending"
        )

        return Response({"payment_url": checkout_url or data_obj}, status=status.HTTP_201_CREATED)
    else:
        # attach provider message if any
        err_msg = res_data.get("message") or res_data.get("error") or "Failed to initiate payment"
        return Response({"error": err_msg, "provider_response": res_data}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def verify_payment(request, booking_id):
    booking = Booking.objects.get(id=booking_id)
    payment = booking.payments.last()

    if not payment:
        return Response({"error": "No payment record found for this booking"}, status=status.HTTP_404_NOT_FOUND)

    headers = {
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"
    }

    try:
        response = requests.get(f"https://api.chapa.co/v1/transaction/verify/{payment.transaction_id}", headers=headers, timeout=10)
        res_data = response.json()
    except Exception:
        return Response({"error": "Failed to verify payment with provider"}, status=status.HTTP_502_BAD_GATEWAY)

    # log so you can debug provider response
    logger.info("Chapa verify response: %s", res_data)

    if res_data.get("status") == "success" and res_data.get("data", {}).get("status") == "success":
        payment.status = "Completed"
        payment.save()
        # trigger confirmation email
        send_payment_confirmation_email.delay(booking.user.email, booking.id)
        return Response({"message": "Payment completed successfully"})
    else:
        payment.status = "Failed"
        payment.save()
        return Response({"message": "Payment failed", "provider_response": res_data}, status=400)


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    def perform_create(self, serializer):
        booking = serializer.save()
        # Trigger Celery task
        send_booking_confirmation_email.delay(booking.user.email, booking.id)

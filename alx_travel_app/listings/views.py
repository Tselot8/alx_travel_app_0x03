import requests
from django.conf import settings
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Payment, Booking
from django.utils import timezone

from rest_framework import viewsets
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
    amount = booking.total_amount  # Assuming booking has total_amount field

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

@api_view(['GET'])
def verify_payment(request, booking_id):
    booking = Booking.objects.get(id=booking_id)
    payment = booking.payments.last()

    headers = {
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"
    }

    response = requests.get(f"https://api.chapa.co/v1/transaction/verify/{payment.transaction_id}", headers=headers)
    res_data = response.json()

    if res_data.get("status") == "success" and res_data["data"]["status"] == "success":
        payment.status = "Completed"
        payment.save()
        # TODO: Send confirmation email here (Celery)
        return Response({"message": "Payment completed successfully"})
    else:
        payment.status = "Failed"
        payment.save()
        return Response({"message": "Payment failed"}, status=400)

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    def perform_create(self, serializer):
        booking = serializer.save()
        # Trigger Celery task
        send_booking_confirmation_email.delay(booking.user.email, booking.id)

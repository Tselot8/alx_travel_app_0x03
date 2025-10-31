from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ListingViewSet, BookingViewSet
from . import views

router = DefaultRouter()
router.register(r'listings', ListingViewSet)
router.register(r'bookings', BookingViewSet)

urlpatterns = [
    path('', views.index, name='index'),
    path('initiate-payment/<int:booking_id>/', views.initiate_payment, name='initiate-payment'),
    path('verify-payment/<int:booking_id>/', views.verify_payment, name='verify-payment'),
    path('', include(router.urls)),  # ✅ This line includes the ViewSet routes
]
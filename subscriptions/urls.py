from django.urls import path
from . import views

urlpatterns = [
    path('plans/', views.PlanListView.as_view(), name='plan-list'),
    path('my-subscription/', views.CurrentSubscriptionView.as_view(), name='current-subscription'),
    path('vfa-access/', views.VfaAccessView.as_view(), name='vfa-access'),
    path('checkout/create-session/', views.CreateCheckoutSessionView.as_view(), name='create-checkout-session'),
    path('checkout/verify/', views.VerifyCheckoutView.as_view(), name='verify-checkout'),
    path('checkout/webhook/', views.RazorpayWebhookView.as_view(), name='razorpay-webhook'),
]

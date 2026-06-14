from django.urls import path
from . import views

urlpatterns = [
    path('plans/', views.PlanListView.as_view(), name='plan-list'),
    path('my-subscription/', views.CurrentSubscriptionView.as_view(), name='current-subscription'),
    path('checkout/create-session/', views.CreateCheckoutSessionView.as_view(), name='create-checkout-session'),
    path('checkout/webhook/', views.RazorpayWebhookView.as_view(), name='razorpay-webhook'),
]

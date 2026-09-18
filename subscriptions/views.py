import hmac
import hashlib
import json
import logging
import uuid
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Plan, Subscription, PaymentHistory
from .serializers import PlanSerializer, SubscriptionSerializer
from .vfa_access import vfa_access_payload

logger = logging.getLogger(__name__)


def _razorpay_creds():
    return (
        getattr(settings, 'RAZORPAY_KEY_ID', '') or 'rzp_test_mockkey',
        getattr(settings, 'RAZORPAY_KEY_SECRET', '') or 'mocksecret',
        getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '') or 'mockwebhooksecret',
    )


def _razorpay_client():
    key_id, key_secret, _ = _razorpay_creds()
    if not key_id or key_id in ('rzp_test_mockkey', 'your_key_id'):
        return None
    try:
        import razorpay
        return razorpay.Client(auth=(key_id, key_secret))
    except Exception as exc:
        logger.exception('Razorpay client init failed: %s', exc)
        return None


def _activate_subscription(sub):
    plan = sub.plan
    now = timezone.now()
    days = int((plan.features or {}).get('duration_days') or (30 if plan.interval == 'month' else 365))
    start = sub.end_date if sub.end_date and sub.end_date > now else now
    if sub.status not in ('active', 'trialing') or sub.end_date <= now:
        start = now
    sub.end_date = start + timedelta(days=days)
    sub.status = 'active'
    sub.save()
    profile = getattr(sub.user, 'userprofile', None)
    if profile and (plan.features or {}).get('vfa_unlock'):
        profile.is_premium = True
        profile.subscription_plan = plan
        profile.subscription_end_date = sub.end_date.date()
        profile.save(update_fields=['is_premium', 'subscription_plan', 'subscription_end_date'])
    return sub


class PlanListView(generics.ListAPIView):
    serializer_class = PlanSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Plan.objects.filter(active=True)
        user_type = self.request.query_params.get('type')
        if user_type in ('student', 'institute'):
            queryset = queryset.filter(user_type=user_type)
        return queryset


class CurrentSubscriptionView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sub = Subscription.objects.filter(
            user=request.user, status__in=('active', 'trialing')
        ).order_by('-end_date').first()
        if not sub:
            return Response({'detail': 'No active subscription found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = SubscriptionSerializer(sub)
        return Response(serializer.data)


class VfaAccessView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(vfa_access_payload(request.user))


class CreateCheckoutSessionView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan_id = request.data.get('plan_id')
        slug = request.data.get('plan_slug')
        if plan_id:
            plan = get_object_or_404(Plan, id=plan_id, active=True)
        elif slug:
            plan = get_object_or_404(Plan, slug=slug, active=True)
        else:
            return Response({'error': 'plan_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        key_id, _secret, _wh = _razorpay_creds()
        amount_paise = int(plan.price * 100)
        client = _razorpay_client()
        order_id = None
        live_mode = bool(client and key_id.startswith('rzp_'))

        if client:
            try:
                order = client.order.create(data={
                    'amount': amount_paise,
                    'currency': plan.currency or 'INR',
                    'receipt': f"receipt_{uuid.uuid4().hex[:10]}",
                    'notes': {'plan': plan.slug, 'user_id': str(request.user.id)},
                })
                order_id = order.get('id')
            except Exception as exc:
                logger.exception('Razorpay order create failed: %s', exc)
                if live_mode and not settings.DEBUG:
                    return Response(
                        {'error': 'Could not start Razorpay checkout. Try again in a moment.'},
                        status=status.HTTP_502_BAD_GATEWAY,
                    )

        if not order_id:
            order_id = f"order_mock_{uuid.uuid4().hex[:12]}"

        days = int((plan.features or {}).get('duration_days') or (30 if plan.interval == 'month' else 365))
        sub, created = Subscription.objects.get_or_create(
            user=request.user,
            plan=plan,
            defaults={
                'status': 'inactive',
                'end_date': timezone.now() + timedelta(days=days),
            }
        )
        if not created and sub.status == 'active' and sub.is_active():
            pass

        PaymentHistory.objects.create(
            user=request.user,
            subscription=sub,
            amount=plan.price,
            status='pending',
            razorpay_order_id=order_id,
        )

        return Response({
            'order_id': order_id,
            'amount': amount_paise,
            'currency': plan.currency or 'INR',
            'key': key_id,
            'plan_name': plan.name,
            'plan_slug': plan.slug,
            'compare_at': (plan.features or {}).get('compare_at'),
        }, status=status.HTTP_200_OK)


class VerifyCheckoutView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get('order_id')
        payment_id = request.data.get('payment_id')
        signature = request.data.get('signature')
        if not order_id:
            return Response({'error': 'order_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        payment_record = PaymentHistory.objects.filter(
            razorpay_order_id=order_id, user=request.user
        ).first()
        if not payment_record:
            return Response({'error': 'Matching order not found.'}, status=status.HTTP_404_NOT_FOUND)

        key_id, key_secret, _ = _razorpay_creds()
        is_mock = str(order_id).startswith('order_mock_')
        if is_mock and not settings.DEBUG:
            return Response({'error': 'Live payments cannot use mock orders.'}, status=status.HTTP_400_BAD_REQUEST)

        if not is_mock:
            if not payment_id or not signature:
                return Response({'error': 'payment_id and signature are required.'}, status=status.HTTP_400_BAD_REQUEST)
            expected = hmac.new(
                key_secret.encode('utf-8'),
                f'{order_id}|{payment_id}'.encode('utf-8'),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected, str(signature)):
                return Response({'error': 'Invalid payment signature.'}, status=status.HTTP_400_BAD_REQUEST)

        payment_record.status = 'success'
        payment_record.razorpay_payment_id = payment_id or payment_record.razorpay_payment_id
        payment_record.razorpay_signature = signature or ''
        payment_record.save()

        if payment_record.subscription:
            _activate_subscription(payment_record.subscription)

        return Response({
            'status': 'ok',
            'vfa': vfa_access_payload(request.user),
        }, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhookView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        payload_body = request.body.decode('utf-8')
        signature = request.headers.get('X-Razorpay-Signature')
        _key_id, _key_secret, webhook_secret = _razorpay_creds()

        if webhook_secret not in ('mockwebhooksecret', 'your_key_secret', '') and signature:
            expected_signature = hmac.new(
                webhook_secret.encode('utf-8'),
                payload_body.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(expected_signature, signature):
                return Response({'error': 'Invalid signature.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event_data = json.loads(payload_body)
            entity = event_data.get('payload', {}).get('payment', {}).get('entity', {})
            order_id = entity.get('order_id')
            payment_id = entity.get('id')
            payment_status = entity.get('status')
        except Exception:
            return Response({'error': 'Invalid payload format.'}, status=status.HTTP_400_BAD_REQUEST)

        if not order_id:
            order_id = request.data.get('order_id')
            payment_id = request.data.get('payment_id', f"pay_mock_{uuid.uuid4().hex[:12]}")
            payment_status = 'captured'
            signature = request.data.get('signature')
            if order_id and payment_id and signature:
                _key_id, key_secret, _wh = _razorpay_creds()
                expected = hmac.new(
                    key_secret.encode('utf-8'),
                    f'{order_id}|{payment_id}'.encode('utf-8'),
                    hashlib.sha256,
                ).hexdigest()
                if hmac.compare_digest(expected, str(signature)):
                    payment_status = 'captured'
                elif not settings.DEBUG:
                    return Response({'error': 'Invalid payment signature.'}, status=status.HTTP_400_BAD_REQUEST)

        if not order_id:
            return Response({'error': 'Order ID missing.'}, status=status.HTTP_400_BAD_REQUEST)

        payment_record = PaymentHistory.objects.filter(razorpay_order_id=order_id).first()
        if not payment_record:
            return Response({'error': 'Matching order not found.'}, status=status.HTTP_404_NOT_FOUND)

        if payment_status in ('captured', 'confirmed', 'success'):
            payment_record.status = 'success'
            payment_record.razorpay_payment_id = payment_id
            payment_record.save()
            if payment_record.subscription:
                _activate_subscription(payment_record.subscription)
            return Response({'status': 'Subscription updated successfully.'}, status=status.HTTP_200_OK)

        return Response({'status': 'No action taken.'}, status=status.HTTP_200_OK)

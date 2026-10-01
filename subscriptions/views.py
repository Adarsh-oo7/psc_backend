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
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Plan, Subscription, PaymentHistory
from .serializers import PlanSerializer, SubscriptionSerializer
from .vfa_access import has_vfa_unlock, vfa_access_payload, vfa_plan

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


def _is_one_time(plan):
    features = plan.features or {}
    return bool(features.get('vfa_unlock') or features.get('one_time'))


def _plan_already_active(user, plan):
    now = timezone.now()
    if Subscription.objects.filter(
        user=user, plan=plan, status__in=('active', 'trialing'), end_date__gt=now
    ).exists():
        return True
    return PaymentHistory.objects.filter(
        user=user, status='success', subscription__plan=plan
    ).exists()


def _activate_subscription(sub):
    plan = sub.plan
    now = timezone.now()
    one_time = _is_one_time(plan)
    already = sub.status in ('active', 'trialing') and sub.end_date and sub.end_date > now
    # A one-time unlock that is already active must not grow when a second payment is confirmed.
    if not (one_time and already):
        days = int((plan.features or {}).get('duration_days') or (30 if plan.interval == 'month' else 365))
        start = sub.end_date if already and not one_time else now
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


def _refund_payment(payment_id):
    client = _razorpay_client()
    if not client or not payment_id:
        return False
    try:
        client.payment.refund(payment_id, {'notes': {'reason': 'duplicate one-time unlock'}})
        return True
    except Exception:
        logger.exception('Could not refund duplicate payment %s', payment_id)
        return False


def _settle_captured_payment(record, payment_id='', signature=''):
    """Record a captured payment once. A second one-time charge is refunded."""
    with transaction.atomic():
        locked = PaymentHistory.objects.select_for_update().select_related(
            'subscription', 'subscription__plan', 'user'
        ).get(pk=record.pk)
        if locked.status == 'success':
            if locked.subscription_id:
                _activate_subscription(locked.subscription)
            return 'already'
        if locked.status == 'refunded':
            return 'refunded'

        plan = locked.subscription.plan if locked.subscription_id else None
        duplicate = False
        if plan and _is_one_time(plan):
            duplicate = PaymentHistory.objects.filter(
                user=locked.user,
                status='success',
                subscription__plan=plan,
            ).exclude(pk=locked.pk).exists()
            sub = locked.subscription
            now = timezone.now()
            if sub and sub.status in ('active', 'trialing') and sub.end_date and sub.end_date > now:
                duplicate = True

        if duplicate and payment_id and not str(locked.razorpay_order_id).startswith('order_mock_'):
            if not _refund_payment(payment_id):
                return 'refund_failed'
            locked.status = 'refunded'
            locked.razorpay_payment_id = payment_id
            if signature:
                locked.razorpay_signature = signature
            locked.save(update_fields=['status', 'razorpay_payment_id', 'razorpay_signature'])
            return 'refunded_duplicate'

        locked.status = 'success'
        if payment_id:
            locked.razorpay_payment_id = payment_id
        if signature:
            locked.razorpay_signature = signature
        locked.save(update_fields=['status', 'razorpay_payment_id', 'razorpay_signature'])
        if locked.subscription_id:
            _activate_subscription(locked.subscription)
        return 'success'


def reconcile_pending_payments(user, plan=None):
    """If Razorpay already captured a payment our verify call missed, unlock from that payment."""
    client = _razorpay_client()
    if not client or not user or not getattr(user, 'is_authenticated', False):
        return False
    since = timezone.now() - timedelta(days=2)
    pending = PaymentHistory.objects.filter(
        user=user, status='pending', created_at__gte=since
    ).exclude(razorpay_order_id__startswith='order_mock').select_related('subscription', 'subscription__plan')
    if plan is not None:
        pending = pending.filter(subscription__plan=plan)
    unlocked = False
    for record in pending.order_by('id')[:5]:
        try:
            order = client.order.fetch(record.razorpay_order_id)
        except Exception:
            logger.exception('Could not fetch Razorpay order %s', record.razorpay_order_id)
            continue
        if order.get('status') != 'paid':
            continue
        try:
            items = client.order.payments(record.razorpay_order_id).get('items') or []
        except Exception:
            logger.exception('Could not fetch payments for %s', record.razorpay_order_id)
            continue
        captured = next((item for item in items if item.get('status') == 'captured'), None)
        if not captured:
            continue
        payment_id = captured.get('id') or ''
        if payment_id and PaymentHistory.objects.filter(razorpay_payment_id=payment_id).exclude(pk=record.pk).exists():
            continue
        outcome = _settle_captured_payment(record, payment_id)
        if outcome in ('success', 'already', 'refunded_duplicate'):
            unlocked = True
    return unlocked


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
        if not has_vfa_unlock(request.user):
            reconcile_pending_payments(request.user, vfa_plan())
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
        live_mode = bool(client and key_id.startswith('rzp_'))

        reconcile_pending_payments(request.user, plan)
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            return self._open_order(request, plan, key_id, amount_paise, client, live_mode)

    def _open_order(self, request, plan, key_id, amount_paise, client, live_mode):
        if _is_one_time(plan) and _plan_already_active(request.user, plan):
            return Response({
                'already_active': True,
                'order_id': None,
                'amount': amount_paise,
                'currency': plan.currency or 'INR',
                'key': key_id,
                'plan_name': plan.name,
                'plan_slug': plan.slug,
                'vfa': vfa_access_payload(request.user),
            }, status=status.HTTP_200_OK)

        recent_cutoff = timezone.now() - timedelta(minutes=20)
        reusable = PaymentHistory.objects.filter(
            user=request.user,
            status='pending',
            subscription__plan=plan,
            created_at__gte=recent_cutoff,
        ).exclude(razorpay_order_id__startswith='order_mock').order_by('-id').first()
        if reusable and client:
            try:
                existing = client.order.fetch(reusable.razorpay_order_id)
            except Exception:
                existing = None
            if existing and existing.get('status') == 'created':
                return Response({
                    'already_active': False,
                    'order_id': reusable.razorpay_order_id,
                    'amount': amount_paise,
                    'currency': plan.currency or 'INR',
                    'key': key_id,
                    'plan_name': plan.name,
                    'plan_slug': plan.slug,
                    'compare_at': (plan.features or {}).get('compare_at'),
                }, status=status.HTTP_200_OK)

        order_id = None

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
            'already_active': False,
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

        if payment_record.status == 'refunded':
            return Response({'error': 'This payment was refunded.'}, status=status.HTTP_400_BAD_REQUEST)

        _key_id, key_secret, _ = _razorpay_creds()
        is_mock = str(order_id).startswith('order_mock_')
        if is_mock and not settings.DEBUG:
            return Response({'error': 'Live payments cannot use mock orders.'}, status=status.HTTP_400_BAD_REQUEST)

        if not is_mock and payment_record.status != 'success':
            if not payment_id or not signature:
                return Response({'error': 'payment_id and signature are required.'}, status=status.HTTP_400_BAD_REQUEST)
            expected = hmac.new(
                key_secret.encode('utf-8'),
                f'{order_id}|{payment_id}'.encode('utf-8'),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected, str(signature)):
                return Response({'error': 'Invalid payment signature.'}, status=status.HTTP_400_BAD_REQUEST)

        outcome = _settle_captured_payment(payment_record, payment_id or '', signature or '')
        if outcome == 'refund_failed':
            return Response({
                'status': 'ok',
                'already_active': True,
                'vfa': vfa_access_payload(request.user),
                'detail': 'Unlock is already active. The extra charge could not be refunded automatically.',
            }, status=status.HTTP_200_OK)
        return Response({
            'status': 'ok',
            'already_active': outcome in ('already', 'refunded_duplicate'),
            'refunded_duplicate': outcome == 'refunded_duplicate',
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
            outcome = _settle_captured_payment(payment_record, payment_id or '')
            if outcome == 'refund_failed':
                return Response({'status': 'Unlock already active. Duplicate refund failed.'}, status=status.HTTP_200_OK)
            if outcome == 'refunded_duplicate':
                return Response({'status': 'Duplicate payment refunded. Unlock stays active.'}, status=status.HTTP_200_OK)
            if outcome == 'already':
                return Response({'status': 'Already recorded.'}, status=status.HTTP_200_OK)
            if outcome == 'refunded':
                return Response({'status': 'Payment was refunded.'}, status=status.HTTP_200_OK)
            return Response({'status': 'Subscription updated successfully.'}, status=status.HTTP_200_OK)

        return Response({'status': 'No action taken.'}, status=status.HTTP_200_OK)

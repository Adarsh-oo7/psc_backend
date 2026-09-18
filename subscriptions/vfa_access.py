from .models import ExamSetAttempt, Plan, Subscription
from django.utils import timezone

VFA_SLUG = 'village-field-assistant'
VFA_FREE_SETS = 2
VFA_PLAN_SLUG = 'vfa-unlock'
VFA_PRICE = 29
VFA_COMPARE_AT = 499


def is_vfa_exam(exam=None, slug='', name=''):
    hay = f"{getattr(exam, 'slug', '') or ''} {getattr(exam, 'name', '') or ''} {slug or ''} {name or ''}".lower()
    return 'village-field' in hay or 'village field' in hay or ' vfa' in f' {hay}' or hay.strip() in ('vfa',)


def has_vfa_unlock(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    now = timezone.now()
    subs = Subscription.objects.filter(
        user=user,
        status__in=('active', 'trialing'),
        end_date__gt=now,
    ).select_related('plan')
    for sub in subs:
        features = sub.plan.features or {}
        if sub.plan.slug == VFA_PLAN_SLUG or features.get('vfa_unlock') or features.get('premium_mock_tests'):
            return True
    profile = getattr(user, 'userprofile', None)
    if profile and getattr(profile, 'is_premium', False):
        end = getattr(profile, 'subscription_end_date', None)
        if end is None or end >= timezone.now().date():
            return True
    return False


def vfa_sets_used(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return 0
    return ExamSetAttempt.objects.filter(user=user, exam_slug=VFA_SLUG).count()


def record_vfa_set(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return
    ExamSetAttempt.objects.create(user=user, exam_slug=VFA_SLUG)


def vfa_plan():
    return Plan.objects.filter(slug=VFA_PLAN_SLUG, active=True).first()


def vfa_access_payload(user):
    plan = vfa_plan()
    unlocked = has_vfa_unlock(user)
    used = vfa_sets_used(user)
    remaining = 0 if unlocked else max(0, VFA_FREE_SETS - used)
    return {
        'unlocked': unlocked,
        'free_sets': VFA_FREE_SETS,
        'sets_used': used,
        'sets_remaining': remaining,
        'can_attempt': unlocked or used < VFA_FREE_SETS,
        'price': float(plan.price) if plan else VFA_PRICE,
        'compare_at': (plan.features or {}).get('compare_at', VFA_COMPARE_AT) if plan else VFA_COMPARE_AT,
        'plan_id': plan.id if plan else None,
        'plan_slug': VFA_PLAN_SLUG,
        'plan_name': plan.name if plan else 'VFA Full Unlock',
        'currency': 'INR',
    }


def vfa_paywall_response(user=None):
    from rest_framework.response import Response
    from rest_framework import status
    payload = vfa_access_payload(user)
    payload['code'] = 'vfa_unlock_required'
    payload['detail'] = 'You have used 2 free VFA sets. Unlock all VFA mocks for ₹29.'
    payload['can_attempt'] = False
    return Response(payload, status=status.HTTP_402_PAYMENT_REQUIRED)

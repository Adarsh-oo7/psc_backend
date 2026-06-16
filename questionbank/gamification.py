from django.utils import timezone
from .models import UserProfile
from datetime import timedelta

def award_xp(user, amount):
    """
    Awards XP to a user's UserProfile.
    Also recalculates their level where 1 level = 100 XP (level = total_xp // 100 + 1).
    Returns (xp_awarded, level_up, new_level)
    """
    try:
        profile = user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)
        
    old_level = profile.level
    profile.total_xp += amount
    
    # 1 level per 100 XP
    new_level = (profile.total_xp // 100) + 1
    profile.level = new_level
    
    profile.save(update_fields=['total_xp', 'level'])
    
    level_up = new_level > old_level
    return amount, level_up, new_level

def update_streak(user):
    """
    Updates a user's streak based on their daily activity.
    Logic:
    - If never active, sets streak to 1.
    - If active today, does nothing.
    - If active yesterday (last_active_date == today - 1), increments streak.
    - If active before yesterday:
        - If they have streak freezes left, decrement freeze and preserve streak.
        - Otherwise, reset streak to 1.
    Returns (current_streak, longest_streak, freeze_used)
    """
    try:
        profile = user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)

    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    current_streak = profile.current_streak
    longest_streak = profile.longest_streak
    freeze_used = False
    
    if profile.last_active_date is None:
        # First activity ever
        current_streak = 1
        longest_streak = max(longest_streak, 1)
        profile.last_active_date = today
    elif profile.last_active_date == today:
        # Already active today, do nothing
        pass
    elif profile.last_active_date == yesterday:
        # Active yesterday, streak continues!
        current_streak += 1
        longest_streak = max(longest_streak, current_streak)
        profile.last_active_date = today
        # Award streak bonus XP!
        award_xp(user, 20)
    else:
        # Missed day(s)
        if profile.streak_freeze_count > 0:
            profile.streak_freeze_count -= 1
            freeze_used = True
            # Keep the streak as is, but mark active today so they don't lose it tomorrow
            profile.last_active_date = today
        else:
            # Reset streak to 1
            current_streak = 1
            profile.last_active_date = today

    profile.current_streak = current_streak
    profile.longest_streak = longest_streak
    profile.save(update_fields=['current_streak', 'longest_streak', 'last_active_date', 'streak_freeze_count'])
    
    streak_promo_awarded = False
    if current_streak >= 5 and not profile.is_premium:
        from subscriptions.models import Plan, Subscription
        
        pro_plan = Plan.objects.filter(slug='pro-monthly').first()
        profile.is_premium = True
        profile.subscription_end_date = today + timedelta(days=30)
        if pro_plan:
            profile.subscription_plan = pro_plan
        profile.save(update_fields=['is_premium', 'subscription_end_date', 'subscription_plan'])
        
        # Create Subscription record
        Subscription.objects.create(
            user=user,
            plan=pro_plan or Plan.objects.first(),
            status='active',
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30)
        )
        streak_promo_awarded = True

    return current_streak, longest_streak, freeze_used, streak_promo_awarded

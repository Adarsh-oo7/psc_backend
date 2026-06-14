from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from questionbank.models import UserProfile, Question, Topic, StudyFeedCard, UserFeedView, AIExplanationCache
from questionbank.gamification import award_xp, update_streak
from subscriptions.models import Plan, Subscription

class GamificationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student1', password='password123')
        # Setup plans
        self.free_plan = Plan.objects.create(
            name='Free Plan',
            slug='student-free',
            price=0.00,
            interval='month',
            user_type='student',
            features={'feed_limit': 15}
        )
        self.basic_plan = Plan.objects.create(
            name='Basic Plan',
            slug='student-basic',
            price=99.00,
            interval='month',
            user_type='student',
            features={'feed_limit': 40}
        )

    def test_award_xp(self):
        # Initial profile check
        profile = UserProfile.objects.create(user=self.user)
        self.assertEqual(profile.total_xp, 0)
        self.assertEqual(profile.level, 1)
        
        # Award 50 XP
        xp, level_up, new_level = award_xp(self.user, 50)
        self.assertEqual(xp, 50)
        self.assertFalse(level_up)
        self.assertEqual(new_level, 1)
        
        # Award another 60 XP -> Total 110 XP, level up to 2
        xp, level_up, new_level = award_xp(self.user, 60)
        self.assertEqual(xp, 60)
        self.assertTrue(level_up)
        self.assertEqual(new_level, 2)
        
        profile.refresh_from_db()
        self.assertEqual(profile.total_xp, 110)
        self.assertEqual(profile.level, 2)

    def test_update_streak_logic(self):
        profile = UserProfile.objects.create(user=self.user)
        self.assertEqual(profile.current_streak, 0)
        
        # 1. First activity
        current_streak, longest_streak, freeze_used = update_streak(self.user)
        self.assertEqual(current_streak, 1)
        self.assertEqual(longest_streak, 1)
        self.assertFalse(freeze_used)
        
        # 2. Active same day: streak remains 1
        current_streak, longest_streak, freeze_used = update_streak(self.user)
        self.assertEqual(current_streak, 1)
        self.assertFalse(freeze_used)
        
        # 3. Active next day (mock last_active_date to yesterday)
        profile.last_active_date = timezone.now().date() - timedelta(days=1)
        profile.save()
        
        current_streak, longest_streak, freeze_used = update_streak(self.user)
        self.assertEqual(current_streak, 2)
        self.assertEqual(longest_streak, 2)
        self.assertFalse(freeze_used)
        
        # 4. Missed a day, but has streak freeze
        profile.last_active_date = timezone.now().date() - timedelta(days=3)
        profile.streak_freeze_count = 1
        profile.save()
        
        current_streak, longest_streak, freeze_used = update_streak(self.user)
        self.assertEqual(current_streak, 2) # Preserved
        self.assertTrue(freeze_used)
        
        # 5. Missed a day, no streak freeze -> reset
        profile.refresh_from_db()
        profile.last_active_date = timezone.now().date() - timedelta(days=3)
        profile.streak_freeze_count = 0
        profile.save()
        
        current_streak, longest_streak, freeze_used = update_streak(self.user)
        self.assertEqual(current_streak, 1) # Reset
        self.assertFalse(freeze_used)

from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

class StudyFeedLimitTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student_feed', password='password123')
        self.profile = UserProfile.objects.create(user=self.user)
        
        # Seed feed cards
        self.cards = []
        for i in range(20):
            card = StudyFeedCard.objects.create(
                card_type='fact',
                title=f'Fact {i}',
                content_data={'fact_text': f'Text {i}'}
            )
            self.cards.append(card)
            
        # JWT Authorization Setup
        token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_free_feed_limit(self):
        # Free default limit is 15. Let's record 15 views today.
        today = timezone.now().date()
        for i in range(15):
            UserFeedView.objects.create(user=self.user, card=self.cards[i], viewed_date=today)
            
        # Try getting feed
        response = self.client.get('/api/study-feed/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['limit_exceeded'])
        self.assertEqual(len(response.data['cards']), 0)
        
    def test_record_view_limit(self):
        today = timezone.now().date()
        
        # Record 15 views
        for i in range(15):
            UserFeedView.objects.create(user=self.user, card=self.cards[i], viewed_date=today)
            
        # Trying to record 16th view should fail with 403
        response = self.client.post('/api/study-feed/view/', {'card_id': self.cards[15].id}, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertTrue(response.data['limit_exceeded'])

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


class StudyFlowTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student_study', password='password123')
        self.profile = UserProfile.objects.create(user=self.user)
        
        # Create topics
        self.topic1 = Topic.objects.create(name='History', slug='history')
        self.topic2 = Topic.objects.create(name='Geography', slug='geography')
        
        # Create questions
        self.q1 = Question.objects.create(
            topic=self.topic1,
            text='Who was the first President of India?',
            options={'A': 'Rajendra Prasad', 'B': 'Nehru', 'C': 'Radhakrishnan', 'D': 'Ambedkar'},
            correct_answer='A',
            difficulty='easy'
        )
        self.q2 = Question.objects.create(
            topic=self.topic1,
            text='In which year did India get independence?',
            options={'A': '1947', 'B': '1950', 'C': '1935', 'D': '1942'},
            correct_answer='A',
            difficulty='medium'
        )
        self.q3 = Question.objects.create(
            topic=self.topic1,
            text='Who wrote Discovery of India?',
            options={'A': 'Nehru', 'B': 'Gandhi', 'C': 'Bose', 'D': 'Tagore'},
            correct_answer='A',
            difficulty='hard'
        )
        
        # Setup plans
        self.free_plan = Plan.objects.create(
            name='Free Plan',
            slug='student-free',
            price=0.00,
            interval='month',
            user_type='student',
            features={'feed_limit': 15}
        )
        
        # JWT Authorization Setup
        token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_signal_update_topic_progress(self):
        from questionbank.models import UserAnswer, TopicProgress
        # Verify signal updates TopicProgress on UserAnswer save
        ua = UserAnswer.objects.create(
            user=self.user,
            question=self.q1,
            selected_option='A',
            is_correct=True
        )
        progress = TopicProgress.objects.get(user=self.user, topic=self.topic1)
        self.assertEqual(progress.total_attempted, 1)
        self.assertEqual(progress.total_correct, 1)
        self.assertEqual(progress.easy_attempted, 1)
        self.assertEqual(progress.easy_correct, 1)

        # Another answer (incorrect)
        UserAnswer.objects.create(
            user=self.user,
            question=self.q2,
            selected_option='B',
            is_correct=False
        )
        progress.refresh_from_db()
        self.assertEqual(progress.total_attempted, 2)
        self.assertEqual(progress.total_correct, 1)
        self.assertEqual(progress.medium_attempted, 1)
        self.assertEqual(progress.medium_correct, 0)

    def test_topic_with_progress_list_view(self):
        # Trigger some progress first
        from questionbank.models import UserAnswer
        UserAnswer.objects.create(user=self.user, question=self.q1, selected_option='A', is_correct=True)
        
        response = self.client.get('/api/topics/')
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(len(data), 2)  # History, Geography
        history = next(item for item in data if item['slug'] == 'history')
        self.assertEqual(history['question_count'], 3)
        self.assertEqual(history['user_accuracy'], 100.0)
        self.assertFalse(history['is_weak_area'])

    def test_topic_questions_list_view(self):
        # Normal request (paginated)
        response = self.client.get('/api/topics/history/questions/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)

        # Difficulty filter
        response = self.client.get('/api/topics/history/questions/?difficulty=easy')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.q1.id)

        # Exclude answered correctly
        from questionbank.models import UserAnswer
        UserAnswer.objects.create(user=self.user, question=self.q1, selected_option='A', is_correct=True)
        response = self.client.get('/api/topics/history/questions/?exclude_answered=true')
        self.assertEqual(response.status_code, 200)
        # q1 should be excluded
        q_ids = [q['id'] for q in response.data['results']]
        self.assertNotIn(self.q1.id, q_ids)

    def test_practice_session_start_and_submit(self):
        # Start practice
        payload = {
            'topic_slug': 'history',
            'difficulty': 'easy',
            'count': 5,
            'session_type': 'topic'
        }
        response = self.client.post('/api/practice/start/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('session_id', response.data)
        session_id = response.data['session_id']
        self.assertEqual(len(response.data['questions']), 1)
        self.assertEqual(response.data['questions'][0]['id'], self.q1.id)

        # Submit practice
        submit_payload = {
            'answers': [
                {
                    'question_id': self.q1.id,
                    'selected_option': 'A',
                    'time_spent_secs': 5
                }
            ],
            'total_time_secs': 5
        }
        submit_response = self.client.post(f'/api/practice/{session_id}/submit/', submit_payload, format='json')
        self.assertEqual(submit_response.status_code, 200)
        self.assertEqual(submit_response.data['correct_count'], 1)
        self.assertEqual(submit_response.data['score_percent'], 100.0)
        self.assertEqual(submit_response.data['xp_earned'], 12)  # (1*10) + (1*2) = 12

    def test_analytics_weak_areas_and_summary(self):
        from questionbank.models import TopicProgress
        # Make user weak in history: total_attempted >= 10, accuracy < 50
        tp = TopicProgress.objects.create(
            user=self.user,
            topic=self.topic1,
            total_attempted=12,
            total_correct=3,  # 25% accuracy
            easy_attempted=12,
            easy_correct=3
        )
        
        # Weak areas endpoint
        response = self.client.get('/api/analytics/weak-areas/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['topic_slug'], 'history')
        self.assertEqual(response.data[0]['accuracy'], 25.0)

        # Topic summary endpoint
        response = self.client.get('/api/analytics/topic-summary/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)  # History and Geography
        history = next(item for item in response.data if item['topic_slug'] == 'history')
        self.assertEqual(history['accuracy'], 25.0)



from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from questionbank.models import UserProfile, Question, Topic, StudyFeedCard, UserFeedView, AIExplanationCache, Exam
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
        # Since the app is now 100% free/unlimited, recording 15 views does NOT hit the limit.
        today = timezone.now().date()
        for i in range(15):
            UserFeedView.objects.create(user=self.user, card=self.cards[i], viewed_date=today)
            
        # Try getting feed
        response = self.client.get('/api/study-feed/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['limit_exceeded'])
        
    def test_record_view_limit(self):
        today = timezone.now().date()
        
        # Record 15 views
        for i in range(15):
            UserFeedView.objects.create(user=self.user, card=self.cards[i], viewed_date=today)
            
        # Trying to record 16th view should succeed (no limit)
        response = self.client.post('/api/study-feed/view/', {'card_id': self.cards[15].id}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])



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


class QuestionEngineTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='engine_student', password='password123')
        self.topic1 = Topic.objects.create(name='Polity', slug='polity')
        self.topic2 = Topic.objects.create(name='Science', slug='science')

        # Create multiple questions
        self.questions = []
        for i in range(5):
            q = Question.objects.create(
                topic=self.topic1,
                text=f'Polity Question {i}',
                options={'A': 'AnsA', 'B': 'AnsB', 'C': 'AnsC', 'D': 'AnsD'},
                correct_answer='A',
                difficulty='medium'
            )
            self.questions.append(q)

        for i in range(5):
            q = Question.objects.create(
                topic=self.topic2,
                text=f'Science Question {i}',
                options={'A': 'AnsA', 'B': 'AnsB', 'C': 'AnsC', 'D': 'AnsD'},
                correct_answer='A',
                difficulty='easy'
            )
            self.questions.append(q)

        # JWT Authorization Setup
        token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_unseen_questions_prioritized(self):
        from questionbank.engine import QuestionEngine
        from questionbank.models import UserAnswer

        # User has answered Polity Question 0 and 1
        UserAnswer.objects.create(user=self.user, question=self.questions[0], selected_option='A', is_correct=True)
        UserAnswer.objects.create(user=self.user, question=self.questions[1], selected_option='B', is_correct=False)

        # Get questions for user in Polity
        qs = QuestionEngine.get_questions_for_user(self.user, filters={'topic_id': self.topic1.id}, limit=3)
        self.assertEqual(qs.count(), 3)
        # Verify that questions[0] and questions[1] are NOT in the result since they are answered and there are unseen ones
        result_ids = [q.id for q in qs]
        self.assertNotIn(self.questions[0].id, result_ids)
        self.assertNotIn(self.questions[1].id, result_ids)

    def test_stale_fallback(self):
        from questionbank.engine import QuestionEngine
        from questionbank.models import UserAnswer

        # Answer ALL Polity questions (questions 0 to 4)
        for i in range(5):
            ua = UserAnswer.objects.create(user=self.user, question=self.questions[i], selected_option='A', is_correct=True)
            # Make one of them answered 40 days ago (stale)
            if i == 0:
                ua.answered_at = timezone.now() - timedelta(days=40)
                ua.save()

        # Get questions: unseen is empty, should fall back to stale (>30 days)
        qs = QuestionEngine.get_questions_for_user(self.user, filters={'topic_id': self.topic1.id}, limit=1)
        self.assertEqual(qs.count(), 1)
        # Should return questions[0] because it is the only stale one
        self.assertEqual(qs.first().id, self.questions[0].id)

    def test_oldest_fallback(self):
        from questionbank.engine import QuestionEngine
        from questionbank.models import UserAnswer

        # Answer ALL Polity questions recently (e.g. within last few minutes/hours)
        now = timezone.now()
        for i in range(5):
            ua = UserAnswer.objects.create(user=self.user, question=self.questions[i], selected_option='A', is_correct=True)
            # Offset their answered_at to test ordering
            ua.answered_at = now - timedelta(hours=10 - i)
            ua.save()

        # Get questions: unseen and stale pools are empty. Fall back to absolute oldest answered.
        qs = QuestionEngine.get_questions_for_user(self.user, filters={'topic_id': self.topic1.id}, limit=2)
        # Sliced query returns 2 questions
        # Oldest answered should be questions[0] (answered now - 10 hours) and questions[1] (now - 9 hours)
        result_ids = [q.id for q in qs]
        self.assertIn(self.questions[0].id, result_ids)
        self.assertIn(self.questions[1].id, result_ids)

    def test_weak_area_questions(self):
        from questionbank.engine import QuestionEngine
        from questionbank.models import TopicProgress

        # Create weak topic progress for polity (total=6, correct=1 -> 16.7% accuracy)
        TopicProgress.objects.create(
            user=self.user,
            topic=self.topic1,
            total_attempted=6,
            total_correct=1,
            easy_attempted=6,
            easy_correct=1
        )

        # Get weak area questions
        qs = QuestionEngine.get_weak_area_questions(self.user, limit=5)
        self.assertTrue(qs.count() > 0)
        # Verify only polity questions are returned (science is not a weak area topic)
        for q in qs:
            self.assertEqual(q.topic.slug, 'polity')

    def test_daily_quiz_uniqueness(self):
        from questionbank.engine import QuestionEngine
        from questionbank.models import UserAnswer

        # Answer polity question 0 today
        UserAnswer.objects.create(user=self.user, question=self.questions[0], selected_option='A', is_correct=True)

        # Get daily quiz
        qs = QuestionEngine.get_daily_quiz(self.user, limit=10)
        result_ids = [q.id for q in qs]
        # Should NOT include polity question 0 as it was answered today
        self.assertNotIn(self.questions[0].id, result_ids)

    def test_view_integrations(self):
        # 1. Question list view with personalization
        from questionbank.models import UserAnswer
        # Answer Polity Question 0
        UserAnswer.objects.create(user=self.user, question=self.questions[0], selected_option='A', is_correct=True)
        response = self.client.get('/api/questions/?topic_id=' + str(self.topic1.id))
        self.assertEqual(response.status_code, 200)
        # Result should exclude Polity Question 0 (total 5 Polity questions, 1 answered -> 4 returned)
        self.assertEqual(len(response.data), 4)
        result_ids = [q['id'] for q in response.data]
        self.assertNotIn(self.questions[0].id, result_ids)

        # 2. Daily quiz view
        response = self.client.get('/api/questions/daily-quiz/?limit=5')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 5)

        # 3. Weak areas questions view
        from questionbank.models import TopicProgress
        TopicProgress.objects.update_or_create(
            user=self.user,
            topic=self.topic1,
            defaults={
                'total_attempted': 6,
                'total_correct': 1
            }
        )
        response = self.client.get('/api/questions/weak-areas/?limit=3')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.data) > 0)
        for q in response.data:
            self.assertEqual(q['topic'], self.topic1.name)

        # 4. Practice session weak areas starting
        payload = {
            'session_type': 'weak_area',
            'count': 3
        }
        response = self.client.post('/api/practice/start/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('session_id', response.data)
        self.assertTrue(len(response.data['questions']) > 0)
        for q in response.data['questions']:
            self.assertEqual(q['topic'], self.topic1.name)


from questionbank.utils import find_similar_questions

class CommunitySubmissionAndDeduplicationTestCase(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(username='admin', password='adminpassword')
        self.regular_user = User.objects.create_user(username='student_sub', password='password123')
        self.profile = UserProfile.objects.create(user=self.regular_user)
        self.topic = Topic.objects.create(name='Polity', slug='polity')
        self.exam = Exam.objects.create(name='LDC (Lower Division Clerk)', slug='ldc', year=2025)

        # JWT Tokens
        self.user_token = RefreshToken.for_user(self.regular_user).access_token
        self.admin_token = RefreshToken.for_user(self.admin_user).access_token

    def test_text_normalization_and_hashing_on_save(self):
        q = Question.objects.create(
            text="Which is the largest state in India?",
            options={'A': 'Rajasthan', 'B': 'UP', 'C': 'MP', 'D': 'Maharashtra'},
            correct_answer='A',
            topic=self.topic,
            difficulty='medium'
        )
        self.assertIsNotNone(q.text_hash)
        self.assertIsNotNone(q.slug)
        self.assertTrue(q.slug.startswith('which-is-the-largest-state'))

    def test_submit_question_api(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user_token}')
        payload = {
            'question_text': "What is the capital of Kerala?",
            'option_a': "Kochi",
            'option_b': "Trivandrum",
            'option_c': "Calicut",
            'option_d': "Kollam",
            'correct_answer': "B",
            'topic_id': self.topic.id,
            'exam_id': self.exam.id,
            'explanation': "Trivandrum is the capital.",
            'language': "en"
        }
        response = self.client.post('/api/questions/submit/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'pending')
        self.assertEqual(response.data['correct_answer'], 'B')

        # Check duplicate submission fails
        response2 = self.client.post('/api/questions/submit/', payload, format='json')
        self.assertEqual(response2.status_code, 400)
        self.assertIn("question_text", response2.data)

    def test_my_submissions_list_api(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user_token}')
        # Create a submission
        Question.objects.create(
            text="Submission 1 text here.",
            options={'A': '1', 'B': '2', 'C': '3', 'D': '4'},
            correct_answer='A',
            topic=self.topic,
            submitted_by=self.regular_user,
            status='pending'
        )
        response = self.client.get('/api/questions/my-submissions/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['text'], "Submission 1 text here.")

    def test_pending_submissions_list_api(self):
        # Create a submission
        q = Question.objects.create(
            text="Pending question text.",
            options={'A': '1', 'B': '2', 'C': '3', 'D': '4'},
            correct_answer='A',
            topic=self.topic,
            submitted_by=self.regular_user,
            status='pending'
        )
        
        # Try listing with normal user -> should be forbidden (since IsAdminUser is required)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user_token}')
        response = self.client.get('/api/questions/pending/')
        self.assertEqual(response.status_code, 403)

        # Admin user
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.get('/api/questions/pending/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], q.id)

    def test_approve_reject_endpoints(self):
        q = Question.objects.create(
            text="Question to approve/reject.",
            options={'A': '1', 'B': '2', 'C': '3', 'D': '4'},
            correct_answer='A',
            topic=self.topic,
            submitted_by=self.regular_user,
            status='pending'
        )

        # Regular user try to approve
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user_token}')
        response = self.client.post(f'/api/questions/{q.id}/approve/')
        self.assertEqual(response.status_code, 403)

        # Admin approve
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post(f'/api/questions/{q.id}/approve/')
        self.assertEqual(response.status_code, 200)

        q.refresh_from_db()
        self.assertEqual(q.status, 'approved')
        self.assertTrue(q.verified)
        self.assertTrue(q.is_verified)

        # Check XP award
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.total_xp, 100)

        # Admin reject a new pending question
        q2 = Question.objects.create(
            text="Question to reject.",
            options={'A': '1', 'B': '2', 'C': '3', 'D': '4'},
            correct_answer='A',
            topic=self.topic,
            submitted_by=self.regular_user,
            status='pending'
        )
        response = self.client.post(f'/api/questions/{q2.id}/reject/')
        self.assertEqual(response.status_code, 200)
        q2.refresh_from_db()
        self.assertEqual(q2.status, 'rejected')

    def test_fuzzy_deduplication_helper(self):
        q = Question.objects.create(
            text="Which is the capital of India?",
            options={'A': 'Delhi', 'B': 'Mumbai', 'C': 'Kolkata', 'D': 'Chennai'},
            correct_answer='A',
            topic=self.topic,
            difficulty='medium'
        )
        
        # Test exact match (using text_hash)
        sim = find_similar_questions("Which is the capital of India?")
        self.assertEqual(len(sim), 1)
        self.assertEqual(sim[0].id, q.id)

        # Test fuzzy match
        sim2 = find_similar_questions("Which is the capital of India really?")
        self.assertEqual(len(sim2), 1)
        self.assertEqual(sim2[0].id, q.id)

        # Test mismatch
        sim3 = find_similar_questions("Who is the Prime Minister of India?")
        self.assertEqual(len(sim3), 0)

    def test_find_duplicates_command(self):
        from django.core.management import call_command
        from io import StringIO

        q1 = Question.objects.create(
            text="Which is the largest country in the world?",
            options={'A': '1', 'B': '2', 'C': '3', 'D': '4'},
            correct_answer='A',
            topic=self.topic
        )
        q2 = Question.objects.create(
            text="Which is the largest country in the world today?",
            options={'A': '1', 'B': '2', 'C': '3', 'D': '4'},
            correct_answer='A',
            topic=self.topic
        )

        out = StringIO()
        call_command('find_duplicates', stdout=out)
        self.assertIn("Found 1 groups of duplicates.", out.getvalue())

        # Test fix
        out_fix = StringIO()
        call_command('find_duplicates', '--fix', stdout=out_fix)
        q2.refresh_from_db()
        self.assertEqual(q2.status, 'rejected')


from unittest.mock import patch

class GoogleSignInTestCase(APITestCase):
    def setUp(self):
        # Configure client ID for testing
        from django.conf import settings
        self.original_client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
        settings.GOOGLE_CLIENT_ID = 'test-client-id'

    def tearDown(self):
        from django.conf import settings
        settings.GOOGLE_CLIENT_ID = self.original_client_id

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_google_sign_in_new_user(self, mock_verify):
        # Configure mock return value
        mock_verify.return_value = {
            'iss': 'accounts.google.com',
            'email': 'mockuser@example.com',
            'given_name': 'Mock',
            'family_name': 'User',
            'sub': '1234567890'
        }

        # Sign in
        response = self.client.post('/api/auth/google/', {'credential': 'mock_token'}, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertFalse(response.data['has_preferred_exams'])
        
        # Verify user and profile were created
        self.assertTrue(User.objects.filter(email='mockuser@example.com').exists())
        user = User.objects.get(email='mockuser@example.com')
        self.assertEqual(user.first_name, 'Mock')
        self.assertEqual(user.last_name, 'User')
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_google_sign_in_existing_user(self, mock_verify):
        # Create user beforehand
        existing_user = User.objects.create_user(
            username='existinggoogle',
            email='mockuser@example.com',
            first_name='Existing',
            last_name='User'
        )
        UserProfile.objects.create(user=existing_user)

        mock_verify.return_value = {
            'iss': 'accounts.google.com',
            'email': 'mockuser@example.com',
            'given_name': 'Mock',
            'family_name': 'User',
            'sub': '1234567890'
        }

        # Sign in
        response = self.client.post('/api/auth/google/', {'credential': 'mock_token'}, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        
        # Verify no duplicate user was created
        self.assertEqual(User.objects.filter(email='mockuser@example.com').count(), 1)

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_google_sign_in_invalid_token(self, mock_verify):
        # Mock ValueError for verification failure
        mock_verify.side_effect = ValueError("Invalid signature")

        response = self.client.post('/api/auth/google/', {'credential': 'invalid_token'}, format='json')
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'Invalid Google token.')

    def test_google_sign_in_missing_credential(self):
        response = self.client.post('/api/auth/google/', {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'Credential token is required.')






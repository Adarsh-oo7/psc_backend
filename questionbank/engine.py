from datetime import timedelta
from django.utils import timezone
from django.db.models import Q, F, Max
from .models import Question, UserAnswer, TopicProgress


class QuestionEngine:
    """
    The core engine for serving non-repeated questions.
    All question delivery goes through this class.
    """

    @staticmethod
    def get_questions_for_user(user, filters: dict, limit: int = None):
        """
        Returns questions filtered by criteria, prioritizing:
        1. Questions never answered by the user
        2. Questions not answered in the last 30 days
        3. Fallback: least-recently-answered questions (oldest answered_at timestamp)
        """
        # Base query to support tenant-aware (institute) questions
        base_query = Q(institute__isnull=True)
        if user and user.is_authenticated and hasattr(user, 'userprofile') and user.userprofile.institute:
            base_query |= Q(institute=user.userprofile.institute)

        queryset = Question.objects.filter(base_query)

        # Apply content filters
        if filters.get('exam_id'):
            exam_id = filters['exam_id']
            exam_qs = queryset.filter(exams__id=exam_id)
            if not exam_qs.exists():
                from .models import Exam
                exam = Exam.objects.filter(id=exam_id).first()
                if exam:
                    words = [w for w in exam.name.replace('(', '').replace(')', '').replace('/', ' ').split() if len(w) > 2]
                    similar_exams = Exam.objects.none()
                    if words:
                        q_obj = Q()
                        for word in words:
                            q_obj |= Q(name__icontains=word)
                        similar_exams = Exam.objects.filter(q_obj).exclude(id=exam_id)
                    if similar_exams.exists():
                        exam_qs = queryset.filter(exams__in=similar_exams)
                    if not exam_qs.exists() and exam.category:
                        exam_qs = queryset.filter(exams__category=exam.category)
            queryset = exam_qs
        if filters.get('topic_id'):
            queryset = queryset.filter(topic_id=filters['topic_id'])
        if filters.get('topic_ids'):
            queryset = queryset.filter(topic_id__in=filters['topic_ids'])
        if filters.get('difficulty'):
            queryset = queryset.filter(difficulty=filters['difficulty'])
        if filters.get('exclude_ids'):
            queryset = queryset.exclude(id__in=filters['exclude_ids'])

        if user and user.is_authenticated:
            # Get all question IDs answered by this user
            answered_ids = UserAnswer.objects.filter(
                user=user
            ).values_list('question_id', flat=True).distinct()

            # Pool 1: Never answered questions
            unseen = queryset.exclude(id__in=answered_ids)

            # Check if there are unseen questions
            if unseen.exists():
                if limit:
                    return unseen.order_by('?')[:limit]
                return unseen.order_by('?')

            # Pool 2: Questions not answered in the last 30 days
            stale_cutoff = timezone.now() - timedelta(days=30)
            stale_questions = queryset.annotate(
                user_last_answered=Max('user_answers__answered_at', filter=Q(user_answers__user=user))
            ).filter(
                user_last_answered__lt=stale_cutoff
            )

            if stale_questions.exists():
                if limit:
                    return stale_questions.order_by('?')[:limit]
                return stale_questions.order_by('?')

            # Pool 3: Fallback - absolute oldest answered first (least-recently-answered)
            fallback_questions = queryset.annotate(
                user_last_answered=Max('user_answers__answered_at', filter=Q(user_answers__user=user))
            ).order_by('user_last_answered')

            if limit:
                return fallback_questions[:limit]
            return fallback_questions
        else:
            # Anonymous user: return random questions matching the filters
            if limit:
                return queryset.order_by('?')[:limit]
            return queryset.order_by('?')

    @staticmethod
    def get_weak_area_questions(user, limit: int = 20):
        """Returns questions from topics where user accuracy < 50%."""
        if not user or not user.is_authenticated:
            return Question.objects.none()

        # Get weak topic IDs (total_attempted >= 5 and total_correct < total_attempted * 0.5)
        weak_topics = TopicProgress.objects.filter(
            user=user,
            total_attempted__gte=5,
            total_correct__lt=F('total_attempted') * 0.5
        ).values_list('topic_id', flat=True)

        return QuestionEngine.get_questions_for_user(
            user,
            filters={'topic_ids': list(weak_topics)},
            limit=limit
        )

    @staticmethod
    def get_daily_quiz(user, limit: int = 10):
        """Returns today's daily quiz questions — unique per user per day."""
        if not user or not user.is_authenticated:
            return QuestionEngine.get_questions_for_user(user, filters={}, limit=limit)

        today = timezone.now().date()

        # Questions answered today
        answered_today_ids = UserAnswer.objects.filter(
            user=user,
            answered_at__date=today
        ).values_list('question_id', flat=True)

        return QuestionEngine.get_questions_for_user(
            user,
            filters={'exclude_ids': list(answered_today_ids)},
            limit=limit
        )

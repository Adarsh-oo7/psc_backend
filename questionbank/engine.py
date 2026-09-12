from datetime import timedelta
from django.db.models import Q, F, Max, OuterRef, Subquery, Case, When, IntegerField
from django.utils import timezone
from .kpsc_format import interleave_reviews
from .models import Question, UserAnswer, TopicProgress


class QuestionEngine:
    """
    The core engine for serving non-repeated questions.
    All question delivery goes through this class.
    """

    @staticmethod
    def _resolve_similar_exams(exams_queryset):
        from .models import Exam
        if not exams_queryset.exists():
            return Exam.objects.none()
            
        q_obj = Q()
        for exam in exams_queryset:
            q_obj |= Q(id=exam.id)
            words = [w for w in exam.name.replace('(', '').replace(')', '').replace('/', ' ').split() if len(w) > 2]
            if words:
                sub_q = Q()
                for word in words:
                    sub_q |= Q(name__icontains=word)
                q_obj |= sub_q
                
        return Exam.objects.filter(q_obj).distinct()

    @staticmethod
    def _ordered_qs(ids):
        if not ids:
            return Question.objects.none()
        preserved = Case(
            *[When(pk=pk, then=pos) for pos, pk in enumerate(ids)],
            output_field=IntegerField(),
        )
        return Question.objects.filter(pk__in=ids).order_by(preserved)

    @staticmethod
    def get_due_review_ids(user, queryset, limit: int):
        """Question IDs whose latest attempt by this user was wrong, oldest first."""
        if not user or not getattr(user, 'is_authenticated', False) or not limit:
            return []
        latest_ok = UserAnswer.objects.filter(
            user=user, question_id=OuterRef('pk')
        ).order_by('-answered_at').values('is_correct')[:1]
        latest_at = UserAnswer.objects.filter(
            user=user, question_id=OuterRef('pk')
        ).order_by('-answered_at').values('answered_at')[:1]
        due = queryset.annotate(
            last_ok=Subquery(latest_ok),
            last_at=Subquery(latest_at),
        ).filter(last_ok=False).order_by('last_at')
        return list(due.values_list('id', flat=True)[:limit])

    @staticmethod
    def _fill_fresh_ids(queryset, user, exclude_ids, needed):
        if needed <= 0:
            return []
        exclude = list(exclude_ids)
        if user and getattr(user, 'is_authenticated', False):
            answered_ids = UserAnswer.objects.filter(user=user).values_list('question_id', flat=True).distinct()
            unseen = queryset.exclude(id__in=list(answered_ids)).exclude(id__in=exclude)
            ids = list(unseen.order_by('?').values_list('id', flat=True)[:needed])
            if len(ids) >= needed:
                return ids

            stale_cutoff = timezone.now() - timedelta(days=30)
            stale = queryset.annotate(
                user_last_answered=Max('user_answers__answered_at', filter=Q(user_answers__user=user))
            ).filter(user_last_answered__lt=stale_cutoff).exclude(id__in=exclude + ids)
            ids.extend(list(stale.order_by('?').values_list('id', flat=True)[:needed - len(ids)]))
            if len(ids) >= needed:
                return ids

            fallback = queryset.annotate(
                user_last_answered=Max('user_answers__answered_at', filter=Q(user_answers__user=user))
            ).exclude(id__in=exclude + ids).order_by('user_last_answered')
            ids.extend(list(fallback.values_list('id', flat=True)[:needed - len(ids)]))
            return ids

        return list(
            queryset.exclude(id__in=exclude).order_by('?').values_list('id', flat=True)[:needed]
        )

    @staticmethod
    def get_questions_for_user(user, filters: dict, limit: int = None):
        """
        Returns questions filtered by criteria, prioritizing:
        1. Due reviews (latest attempt was wrong) mixed ~1 in 3
        2. Questions never answered by the user
        3. Questions not answered in the last 30 days
        4. Fallback: least-recently-answered questions
        """
        # Base query to support tenant-aware (institute) questions
        base_query = Q(institute__isnull=True)
        if user and user.is_authenticated and hasattr(user, 'userprofile') and user.userprofile.institute:
            base_query |= Q(institute=user.userprofile.institute)

        queryset = Question.objects.filter(base_query, status='approved', is_public=True)

        # Apply content filters
        from .models import Exam, Topic
        target_exams = Exam.objects.none()
        
        exam_query = filters.get('exam_id') or filters.get('exam')
        if exam_query:
            if str(exam_query).isdigit():
                exam_obj = Exam.objects.filter(id=int(exam_query))
            else:
                clean_q = str(exam_query).replace('-', ' ').strip()
                exam_obj = Exam.objects.filter(
                    Q(slug__icontains=exam_query) | 
                    Q(name__icontains=exam_query) | 
                    Q(name__icontains=clean_q)
                )
            if exam_obj.exists():
                target_exams = QuestionEngine._resolve_similar_exams(exam_obj)
        elif user and user.is_authenticated and not filters.get('exam_ids') and hasattr(user, 'userprofile'):
            user_prefs = user.userprofile.preferred_exams.all()
            if user_prefs.exists():
                target_exams = QuestionEngine._resolve_similar_exams(user_prefs)
                
        if target_exams.exists():
            queryset = queryset.filter(exams__in=target_exams)
            
            # Filter strictly by syllabus topics if configured in syllabus_db
            from .syllabus_db import resolve_exam_slug, SYLLABUS_DATABASE
            allowed_topics = set()
            for exam in target_exams:
                slug_key = resolve_exam_slug(exam.slug)
                if slug_key and slug_key in SYLLABUS_DATABASE:
                    for item in SYLLABUS_DATABASE[slug_key]['syllabus']:
                        allowed_topics.add(item['topic'].lower())
            
            if allowed_topics:
                q_topic_filter = Q()
                for topic_name in allowed_topics:
                    q_topic_filter |= Q(topic__name__icontains=topic_name) | Q(sub_topic__icontains=topic_name)
                filtered_qs = queryset.filter(q_topic_filter)
                if filtered_qs.exists():
                    queryset = filtered_qs
                
            queryset = queryset.distinct()

        # Handle explicit topic query (topic_id, topic_name, topic, sub_topic)
        topic_query = filters.get('topic_id') or filters.get('topic') or filters.get('topic_name')
        if topic_query:
            if str(topic_query).isdigit():
                t_qs = queryset.filter(topic_id=int(topic_query))
            else:
                clean_t = str(topic_query).replace('-', ' ').strip()
                t_qs = queryset.filter(
                    Q(topic__name__icontains=topic_query) | 
                    Q(topic__name__icontains=clean_t) |
                    Q(sub_topic__icontains=topic_query) |
                    Q(sub_topic__icontains=clean_t)
                )
            if t_qs.exists():
                queryset = t_qs

        if filters.get('topic_ids'):
            queryset = queryset.filter(topic_id__in=filters['topic_ids'])
        if filters.get('difficulty'):
            queryset = queryset.filter(difficulty=filters['difficulty'])
        if filters.get('exclude_ids'):
            queryset = queryset.exclude(id__in=filters['exclude_ids'])
        if filters.get('section'):
            from .models import Topic
            from .psc_sections import assign_topic_to_exam_section, exam_blueprint, section_key, user_exam
            section = section_key(str(filters['section']))
            exam = None
            if user and getattr(user, 'is_authenticated', False):
                exam = user_exam(user)
            blueprint = exam_blueprint(exam)
            matching_ids = []
            for topic in Topic.objects.all().only('id', 'name'):
                assigned = assign_topic_to_exam_section(topic.name, blueprint['syllabus'])
                if assigned and section_key(assigned) == section:
                    matching_ids.append(topic.id)
            if matching_ids:
                queryset = queryset.filter(
                    Q(topic_id__in=matching_ids) | Q(sub_topic__icontains=filters['section'])
                )
            else:
                queryset = queryset.filter(
                    Q(topic__name__icontains=filters['section']) | Q(sub_topic__icontains=filters['section'])
                )

        # Fall back to user's preferred language if no explicit language filter is provided
        language_filter = filters.get('language')
        if not language_filter and user and user.is_authenticated and hasattr(user, 'userprofile'):
            language_filter = getattr(user.userprofile, 'preferred_language', None)
            
        if language_filter:
            queryset = queryset.filter(language=language_filter)


        if user and getattr(user, 'is_authenticated', False):
            if limit:
                review_n = max(1, limit // 3)
                review_ids = QuestionEngine.get_due_review_ids(user, queryset, review_n)
                fresh_ids = QuestionEngine._fill_fresh_ids(
                    queryset, user, review_ids, limit - len(review_ids)
                )
                return QuestionEngine._ordered_qs(
                    interleave_reviews(fresh_ids, review_ids)[:limit]
                )

            answered_ids = UserAnswer.objects.filter(
                user=user
            ).values_list('question_id', flat=True).distinct()
            unseen = queryset.exclude(id__in=answered_ids)
            if unseen.exists():
                return unseen.order_by('?')

            stale_cutoff = timezone.now() - timedelta(days=30)
            stale_questions = queryset.annotate(
                user_last_answered=Max('user_answers__answered_at', filter=Q(user_answers__user=user))
            ).filter(
                user_last_answered__lt=stale_cutoff
            )
            if stale_questions.exists():
                return stale_questions.order_by('?')

            return queryset.annotate(
                user_last_answered=Max('user_answers__answered_at', filter=Q(user_answers__user=user))
            ).order_by('user_last_answered')

        if limit:
            return queryset.order_by('?')[:limit]
        return queryset.order_by('?')

    @staticmethod
    def get_weak_area_questions(user, limit: int = 20, language: str = None):
        """Returns questions from topics where user accuracy < 50%."""
        if not user or not user.is_authenticated:
            return Question.objects.none()

        # Get weak topic IDs (total_attempted >= 5 and total_correct < total_attempted * 0.5)
        weak_topics = TopicProgress.objects.filter(
            user=user,
            total_attempted__gte=5,
            total_correct__lt=F('total_attempted') * 0.5
        ).values_list('topic_id', flat=True)

        filters = {'topic_ids': list(weak_topics)}
        if language:
            filters['language'] = language

        return QuestionEngine.get_questions_for_user(
            user,
            filters=filters,
            limit=limit
        )


    @staticmethod
    def get_daily_quiz(user, limit: int = 10, language: str = None):
        """Returns today's daily quiz questions — unique per user per day."""
        if not user or not user.is_authenticated:
            filters = {}
            if language:
                filters['language'] = language
            return QuestionEngine.get_questions_for_user(user, filters=filters, limit=limit)

        today = timezone.localdate()

        # Keep today's misses in the pool so they can be re-asked; skip only what's already correct today.
        answered_correct_today_ids = UserAnswer.objects.filter(
            user=user,
            answered_at__date=today,
            is_correct=True,
        ).values_list('question_id', flat=True)

        filters = {'exclude_ids': list(answered_correct_today_ids)}
        if language:
            filters['language'] = language

        return QuestionEngine.get_questions_for_user(
            user,
            filters=filters,
            limit=limit
        )


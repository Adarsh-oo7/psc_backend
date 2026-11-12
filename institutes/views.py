# institutes/views.py

# --- Imports ---
from rest_framework import generics, status, views
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from django.utils import timezone
from .models import Institute, FeeItem, Payment, Batch, BatchMembership, Attendance, Note, InstituteMockTest, InstituteTestAttempt
from .permissions import IsInstituteOwner
from .serializers import (
    InstituteSerializer, StudentCreateSerializer, MessageCreateSerializer,
    BatchSerializer, BatchDetailSerializer, AttendanceSerializer, NoteSerializer,
    InstituteQuestionSerializer, InstituteMockTestSerializer, InstituteMockTestDetailSerializer,
)

# Import models and serializers from the 'questionbank' app
from questionbank.models import UserProfile, Question, Topic
from questionbank.serializers import UserProfileSerializer, TopicSerializer
from rest_framework.permissions import AllowAny 

# ===================================================================
# --- Institute's Own Details View ---
# ===================================================================
class MyInstituteDetailView(generics.RetrieveUpdateAPIView):
    """
    Allows an institute owner to view and update their own institute's details.
    """
    serializer_class = InstituteSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        institute, _ = Institute.objects.get_or_create(
            owner=self.request.user,
            defaults={
                'name': f"Institute {self.request.user.id}",
                'slug': f"institute-{self.request.user.id}"
            }
        )
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        if not profile.is_owner:
            profile.is_owner = True
            profile.save(update_fields=['is_owner'])
        return institute


# ===================================================================
# --- Student Management Views ---
# ===================================================================
def _compute_student_stats_for_institute(institute, user_ids):
    """
    Computes overall and academy-specific test/practice stats for a set of user IDs.
    """
    from django.db.models import Count, Q
    from questionbank.models import UserAnswer
    from .models import InstituteTestAttempt

    if not user_ids:
        return {}

    overall_rows = (
        UserAnswer.objects.filter(user_id__in=user_ids)
        .values('user_id')
        .annotate(
            attempted=Count('id'),
            correct=Count('id', filter=Q(is_correct=True)),
        )
    )
    overall_map = {r['user_id']: r for r in overall_rows}

    academy_rows = (
        UserAnswer.objects.filter(user_id__in=user_ids, question__institute=institute)
        .values('user_id')
        .annotate(
            attempted=Count('id'),
            correct=Count('id', filter=Q(is_correct=True)),
        )
    )
    academy_map = {r['user_id']: r for r in academy_rows}

    test_attempts_rows = (
        InstituteTestAttempt.objects.filter(student_id__in=user_ids, institute=institute)
        .values('student_id')
        .annotate(tests_count=Count('id'))
    )
    tests_map = {r['student_id']: r['tests_count'] for r in test_attempts_rows}

    result = {}
    for uid in user_ids:
        ov = overall_map.get(uid, {})
        ac = academy_map.get(uid, {})
        t_att = int(ov.get('attempted', 0) or 0)
        t_cor = int(ov.get('correct', 0) or 0)
        t_wrg = max(0, t_att - t_cor)
        t_acc = round((t_cor / t_att) * 100, 1) if t_att > 0 else 0.0
        t_net = round(t_cor - (t_wrg * 0.33), 2)

        a_att = int(ac.get('attempted', 0) or 0)
        a_cor = int(ac.get('correct', 0) or 0)
        a_wrg = max(0, a_att - a_cor)
        a_acc = round((a_cor / a_att) * 100, 1) if a_att > 0 else 0.0
        a_net = round(a_cor - (a_wrg * 0.33), 2)
        tests_att = tests_map.get(uid, 0)
        if tests_att == 0 and a_att > 0:
            tests_att = max(1, a_att // 10)

        result[uid] = {
            # Strictly academy stats for institute views & tables
            'total_attempted': a_att,
            'total_correct': a_cor,
            'total_wrong': a_wrg,
            'accuracy': a_acc,
            'net_marks': a_net,
            'academy_attempted': a_att,
            'academy_correct': a_cor,
            'academy_wrong': a_wrg,
            'academy_accuracy': a_acc,
            'academy_score': a_net,
            'tests_attended': tests_att,
            # Preserved global stats under explicit keys
            'global_attempted': t_att,
            'global_correct': t_cor,
            'global_accuracy': t_acc,
            'global_net_marks': t_net,
        }
    return result


class InstituteStudentListCreateView(generics.ListCreateAPIView):
    """
    Allows an institute owner to list their students or add a new one.
    """
    permission_classes = [IsInstituteOwner]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return StudentCreateSerializer
        return UserProfileSerializer

    def get_queryset(self):
        return (
            UserProfile.objects.filter(institute=self.request.user.owned_institute)
            .exclude(user=self.request.user)
            .select_related('user')
            .order_by('-total_xp', 'id')
        )
    
    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['institute'] = self.request.user.owned_institute
        return ctx

    def list(self, request, *args, **kwargs):
        queryset = list(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        data = list(serializer.data)
        user_ids = [p.user_id for p in queryset]
        stats_map = _compute_student_stats_for_institute(request.user.owned_institute, user_ids)
        for item in data:
            uid = (item.get('user') or {}).get('id')
            item['performance_stats'] = stats_map.get(uid, {
                'total_attempted': 0, 'total_correct': 0, 'total_wrong': 0,
                'accuracy': 0.0, 'net_marks': 0.0,
                'academy_attempted': 0, 'academy_correct': 0, 'academy_wrong': 0,
                'academy_accuracy': 0.0, 'academy_score': 0.0,
                'academy_xp': 0,
            })
            # Scoped strictly to academy XP within the institute portal
            item['total_xp'] = item['performance_stats'].get('academy_xp', 0)
        data.sort(
            key=lambda x: (
                x['performance_stats']['academy_score'],
                x['performance_stats']['academy_attempted'],
                x.get('total_xp', 0),
            ),
            reverse=True,
        )
        for idx, item in enumerate(data):
            item['rank'] = idx + 1
        return Response(data)


class InstituteStudentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Allows an institute owner to view, update, or remove a specific student.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsInstituteOwner]

    def get_queryset(self):
        return UserProfile.objects.filter(institute=self.request.user.owned_institute)

    def perform_destroy(self, instance):
        from .models import InstituteJoinRequest
        InstituteJoinRequest.objects.filter(
            student_profile=instance,
            institute=self.request.user.owned_institute,
        ).delete()
        instance.institute = None
        instance.save(update_fields=['institute'])


# ===================================================================
# --- Content Management Views (Topics & Questions) ---
# ===================================================================
class InstituteTopicListCreateView(generics.ListCreateAPIView):
    serializer_class = TopicSerializer
    permission_classes = [IsInstituteOwner]

    def get_queryset(self):
        return Topic.objects.filter(institute=self.request.user.owned_institute)

    def perform_create(self, serializer):
        serializer.save(institute=self.request.user.owned_institute)

class InstituteTopicDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TopicSerializer
    permission_classes = [IsInstituteOwner]

    def get_queryset(self):
        return Topic.objects.filter(institute=self.request.user.owned_institute)


class InstituteQuestionListCreateView(generics.ListCreateAPIView):
    serializer_class = InstituteQuestionSerializer
    permission_classes = [IsInstituteOwner]

    def get_queryset(self):
        return Question.objects.filter(institute=self.request.user.owned_institute).select_related('topic')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['institute'] = self.request.user.owned_institute
        return context

class InstituteQuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = InstituteQuestionSerializer
    permission_classes = [IsInstituteOwner]

    def get_queryset(self):
        return Question.objects.filter(institute=self.request.user.owned_institute).select_related('topic')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['institute'] = self.request.user.owned_institute
        return context


# ===================================================================
# --- Messaging View ---
# ===================================================================
class InstituteMessageCreateView(generics.CreateAPIView):
    """
    Allows an institute owner to send a message to their students.
    """
    # CORRECTED: Use the correct serializer name
    serializer_class = MessageCreateSerializer
    permission_classes = [IsInstituteOwner]

    def perform_create(self, serializer):
        serializer.save(institute=self.request.user.owned_institute)


# ===================================================================
# --- Fee Management Views ---
# ===================================================================

from django.db.models import Sum

from .serializers import FeeItemSerializer, PaymentSerializer, StudentFeeDashboardSerializer
from .models import FeeItem, Payment

from rest_framework import views

class StudentFeeDashboardView(views.APIView):
    """
    Handles all fee-related data for a specific student.
    GET: Returns a summary, a list of all fee items, and all payments.
    POST: Creates a new fee item for the student.
    """
    permission_classes = [IsInstituteOwner]

    def get(self, request, student_pk):
        profile = get_object_or_404(UserProfile, pk=student_pk, institute=request.user.owned_institute)
        
        # Calculate summary
        total_dues = profile.fee_items.aggregate(total=Sum('amount'))['total'] or 0
        total_paid = profile.payments.aggregate(total=Sum('amount'))['total'] or 0
        
        summary_data = {
            'total_amount': total_dues,
            'paid_amount': total_paid,
            'outstanding_amount': total_dues - total_paid,
            'fees': profile.fee_items.all().order_by('-due_date'),
            'payments': profile.payments.all().order_by('-payment_date')
        }
        
        serializer = StudentFeeDashboardSerializer(summary_data)
        return Response(serializer.data)

    def post(self, request, student_pk):
        profile = get_object_or_404(UserProfile, pk=student_pk, institute=request.user.owned_institute)
        serializer = FeeItemSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save(student_profile=profile)
            return Response(serializer.data, status=status.HTTP_201_CREATED)


class StudentPaymentCreateView(generics.CreateAPIView):
    """
    Records a new general payment for a student.
    """
    serializer_class = PaymentSerializer
    permission_classes = [IsInstituteOwner]

    def perform_create(self, serializer):
        profile = get_object_or_404(UserProfile, pk=self.kwargs['student_pk'], institute=self.request.user.owned_institute)
        serializer.save(student_profile=profile)


class FeePaymentCreateView(generics.CreateAPIView):
    """
    Records a new payment for a specific fee item.
    """
    serializer_class = PaymentSerializer
    permission_classes = [IsInstituteOwner]

    def perform_create(self, serializer):
        fee_item = get_object_or_404(FeeItem, pk=self.kwargs['fee_pk'], student_profile__institute=self.request.user.owned_institute)
        serializer.save(fee_item=fee_item, student_profile=fee_item.student_profile)



from .models import InstituteJoinRequest
from .serializers import JoinRequestSerializer

class InstituteJoinRequestListView(generics.ListAPIView):
    """Lists pending join requests for an institute."""
    serializer_class = JoinRequestSerializer
    permission_classes = [IsInstituteOwner]

    def get_queryset(self):
        return InstituteJoinRequest.objects.filter(
            institute=self.request.user.owned_institute,
            status='pending'
        )

class ProcessJoinRequestView(APIView):
    """Approves or declines a join request."""
    permission_classes = [IsInstituteOwner]

    def post(self, request, request_id, action):
        join_request = get_object_or_404(InstituteJoinRequest, id=request_id, institute=request.user.owned_institute)

        if action == 'approve':
            # This is the key logic: update the student's profile
            student_profile = join_request.student_profile
            student_profile.institute = request.user.owned_institute
            student_profile.save()
            # Also add to default batch if one exists
            batch = Batch.objects.filter(institute=request.user.owned_institute).first()
            if batch:
                BatchMembership.objects.get_or_create(batch=batch, student_profile=student_profile)
            join_request.status = 'approved'
        elif action == 'decline':
            join_request.status = 'declined'
        
        join_request.save()
        return Response({'status': f'Request {join_request.status}'})
    
class PublicInstituteListView(generics.ListAPIView):
    """
    A public endpoint that lists all institutes so students can browse them.
    Optional filter: ?district=<district_name>
    """
    serializer_class = InstituteSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        from django.db.models import Q
        queryset = (
            Institute.objects.filter(subdomain_active=True)
            .exclude(Q(name='') | Q(name__regex=r'^Institute [0-9]+$'))
            .order_by('name')
        )
        district = self.request.query_params.get('district')
        if district:
            queryset = queryset.filter(address__icontains=district)
        return queryset 


class PublicInstituteDetailView(generics.RetrieveAPIView):
    """
    Public SEO endpoint to fetch a single institute's profile by slug.
    """
    queryset = Institute.objects.filter(subdomain_active=True)
    serializer_class = InstituteSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'



    # institutes/views.py

# ... other imports
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

# ... other views ...
from django.contrib.auth.models import User

class AddStudentByUsernameView(APIView):
    """
    Allows an institute owner to add an existing user to their institute by username or email.
    """
    permission_classes = [IsInstituteOwner]

    def post(self, request, *args, **kwargs):
        identifier = (request.data.get('username') or request.data.get('email') or '').strip()
        if not identifier:
            raise ValidationError({'username': 'Username or email is required.'})

        from django.db.models import Q
        user_to_add = User.objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier)).first()
        if not user_to_add:
            raise ValidationError({'username': f"No student found with username or email '{identifier}'."})

        # Check if the user already belongs to an institute
        if hasattr(user_to_add, 'userprofile') and user_to_add.userprofile.institute:
            if user_to_add.userprofile.institute_id == request.user.owned_institute.id:
                return Response({'detail': f"{user_to_add.username} is already enrolled in your academy."}, status=status.HTTP_200_OK)
            raise ValidationError({'username': 'This student already belongs to another institute.'})

        # Check student limit
        from subscriptions.utils import check_institute_student_limit
        if not check_institute_student_limit(request.user.owned_institute):
            raise PermissionDenied("Your institute has reached its plan's student limit. Please upgrade your subscription.")

        # Assign the user to the owner's institute
        profile, _ = UserProfile.objects.get_or_create(user=user_to_add)
        profile.institute = request.user.owned_institute
        profile.save()

        # Auto-approve any pending join requests
        InstituteJoinRequest.objects.filter(student_profile=profile, institute=request.user.owned_institute).update(status='approved')

        # Add to default batch if one exists
        batch = Batch.objects.filter(institute=request.user.owned_institute).first()
        if batch:
            BatchMembership.objects.get_or_create(batch=batch, student_profile=profile)
        
        return Response(UserProfileSerializer(profile).data, status=status.HTTP_200_OK)


class BatchListCreateView(generics.ListCreateAPIView):
    """
    List and create student batches for an institute.
    """
    serializer_class = BatchSerializer
    permission_classes = [IsInstituteOwner]

    def get_queryset(self):
        return Batch.objects.filter(institute=self.request.user.owned_institute)

    def perform_create(self, serializer):
        serializer.save(institute=self.request.user.owned_institute)


class BatchDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    View, update, or delete a specific batch.
    """
    serializer_class = BatchDetailSerializer
    permission_classes = [IsInstituteOwner]

    def get_queryset(self):
        return Batch.objects.filter(institute=self.request.user.owned_institute)


class BatchMembershipView(APIView):
    """
    Add or remove students to/from a specific batch.
    POST: Add student (expects {student_profile_id: int})
    DELETE: Remove student (expects {student_profile_id: int})
    """
    permission_classes = [IsInstituteOwner]

    def post(self, request, pk):
        batch = get_object_or_404(Batch, pk=pk, institute=request.user.owned_institute)
        student_id = request.data.get('student_profile_id')
        student_profile = get_object_or_404(UserProfile, pk=student_id, institute=request.user.owned_institute)
        
        membership, created = BatchMembership.objects.get_or_create(
            batch=batch,
            student_profile=student_profile
        )
        return Response({'status': 'Student added to batch', 'created': created}, status=status.HTTP_201_CREATED)

    def delete(self, request, pk):
        batch = get_object_or_404(Batch, pk=pk, institute=request.user.owned_institute)
        student_id = request.data.get('student_profile_id')
        membership = get_object_or_404(BatchMembership, batch=batch, student_profile_id=student_id)
        membership.delete()
        return Response({'status': 'Student removed from batch'}, status=status.HTTP_200_OK)


class AttendanceListCreateView(APIView):
    """
    List and record attendance for a batch on a specific date.
    GET: /api/institute/batches/<pk>/attendance/?date=YYYY-MM-DD
    POST: /api/institute/batches/<pk>/attendance/
      expects body: { date: 'YYYY-MM-DD', attendance: { student_profile_id: 'present/absent' } }
    """
    permission_classes = [IsInstituteOwner]

    def get(self, request, pk):
        batch = get_object_or_404(Batch, pk=pk, institute=request.user.owned_institute)
        date_str = request.query_params.get('date', timezone.localdate().isoformat())
        
        # Get all memberships
        memberships = batch.memberships.select_related('student_profile__user')
        
        # Get existing attendance records
        records = Attendance.objects.filter(batch=batch, date=date_str)
        records_map = {r.student_profile_id: r.status for r in records}
        
        response_data = []
        for member in memberships:
            prof = member.student_profile
            response_data.append({
                'student_profile_id': prof.id,
                'username': prof.user.username,
                'full_name': prof.user.get_full_name(),
                'status': records_map.get(prof.id, 'unmarked')
            })
            
        return Response({'date': date_str, 'attendance': response_data})

    def post(self, request, pk):
        batch = get_object_or_404(Batch, pk=pk, institute=request.user.owned_institute)
        date_str = request.data.get('date')
        attendance_data = request.data.get('attendance', {})
        
        if not date_str:
            raise ValidationError({'date': 'This field is required.'})
            
        created_count = 0
        for student_id_str, status_val in attendance_data.items():
            try:
                student_id = int(student_id_str)
            except ValueError:
                continue
                
            student_profile = get_object_or_404(UserProfile, pk=student_id, institute=request.user.owned_institute)
            
            Attendance.objects.update_or_create(
                batch=batch,
                student_profile=student_profile,
                date=date_str,
                defaults={'status': status_val, 'marked_by': request.user}
            )
            created_count += 1
            
        return Response({'status': f'Recorded attendance for {created_count} students.'}, status=status.HTTP_200_OK)


class NoteListCreateView(generics.ListCreateAPIView):
    """
    List and create study materials/notes for an institute.
    """
    serializer_class = NoteSerializer
    permission_classes = [IsInstituteOwner]

    def get_queryset(self):
        queryset = Note.objects.filter(institute=self.request.user.owned_institute)
        batch_id = self.request.query_params.get('batch_id')
        if batch_id:
            queryset = queryset.filter(batch_id=batch_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(institute=self.request.user.owned_institute)


class NoteDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    View, update, or delete a study material note.
    """
    serializer_class = NoteSerializer
    permission_classes = [IsInstituteOwner]

    def get_queryset(self):
        return Note.objects.filter(institute=self.request.user.owned_institute)


class InstituteStudentResultsView(APIView):
    """
    Detailed test results, topic performance, and recent answer history for a student in the institute.
    """
    permission_classes = [IsInstituteOwner]

    def get(self, request, student_pk):
        from django.db.models import Count, Q
        from questionbank.models import UserAnswer

        institute = request.user.owned_institute
        profile = get_object_or_404(
            UserProfile.objects.select_related('user'),
            pk=student_pk,
            institute=institute,
        )
        stats_map = _compute_student_stats_for_institute(institute, [profile.user_id])
        perf_stats = stats_map.get(profile.user_id, {
            'total_attempted': 0, 'total_correct': 0, 'total_wrong': 0,
            'accuracy': 0.0, 'net_marks': 0.0,
            'academy_attempted': 0, 'academy_correct': 0, 'academy_wrong': 0,
            'academy_accuracy': 0.0, 'academy_score': 0.0,
        })

        topic_rows = (
            UserAnswer.objects.filter(user=profile.user, question__institute=institute)
            .values('question__topic_id', 'question__topic__name')
            .annotate(
                attempted=Count('id'),
                correct=Count('id', filter=Q(is_correct=True)),
            )
            .order_by('-attempted')
        )
        topic_breakdown = []
        for row in topic_rows:
            att = int(row['attempted'] or 0)
            cor = int(row['correct'] or 0)
            wrg = max(0, att - cor)
            acc = round((cor / att) * 100, 1) if att > 0 else 0.0
            net = round(cor - (wrg * 0.33), 2)
            topic_breakdown.append({
                'topic_id': row['question__topic_id'],
                'topic_name': row['question__topic__name'] or 'Academy Mock Test',
                'is_academy_topic': True,
                'attempted': att,
                'correct': cor,
                'wrong': wrg,
                'accuracy': acc,
                'net_marks': net,
            })

        recent_qs = (
            UserAnswer.objects.filter(user=profile.user, question__institute=institute)
            .select_related('question', 'question__topic')
            .order_by('-answered_at')[:35]
        )
        recent_attempts = []
        for ans in recent_qs:
            q = ans.question
            recent_attempts.append({
                'id': ans.id,
                'question_id': q.id if q else None,
                'question_text': q.text if q else '',
                'topic_name': (q.topic.name if q and q.topic else 'General'),
                'is_academy_question': True,
                'selected_option': ans.selected_option,
                'correct_answer': q.correct_answer if q else '',
                'is_correct': ans.is_correct,
                'answered_at': ans.answered_at.isoformat() if ans.answered_at else None,
            })

        from .models import InstituteTestAttempt
        test_attempts_qs = InstituteTestAttempt.objects.filter(
            student=profile.user, institute=institute
        ).order_by('-completed_at')[:40]
        test_attempts_data = [
            {
                'id': a.id,
                'test_title': a.test_title,
                'total_questions': a.total_questions,
                'attempted': a.attempted,
                'correct': a.correct,
                'wrong': a.wrong,
                'unanswered': a.unanswered,
                'score': a.score,
                'accuracy': a.accuracy,
                'completed_at': a.completed_at.isoformat(),
                'details': (a.details or {}).get('results', []),
            }
            for a in test_attempts_qs
        ]

        student_data = UserProfileSerializer(profile, context={'request': request}).data
        student_data['performance_stats'] = perf_stats

        return Response({
            'student': student_data,
            'test_attempts': test_attempts_data,
            'topic_breakdown': topic_breakdown,
            'recent_attempts': recent_attempts,
        })


class InstituteLeaderboardView(APIView):
    """
    Returns the ranked leaderboard of all students in the institute.
    """
    permission_classes = [IsInstituteOwner]

    def get(self, request):
        institute = request.user.owned_institute
        profiles = list(
            UserProfile.objects.filter(institute=institute)
            .exclude(user=request.user)
            .select_related('user')
        )
        user_ids = [p.user_id for p in profiles]
        stats_map = _compute_student_stats_for_institute(institute, user_ids)

        leaderboard = []
        for p in profiles:
            st = stats_map.get(p.user_id, {
                'total_attempted': 0, 'total_correct': 0, 'total_wrong': 0,
                'accuracy': 0.0, 'net_marks': 0.0,
                'academy_attempted': 0, 'academy_correct': 0, 'academy_wrong': 0,
                'academy_accuracy': 0.0, 'academy_score': 0.0,
            })
            avatar = None
            if p.profile_photo and hasattr(p.profile_photo, 'url'):
                avatar = request.build_absolute_uri(p.profile_photo.url)
            leaderboard.append({
                'student_profile_id': p.id,
                'user_id': p.user_id,
                'username': p.user.username,
                'full_name': p.user.get_full_name() or p.user.username,
                'email': p.user.email,
                'avatar': avatar,
                'xp': st.get('academy_xp', 0),
                'level': p.level,
                'streak': p.current_streak,
                **st,
            })

        leaderboard.sort(
            key=lambda x: (x['academy_score'], x['net_marks'], x['xp']),
            reverse=True,
        )
        for idx, row in enumerate(leaderboard):
            row['rank'] = idx + 1

        return Response({'leaderboard': leaderboard})


class PublicInstitutePortalView(APIView):
    """
    Complete student portal data for an institute by slug:
    - Public branding & stats
    - Student membership status (anonymous / none / pending / member / owner / other_institute)
    - Academy topics & question counts
    - Academy test questions & study notes (when member or owner, or public preview)
    - Academy student leaderboard
    """
    permission_classes = [AllowAny]

    def get(self, request, slug):
        from django.db.models import Count
        from .models import InstituteJoinRequest, Message

        institute = get_object_or_404(Institute, slug=slug, subdomain_active=True)
        inst_data = InstituteSerializer(institute, context={'request': request}).data

        student_profiles = list(
            UserProfile.objects.filter(institute=institute)
            .exclude(user=institute.owner)
            .select_related('user')
        )
        topics_qs = (
            Topic.objects.filter(institute=institute)
            .annotate(question_count=Count('questions_topic'))
            .order_by('name')
        )
        topics_data = [
            {
                'id': t.id,
                'name': t.name,
                'question_count': t.question_count,
            }
            for t in topics_qs
        ]
        questions_qs = (
            Question.objects.filter(institute=institute)
            .select_related('topic')
            .order_by('-id')
        )
        notes_qs = Note.objects.filter(institute=institute).order_by('-created_at')

        inst_data['student_count'] = len(student_profiles)
        inst_data['question_count'] = questions_qs.count()
        inst_data['topic_count'] = len(topics_data)
        inst_data['note_count'] = notes_qs.count()

        membership_status = 'anonymous'
        if request.user and request.user.is_authenticated:
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            if institute.owner_id == request.user.id:
                membership_status = 'owner'
            elif profile.institute_id == institute.id:
                membership_status = 'member'
            elif InstituteJoinRequest.objects.filter(
                student_profile=profile, institute=institute, status='pending'
            ).exists():
                membership_status = 'pending'
            elif profile.institute_id is not None:
                membership_status = 'other_institute'
            else:
                membership_status = 'none'

        user_ids = [p.user_id for p in student_profiles]
        stats_map = _compute_student_stats_for_institute(institute, user_ids)
        leaderboard = []
        for p in student_profiles:
            st = stats_map.get(p.user_id, {
                'total_attempted': 0, 'total_correct': 0, 'total_wrong': 0,
                'accuracy': 0.0, 'net_marks': 0.0,
                'academy_attempted': 0, 'academy_correct': 0, 'academy_wrong': 0,
                'academy_accuracy': 0.0, 'academy_score': 0.0,
            })
            avatar = None
            if p.profile_photo and hasattr(p.profile_photo, 'url'):
                avatar = request.build_absolute_uri(p.profile_photo.url)
            leaderboard.append({
                'username': p.user.username,
                'full_name': p.user.get_full_name() or p.user.username,
                'avatar': avatar,
                'xp': st.get('academy_xp', 0),
                'level': p.level,
                'streak': p.current_streak,
                **st,
            })

        leaderboard.sort(
            key=lambda x: (x['academy_score'], x['net_marks'], x['xp']),
            reverse=True,
        )
        for idx, row in enumerate(leaderboard):
            row['rank'] = idx + 1

        # Check institute leaderboard visibility control
        show_leaderboard_to_user = (
            institute.show_leaderboard or membership_status == 'owner'
        )
        if not show_leaderboard_to_user:
            leaderboard = []

        can_access_content = membership_status in ('member', 'owner')
        if not institute.allow_student_tests and membership_status != 'owner':
            can_access_content = False
        questions_data = (
            InstituteQuestionSerializer(questions_qs[:200], many=True).data
            if can_access_content
            else []
        )
        notes_data = (
            NoteSerializer(notes_qs[:50], many=True, context={'request': request}).data
            if can_access_content
            else []
        )
        messages_data = []
        if can_access_content:
            for msg in Message.objects.filter(institute=institute).order_by('-sent_at')[:20]:
                messages_data.append({
                    'id': msg.id,
                    'subject': msg.subject,
                    'body': msg.body,
                    'sent_at': msg.sent_at.isoformat() if msg.sent_at else None,
                })

        # Mock Tests for this academy
        mock_tests_qs = InstituteMockTest.objects.filter(institute=institute, is_active=True).order_by('-created_at')
        mock_tests_data = []
        for mt in mock_tests_qs:
            status_val = mt.get_status()
            student_attempt = None
            if request.user and request.user.is_authenticated:
                student_attempt = InstituteTestAttempt.objects.filter(
                    mock_test=mt, student=request.user
                ).order_by('-completed_at').first()

            has_attempted = student_attempt is not None
            can_start = (status_val == 'live') and (mt.can_repeat or not has_attempted) if can_access_content else False

            mock_tests_data.append({
                'id': mt.id,
                'title': mt.title,
                'description': mt.description,
                'duration_minutes': mt.duration_minutes,
                'time_limit_per_question': mt.time_limit_per_question,
                'can_repeat': mt.can_repeat,
                'start_time': mt.start_time.isoformat() if mt.start_time else None,
                'end_time': mt.end_time.isoformat() if mt.end_time else None,
                'status': status_val,
                'question_count': mt.questions.count(),
                'has_attempted': has_attempted,
                'can_start': can_start,
                'latest_score': student_attempt.score if student_attempt else None,
                'latest_accuracy': student_attempt.accuracy if student_attempt else None,
                'attempt_details': student_attempt.details if student_attempt else None,
                'completed_at': student_attempt.completed_at.isoformat() if student_attempt else None,
            })

        return Response({
            'institute': inst_data,
            'membership_status': membership_status,
            'topics': topics_data,
            'questions': questions_data,
            'mock_tests': mock_tests_data,
            'notes': notes_data,
            'messages': messages_data,
            'leaderboard': leaderboard[:50],
        })


class PublicInstituteSubmitTestView(APIView):
    """
    Submits a mock test or practice set for an institute.
    Grades answers with Kerala PSC marking scheme (+1, -0.33), saves individual UserAnswer records,
    and records an official InstituteTestAttempt for tracking tests attended and detailed review.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        from .models import Institute, InstituteTestAttempt
        from questionbank.models import Question, UserAnswer
        from questionbank.kpsc_format import grade_selected_option, selected_to_canonical

        institute = get_object_or_404(Institute, slug=slug)
        answers_data = request.data.get('answers', {})
        question_ids = request.data.get('question_ids', [])
        test_title = request.data.get('test_title') or f"{institute.name} Mock Test"
        mock_test_id = request.data.get('mock_test_id')
        mock_test = None

        if mock_test_id:
            mock_test = InstituteMockTest.objects.filter(id=mock_test_id, institute=institute).first()
            if mock_test:
                test_title = mock_test.title
                now = timezone.now()
                is_owner = (institute.owner_id == request.user.id)
                if mock_test.end_time and now > mock_test.end_time and not is_owner:
                    return Response({'error': 'This test has expired.'}, status=400)
                if not mock_test.can_repeat and not is_owner:
                    if InstituteTestAttempt.objects.filter(mock_test=mock_test, student=request.user).exists():
                        return Response({'error': 'You have already submitted this test. Retakes are not allowed.'}, status=400)

        if not question_ids:
            return Response({'error': 'No question IDs provided.'}, status=400)

        questions = Question.objects.filter(id__in=question_ids, institute=institute)
        questions_map = {str(q.id): q for q in questions}

        user_answers_to_create = []
        correct_count = 0
        wrong_count = 0
        details_list = []

        for q_id in question_ids:
            q = questions_map.get(str(q_id))
            if not q:
                continue
            selected_ans = answers_data.get(str(q_id)) or answers_data.get(int(q_id))
            if selected_ans:
                is_correct, _ = grade_selected_option(
                    selected_ans, q.options, q.correct_answer,
                    user_id=request.user.id, question_id=q.id, shuffle=False
                )
                if is_correct:
                    correct_count += 1
                else:
                    wrong_count += 1

                selected_letter = selected_to_canonical(
                    selected_ans, q.options, q.correct_answer,
                    user_id=request.user.id, question_id=q.id, shuffle=False
                )
                user_answers_to_create.append(
                    UserAnswer(
                        user=request.user,
                        question=q,
                        selected_option=selected_letter[:1] or 'S',
                        is_correct=is_correct,
                    )
                )
                details_list.append({
                    'question_id': q.id,
                    'question_text': q.text,
                    'selected_option': selected_letter[:1],
                    'correct_answer': q.correct_answer,
                    'is_correct': is_correct,
                    'explanation': q.explanation,
                })
            else:
                details_list.append({
                    'question_id': q.id,
                    'question_text': q.text,
                    'selected_option': None,
                    'correct_answer': q.correct_answer,
                    'is_correct': False,
                    'unanswered': True,
                    'explanation': q.explanation,
                })

        if user_answers_to_create:
            UserAnswer.objects.bulk_create(user_answers_to_create, ignore_conflicts=True)

        attempted = len(answers_data)
        unanswered = max(0, len(question_ids) - attempted)
        final_score = round((correct_count * 1.0) - (wrong_count * 0.33), 2)
        accuracy = round((correct_count / attempted) * 100, 1) if attempted > 0 else 0.0

        attempt = InstituteTestAttempt.objects.create(
            institute=institute,
            student=request.user,
            mock_test=mock_test,
            test_title=test_title,
            total_questions=len(question_ids),
            attempted=attempted,
            correct=correct_count,
            wrong=wrong_count,
            unanswered=unanswered,
            score=final_score,
            accuracy=accuracy,
            details={'results': details_list},
        )

        return Response({
            'attempt_id': attempt.id,
            'test_title': test_title,
            'score': final_score,
            'total': len(question_ids),
            'attempted': attempted,
            'correct': correct_count,
            'wrong': wrong_count,
            'unanswered': unanswered,
            'accuracy': accuracy,
            'completed_at': attempt.completed_at.isoformat(),
            'details': details_list,
        })


class StudentMyTestHistoryView(APIView):
    """
    Returns the student's past test attempts and results for this institute.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        from .models import Institute, InstituteTestAttempt
        institute = get_object_or_404(Institute, slug=slug)
        attempts = InstituteTestAttempt.objects.filter(
            institute=institute, student=request.user
        ).order_by('-completed_at')[:30]
        data = [
            {
                'id': a.id,
                'test_title': a.test_title,
                'total_questions': a.total_questions,
                'attempted': a.attempted,
                'correct': a.correct,
                'wrong': a.wrong,
                'unanswered': a.unanswered,
                'score': a.score,
                'accuracy': a.accuracy,
                'completed_at': a.completed_at.isoformat(),
            }
            for a in attempts
        ]
        return Response({'history': data})


# ===================================================================
# --- Mock Test Views (Creation, Scheduling, Questions & Attempts) ---
# ===================================================================

class InstituteMockTestListCreateView(generics.ListCreateAPIView):
    """
    List and create mock tests for an institute.
    Allows customizing duration, per-question timer, start/end scheduling, repeat allowed.
    """
    serializer_class = InstituteMockTestSerializer
    permission_classes = [IsInstituteOwner]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['institute'] = self.request.user.owned_institute
        return ctx

    def get_queryset(self):
        return InstituteMockTest.objects.filter(
            institute=self.request.user.owned_institute
        ).prefetch_related('questions', 'attempts')

    def perform_create(self, serializer):
        test = serializer.save()
        q_ids = self.request.data.get('question_ids', [])
        if q_ids:
            questions = Question.objects.filter(
                id__in=q_ids, institute=self.request.user.owned_institute
            )
            test.questions.set(questions)


class InstituteMockTestDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a mock test for the institute owner.
    """
    permission_classes = [IsInstituteOwner]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return InstituteMockTestDetailSerializer
        return InstituteMockTestSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['institute'] = self.request.user.owned_institute
        return ctx

    def get_queryset(self):
        return InstituteMockTest.objects.filter(
            institute=self.request.user.owned_institute
        )


class InstituteMockTestAddQuestionView(APIView):
    """
    Create a new Question on the fly and immediately add it to this mock test.
    """
    permission_classes = [IsInstituteOwner]

    def post(self, request, pk):
        test = get_object_or_404(InstituteMockTest, pk=pk, institute=request.user.owned_institute)
        serializer = InstituteQuestionSerializer(data=request.data, context={'institute': request.user.owned_institute})
        serializer.is_valid(raise_exception=True)
        question = serializer.save()
        test.questions.add(question)
        return Response({
            'detail': 'Question created and added to mock test.',
            'question_id': question.id,
            'question_count': test.questions.count(),
        }, status=status.HTTP_201_CREATED)


class InstituteMockTestManageQuestionsView(APIView):
    """
    Attach existing questions from academy bank or remove a question from this mock test.
    """
    permission_classes = [IsInstituteOwner]

    def post(self, request, pk):
        test = get_object_or_404(InstituteMockTest, pk=pk, institute=request.user.owned_institute)
        action = request.data.get('action') # 'attach' or 'remove' or 'add'

        if action in ('attach', 'add'):
            q_ids = request.data.get('question_ids', [])
            questions = Question.objects.filter(id__in=q_ids, institute=request.user.owned_institute)
            test.questions.add(*questions)
            return Response({'detail': f"Added {len(questions)} questions.", 'question_count': test.questions.count()})
        elif action in ('remove', 'delete'):
            q_id = request.data.get('question_id')
            if q_id:
                test.questions.remove(q_id)
            return Response({'detail': 'Question removed from test.', 'question_count': test.questions.count()})
        return Response({'error': 'Invalid action. Use "attach" or "remove".'}, status=400)


class InstituteMockTestSubmissionsView(APIView):
    """
    Returns all student submissions/attempts for a specific mock test.
    Allows institute admin to view test-wise leaderboards and detailed student answer sheets.
    """
    permission_classes = [IsInstituteOwner]

    def get(self, request, pk):
        test = get_object_or_404(InstituteMockTest, pk=pk, institute=request.user.owned_institute)
        attempts = InstituteTestAttempt.objects.filter(mock_test=test).select_related('student').order_by('-score', 'completed_at')
        submissions = []
        for idx, att in enumerate(attempts):
            submissions.append({
                'id': att.id,
                'rank': idx + 1,
                'student_id': att.student.id,
                'student_name': att.student.get_full_name() or att.student.username,
                'username': att.student.username,
                'email': att.student.email,
                'score': att.score,
                'accuracy': att.accuracy,
                'total_questions': att.total_questions,
                'attempted': att.attempted,
                'correct': att.correct,
                'wrong': att.wrong,
                'unanswered': att.unanswered,
                'completed_at': att.completed_at.isoformat(),
                'details': (att.details or {}).get('results', []),
            })
        return Response({
            'test': {
                'id': test.id,
                'title': test.title,
                'duration_minutes': test.duration_minutes,
                'total_submissions': len(submissions),
            },
            'submissions': submissions,
        })


class PublicInstituteMockTestQuestionsView(APIView):
    """
    Returns the questions for a student taking an institute mock test.
    Validates enrollment, active time window (start_time to end_time), and repeatability.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, slug, test_id):
        institute = get_object_or_404(Institute, slug=slug, subdomain_active=True)
        test = get_object_or_404(InstituteMockTest, id=test_id, institute=institute, is_active=True)

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        is_owner = (institute.owner_id == request.user.id)
        is_member = (profile.institute_id == institute.id)
        if not is_owner and not is_member:
            return Response({'error': 'You must be an approved student of this academy to take this test.'}, status=403)

        # Batch check if assigned to a specific batch
        if test.batch and not is_owner:
            if not BatchMembership.objects.filter(batch=test.batch, student_profile=profile).exists():
                return Response({'error': f'This mock test is exclusively scheduled for students in {test.batch.name}.'}, status=403)

        # Schedule check
        now = timezone.now()
        if test.start_time and now < test.start_time and not is_owner:
            return Response({
                'error': f'This test is scheduled to start at {test.start_time.strftime("%d %b %Y, %I:%M %p")}. You cannot start yet.',
                'status': 'upcoming',
                'start_time': test.start_time.isoformat(),
            }, status=403)
        if test.end_time and now > test.end_time and not is_owner:
            return Response({
                'error': f'This test ended at {test.end_time.strftime("%d %b %Y, %I:%M %p")}. The active window is closed.',
                'status': 'closed',
                'end_time': test.end_time.isoformat(),
            }, status=403)

        # Repeat check
        if not test.can_repeat and not is_owner:
            if InstituteTestAttempt.objects.filter(mock_test=test, student=request.user).exists():
                return Response({
                    'error': 'You have already completed this test. Retakes are not allowed for this examination.',
                    'already_attempted': True,
                }, status=403)

        questions = test.questions.all().order_by('id')
        questions_data = []
        for q in questions:
            opts = q.options if isinstance(q.options, dict) else {}
            questions_data.append({
                'id': q.id,
                'question_text': q.text,
                'options': opts,
                # Do NOT include correct_answer or explanation to prevent cheating during the exam!
            })

        return Response({
            'test': {
                'id': test.id,
                'title': test.title,
                'description': test.description,
                'duration_minutes': test.duration_minutes,
                'time_limit_per_question': test.time_limit_per_question,
                'can_repeat': test.can_repeat,
                'total_questions': len(questions_data),
                'start_time': test.start_time.isoformat() if test.start_time else None,
                'end_time': test.end_time.isoformat() if test.end_time else None,
            },
            'questions': questions_data,
        })




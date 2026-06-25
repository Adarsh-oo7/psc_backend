# institutes/views.py

# --- Imports ---
from rest_framework import generics, status, views
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from django.utils import timezone
from .models import Institute, FeeItem, Payment, Batch, BatchMembership, Attendance, Note
from .permissions import IsInstituteOwner
from .serializers import (
    InstituteSerializer, StudentCreateSerializer, MessageCreateSerializer,
    BatchSerializer, BatchDetailSerializer, AttendanceSerializer, NoteSerializer
)

# Import models and serializers from the 'questionbank' app
from questionbank.models import UserProfile, Question, Topic
from questionbank.serializers import UserProfileSerializer, QuestionSerializer, TopicSerializer
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
        return institute


# ===================================================================
# --- Student Management Views ---
# ===================================================================
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
        return UserProfile.objects.filter(institute=self.request.user.owned_institute)
    
    def get_serializer_context(self):
        return {'institute': self.request.user.owned_institute}


class InstituteStudentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Allows an institute owner to view, update, or remove a specific student.
    """
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsInstituteOwner]


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
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer
    permission_classes = [IsInstituteOwner]


class InstituteQuestionListCreateView(generics.ListCreateAPIView):
    serializer_class = QuestionSerializer
    permission_classes = [IsInstituteOwner]

    def get_queryset(self):
        return Question.objects.filter(institute=self.request.user.owned_institute)

    def perform_create(self, serializer):
        serializer.save(institute=self.request.user.owned_institute)

class InstituteQuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [IsInstituteOwner]


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
            join_request.status = 'approved'
        elif action == 'decline':
            join_request.status = 'declined'
        
        join_request.save()
        return Response({'status': f'Request {join_request.status}'})
    
class PublicInstituteListView(generics.ListAPIView):
    """
    A public endpoint that lists all institutes so students can browse them.
    """
    # We use the simple InstituteSerializer, but you could create an even simpler one if needed.
    queryset = Institute.objects.all().order_by('name')
    serializer_class = InstituteSerializer
    permission_classes = [AllowAny] 


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
    Allows an institute owner to add an existing user to their institute by username.
    """
    permission_classes = [IsInstituteOwner]

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        if not username:
            raise ValidationError({'username': 'This field is required.'})

        # Find the user
        try:
            user_to_add = User.objects.get(username=username)
        except User.DoesNotExist:
            raise ValidationError({'username': 'User with this username does not exist.'})

        # Check if the user already belongs to an institute
        if hasattr(user_to_add, 'userprofile') and user_to_add.userprofile.institute:
            raise ValidationError({'username': 'This user already belongs to another institute.'})

        # Check student limit
        from subscriptions.utils import check_institute_student_limit
        if not check_institute_student_limit(request.user.owned_institute):
            raise PermissionDenied("Your institute has reached its plan's student limit. Please upgrade your subscription.")

        # If everything is okay, assign the user to the owner's institute
        profile, _ = UserProfile.objects.get_or_create(user=user_to_add)
        profile.institute = request.user.owned_institute
        profile.save()
        
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
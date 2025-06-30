# institutes/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Endpoint for the institute to manage its own profile
    path('my-institute/', views.MyInstituteDetailView.as_view(), name='my-institute-detail'),
    
    # Endpoints for managing students
    path('students/', views.InstituteStudentListCreateView.as_view(), name='institute-student-list'),
    path('students/<int:pk>/', views.InstituteStudentDetailView.as_view(), name='institute-student-detail'),
    
    # Endpoints for managing custom topics
    path('topics/', views.InstituteTopicListCreateView.as_view(), name='institute-topic-list'),
    path('topics/<int:pk>/', views.InstituteTopicDetailView.as_view(), name='institute-topic-detail'),
    
    # Endpoints for managing custom questions
    path('questions/', views.InstituteQuestionListCreateView.as_view(), name='institute-question-list'),
    path('questions/<int:pk>/', views.InstituteQuestionDetailView.as_view(), name='institute-question-detail'),
    
    # Endpoint for sending messages
    path('messages/send/', views.InstituteMessageCreateView.as_view(), name='institute-send-message'),

  #  path('students/<int:student_pk>/fees/', views.StudentFeeDetailView.as_view(), name='student-fee-detail'),
    path('fees/<int:fee_pk>/record-payment/', views.StudentPaymentCreateView.as_view(), name='student-record-payment'),


    path('join-requests/', views.InstituteJoinRequestListView.as_view(), name='institute-join-requests'),
    path('join-requests/<int:request_id>/<str:action>/', views.ProcessJoinRequestView.as_view(), name='process-join-request'),
    path('public/list/', views.PublicInstituteListView.as_view(), name='public-institute-list'),
    path('students/add-by-username/', views.AddStudentByUsernameView.as_view(), name='institute-add-student-by-username'),

    path('students/<int:student_pk>/fees/', views.StudentFeeDashboardView.as_view(), name='student-fee-dashboard'),
    
    # POST to record a new payment for a student
    path('students/<int:student_pk>/record-payment/', views.StudentPaymentCreateView.as_view(), name='student-record-payment'),

]
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# ===================================================================
# --- Models for Exam & Content Structure ---
# ===================================================================
class ExamCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "Exam Categories"
        ordering = ['order']

    def __str__(self):
        return self.name

class Exam(models.Model):
    category = models.ForeignKey('ExamCategory', on_delete=models.SET_NULL, related_name='exams', null=True, blank=True)
    name = models.CharField(max_length=100)
    year = models.IntegerField()
    duration_minutes = models.PositiveIntegerField(default=75, help_text="Exam duration in minutes")

    def __str__(self):
        return f"{self.name} ({self.year})"

class Topic(models.Model):
    name = models.CharField(max_length=100)
    institute = models.ForeignKey('institutes.Institute', on_delete=models.CASCADE, null=True, blank=True, related_name='topics')
    image = models.ImageField(upload_to='topic_images/', null=True, blank=True)

    def __str__(self):
        return self.name

class Question(models.Model):
    exam = models.ForeignKey('Exam', on_delete=models.CASCADE, related_name='questions')
    topic = models.ForeignKey('Topic', on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    options = models.JSONField()
    correct_answer = models.CharField(max_length=1)
    explanation = models.TextField(blank=True)
    difficulty = models.CharField(max_length=20, choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')], default='medium')
    institute = models.ForeignKey('institutes.Institute', on_delete=models.CASCADE, null=True, blank=True, related_name='questions')
    
    def __str__(self):
        return self.text[:50]


# ===================================================================
# --- Models for User Data & Tracking ---
# ===================================================================

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_photo = models.ImageField(upload_to='profiles/', blank=True, null=True)
    qualifications = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    place = models.CharField(max_length=100, blank=True)
    preferred_topics = models.ManyToManyField('Topic', blank=True)
    preferred_difficulty = models.CharField(max_length=20, choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')], blank=True)
    institute = models.ForeignKey('institutes.Institute', on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    
    # --- NEW: Field to store multiple preferred exams ---
    preferred_exams = models.ManyToManyField('Exam', blank=True, related_name='followers')

    def __str__(self):
        return self.user.username

class ExamSyllabus(models.Model):
    exam = models.ForeignKey('Exam', on_delete=models.CASCADE, related_name='syllabus_parts')
    topic = models.ForeignKey('Topic', on_delete=models.CASCADE)
    num_questions = models.PositiveIntegerField(default=10)

    class Meta:
        unique_together = ('exam', 'topic')

    def __str__(self):
        return f"{self.exam.name}: {self.num_questions} questions from {self.topic.name}"

class UserAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey('Question', on_delete=models.CASCADE, related_name='user_answers')
    selected_option = models.CharField(max_length=1)
    is_correct = models.BooleanField()
    answered_at = models.DateTimeField(auto_now_add=True)

class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey('Question', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class Report(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey('Question', on_delete=models.CASCADE)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
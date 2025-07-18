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

# In questionbank/models.py

class Question(models.Model):
    # The temporary 'old_exam' field is now completely removed.
    
    # Only the new ManyToManyField remains. This is the final version.
    exams = models.ManyToManyField('Exam', related_name='questions')
    
    sub_topic = models.CharField(max_length=255, blank=True, help_text="e.g., Indian Freedom Movement")
    topic = models.ForeignKey('Topic', on_delete=models.CASCADE, related_name='questions_topic')
    text = models.TextField()
    options = models.JSONField()
    correct_answer = models.CharField(max_length=1)
    explanation = models.TextField(blank=True)
    difficulty = models.CharField(
        max_length=20,
        choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')],
        default='medium'
    )
    institute = models.ForeignKey(
        'institutes.Institute', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='questions_institute'
    )
    
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
    is_content_creator = models.BooleanField(default=False, help_text="Designates this user as a trusted community content creator.")

    # --- NEW: Field to store multiple preferred exams ---
    preferred_exams = models.ManyToManyField('Exam', blank=True, related_name='followers')
    bio = models.TextField(blank=True, help_text="A short description or bio for the user's public profile.")
    
    is_content_creator = models.BooleanField(default=False, help_text="Designates this user as a trusted community content creator.")
    is_owner = models.BooleanField(default=False) # We will keep this for future institute features
    


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



from django.db import models

class Questions(models.Model):
    question_text = models.TextField(verbose_name="Question")
    option_a = models.CharField(max_length=255, verbose_name="Option A")
    option_b = models.CharField(max_length=255, verbose_name="Option B")
    option_c = models.CharField(max_length=255, blank=True, verbose_name="Option C")
    option_d = models.CharField(max_length=255, blank=True, verbose_name="Option D")
    correct_answer = models.CharField(
        max_length=1,
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')],
        verbose_name="Correct Answer"
    )
    explanation = models.TextField(blank=True, verbose_name="Explanation")

    def __str__(self):
        return self.question_text[:70]

class DailyExam(models.Model):
    date = models.DateField(unique=True)
    questions = models.ManyToManyField(Questions, blank=True, related_name='daily_exams')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Daily Exam {self.date}"
    


class DailyExamAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_exam_attempts')
    daily_exam = models.ForeignKey(DailyExam, on_delete=models.CASCADE, related_name='attempts')
    score = models.FloatField()
    time_taken = models.IntegerField(help_text="Time taken in seconds")
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # A user can only attempt a specific daily exam once
        unique_together = ('user', 'daily_exam')
        ordering = ['-score', 'time_taken'] # Order by highest score, then fastest time


# In questionbank/models.py

class ModelExam(models.Model):
    name = models.CharField(max_length=255, help_text="e.g., LDC Model Paper 1")
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='model_exams')
    questions = models.ManyToManyField(Question, help_text="Select exactly 100 questions for this model exam.")
    duration_minutes = models.PositiveIntegerField(default=120)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

class ModelExamAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='model_exam_attempts')
    model_exam = models.ForeignKey(ModelExam, on_delete=models.CASCADE, related_name='attempts')
    score = models.FloatField()
    time_taken = models.IntegerField(help_text="Time taken in seconds")
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-score', 'time_taken']



class PreviousYearPaper(models.Model):
    title = models.CharField(max_length=255, help_text="e.g., LDC Main Exam 2017")
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='pyq_papers')
    year = models.PositiveIntegerField()
    pdf_file = models.FileField(upload_to='pyq_papers/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-year']

    def __str__(self):
        return self.title
    


class Syllabus(models.Model):
    exam = models.OneToOneField(Exam, on_delete=models.CASCADE, related_name='syllabus')
    details = models.TextField(help_text="Detailed syllabus content. Can include HTML for formatting.")
    pdf_file = models.FileField(upload_to='syllabuses/', null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Syllabus for {self.exam.name}"

from django.utils import timezone

class ExamAnnouncement(models.Model):
    # REMOVED: exam, notification_date, last_date_to_apply, exam_date, notes
    # NEW fields below:
    title = models.CharField(max_length=255, help_text="e.g., EXAMINATION PROGRAMME FOR THE MONTH OF SEPTEMBER 2025",null=True,)
    pdf_file = models.FileField(upload_to='exam_programmes/', null=True, blank=True)
    publication_date = models.DateField(default=timezone.now)

    class Meta:
        # Order by the most recent publication date first
        ordering = ['-publication_date']

    def __str__(self):
        return self.title
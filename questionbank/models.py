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
    slug = models.SlugField(max_length=150, null=True, blank=True, unique=True)
    year = models.IntegerField()
    duration_minutes = models.PositiveIntegerField(default=75, help_text="Exam duration in minutes")

    def __str__(self):
        return f"{self.name} ({self.year})"

class Topic(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=150, null=True, blank=True, unique=True)
    institute = models.ForeignKey('institutes.Institute', on_delete=models.CASCADE, null=True, blank=True, related_name='topics')
    image = models.ImageField(upload_to='topic_images/', null=True, blank=True)

    def __str__(self):
        return self.name

# In questionbank/models.py

class Question(models.Model):
    # The temporary 'old_exam' field is now completely removed.
    
    # Only the new ManyToManyField remains. This is the final version.
    exams = models.ManyToManyField('Exam', related_name='questions')
    slug = models.SlugField(max_length=150, null=True, blank=True, unique=True)
    
    sub_topic = models.CharField(max_length=255, blank=True, help_text="e.g., Indian Freedom Movement")
    topic = models.ForeignKey('Topic', on_delete=models.CASCADE, related_name='questions_topic')
    text = models.TextField()
    options = models.JSONField()
    correct_answer = models.CharField(max_length=1)
    explanation = models.TextField(blank=True)
    
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    difficulty = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        default='medium'
    )
    institute = models.ForeignKey(
        'institutes.Institute', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='questions_institute'
    )
    
    year = models.PositiveIntegerField(null=True, blank=True, help_text="Year this question appeared in exam")
    
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('ml', 'Malayalam'),
    ]
    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default='en')
    
    tags = models.JSONField(default=list, help_text="['freedom_struggle','gandhi'] for SEO tagging")
    is_verified = models.BooleanField(default=False, help_text="Admin-verified question")
    
    SOURCE_CHOICES = [
        ('psc_official', 'PSC Official'),
        ('rank_file', 'Rank File'),
        ('ai_generated', 'AI Generated'),
        ('community', 'Community'),
        ('manual', 'Manual'),
    ]
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, default='manual', blank=True)
    
    times_answered = models.PositiveIntegerField(default=0, db_index=True)
    times_correct = models.PositiveIntegerField(default=0)
    
    # --- Prompt 1: New fields ---
    text_hash = models.CharField(max_length=64, unique=True, db_index=True, null=True, blank=True)
    ai_explanation = models.TextField(blank=True)
    verified = models.BooleanField(default=False)
    times_appeared = models.PositiveIntegerField(default=1)
    is_public = models.BooleanField(default=True)
    submitted_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    
    STATUS_CHOICES = [
        ('approved', 'Approved'),
        ('pending', 'Pending'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved')

    @property
    def global_accuracy(self):
        if self.times_answered == 0:
            return None
        return round((self.times_correct / self.times_answered) * 100, 1)

    def save(self, *args, **kwargs):
        import re
        import hashlib
        from django.utils.text import slugify
        import uuid

        # Normalize text: lowercase, remove punctuation, strip
        normalized = re.sub(r'[^\w\s]', '', self.text).lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Incorporate options to prevent collisions on generic questions
        if self.options and isinstance(self.options, dict):
            opts_str = "|".join(f"{k}:{str(v).lower().strip()}" for k, v in sorted(self.options.items()))
            normalized = f"{normalized}||{opts_str}"
            
        # Calculate SHA-256 hash
        self.text_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()

        # Generate slug from first 8 words
        if not self.slug:
            words = self.text.split()[:8]
            base_slug = slugify(' '.join(words))
            if not base_slug:
                base_slug = 'question'
            
            slug = base_slug[:100]
            while Question.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                suffix = f"-{uuid.uuid4().hex[:6]}"
                slug = f"{base_slug[:100-len(suffix)]}{suffix}"
            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.text[:50]
# ===================================================================
# --- Models for User Data & Tracking ---
# ===================================================================

class UserProfile(models.Model):
    DISTRICT_CHOICES = [
        ('TVM', 'Thiruvananthapuram'),
        ('KLM', 'Kollam'),
        ('PTA', 'Pathanamthitta'),
        ('ALP', 'Alappuzha'),
        ('KTY', 'Kottayam'),
        ('IDK', 'Idukki'),
        ('EKM', 'Ernakulam'),
        ('TCR', 'Thrissur'),
        ('PKD', 'Palakkad'),
        ('MLP', 'Malappuram'),
        ('KOZ', 'Kozhikode'),
        ('WYD', 'Wayanad'),
        ('KNR', 'Kannur'),
        ('KSD', 'Kasaragod'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_photo = models.ImageField(upload_to='profiles/', blank=True, null=True)
    qualifications = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    place = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=3, choices=DISTRICT_CHOICES, blank=True)
    friends = models.ManyToManyField('self', blank=True, symmetrical=True)
    preferred_topics = models.ManyToManyField('Topic', blank=True)
    preferred_difficulty = models.CharField(max_length=20, choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')], blank=True)
    institute = models.ForeignKey('institutes.Institute', on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    is_content_creator = models.BooleanField(default=False, help_text="Designates this user as a trusted community content creator.")

    # --- NEW: Field to store multiple preferred exams ---
    preferred_exams = models.ManyToManyField('Exam', blank=True, related_name='followers')
    bio = models.TextField(blank=True, help_text="A short description or bio for the user's public profile.")
    is_owner = models.BooleanField(default=False) # We will keep this for future institute features
    
    # --- Gamification and Streak Fields ---
    total_xp = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(default=1)
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_active_date = models.DateField(null=True, blank=True)
    streak_freeze_count = models.PositiveIntegerField(default=0)
    
    phone_number = models.CharField(max_length=15, blank=True)
    target_exam_date = models.DateField(null=True, blank=True)
    subscription_plan = models.ForeignKey(
        'subscriptions.Plan', on_delete=models.SET_NULL, null=True, blank=True
    )
    subscription_end_date = models.DateField(null=True, blank=True)
    is_premium = models.BooleanField(default=False)
    referral_code = models.CharField(max_length=10, unique=True, null=True, blank=True)
    referred_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True
    )

    def save(self, *args, **kwargs):
        if not self.referral_code:
            import random, string
            self.referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        super().save(*args, **kwargs)

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

class DailyExam(models.Model):
    date = models.DateField(unique=True)
    questions = models.ManyToManyField(Question, blank=True, related_name='daily_exams')
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
    questions = models.ManyToManyField(
        'Question',
        blank=True,
        related_name='pyq_papers',
        help_text="Link questions from this paper to enable quiz mode"
    )
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


class CurrentAffairs(models.Model):
    LIKELIHOOD_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ]
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)
    content = models.TextField(help_text="Full news article details")
    category = models.CharField(max_length=50, default='Kerala')
    publication_date = models.DateField(default=timezone.now)
    psc_likelihood = models.CharField(max_length=10, choices=LIKELIHOOD_CHOICES, default='medium')
    ai_summary = models.TextField(blank=True, help_text="AI-generated summary")
    source_url = models.URLField(max_length=500, blank=True, null=True, help_text="Credible news source URL")
    mcq = models.JSONField(blank=True, null=True, help_text="AI-generated PSC-style MCQ")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        verbose_name_plural = "Current Affairs"
        ordering = ['-publication_date', '-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            import uuid
            base_slug = slugify(self.title) or "current-affair"
            self.slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class StudyFeedCard(models.Model):
    CARD_TYPES = [
        ('question', 'Question'),
        ('current_affairs', 'Current Affairs'),
        ('fact', 'Fact'),
        ('community_win', 'Community Win')
    ]
    card_type = models.CharField(max_length=20, choices=CARD_TYPES)
    title = models.CharField(max_length=255)
    content_data = models.JSONField(help_text="Dynamic contents based on card type")
    psc_likelihood_tag = models.CharField(max_length=5, blank=True) # 🔥, 💡 etc.
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.card_type}: {self.title}"


class UserFeedView(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    card = models.ForeignKey(StudyFeedCard, on_delete=models.CASCADE)
    viewed_date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'card', 'viewed_date')

    def __str__(self):
        return f"{self.user.username} viewed {self.card.id} on {self.viewed_date}"


class AIExplanationCache(models.Model):
    question = models.ForeignKey('Question', on_delete=models.CASCADE)
    language = models.CharField(max_length=5, default='en') # 'en' or 'ml'
    explanation_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('question', 'language')

    def __str__(self):
        return f"{self.question.id} ({self.language})"


# ===================================================================
# --- Models for Study Flow & Analytics ---
# ===================================================================

class TopicProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='topic_progress')
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    total_attempted = models.PositiveIntegerField(default=0)
    total_correct = models.PositiveIntegerField(default=0)
    easy_attempted = models.PositiveIntegerField(default=0)
    easy_correct = models.PositiveIntegerField(default=0)
    medium_attempted = models.PositiveIntegerField(default=0)
    medium_correct = models.PositiveIntegerField(default=0)
    hard_attempted = models.PositiveIntegerField(default=0)
    hard_correct = models.PositiveIntegerField(default=0)
    last_practiced = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'topic')

    @property
    def accuracy(self):
        if self.total_attempted == 0:
            return 0.0
        return round((self.total_correct / self.total_attempted) * 100, 1)

    @property
    def is_weak_area(self):
        return self.total_attempted >= 10 and self.accuracy < 50

    def __str__(self):
        return f"{self.user.username} | {self.topic.name} | {self.accuracy}%"


class PracticeSession(models.Model):
    SESSION_TYPES = [
        ('topic', 'Topic Practice'),
        ('difficulty', 'Difficulty Drill'),
        ('mixed', 'Mixed Practice'),
        ('pyq', 'Previous Year Questions'),
        ('weak_area', 'Weak Area Drill'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='practice_sessions')
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES)
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True)
    difficulty = models.CharField(max_length=20, blank=True)
    questions = models.ManyToManyField(Question, through='SessionAnswer')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    total_questions = models.PositiveIntegerField(default=0)
    correct_count = models.PositiveIntegerField(default=0)
    time_taken_secs = models.PositiveIntegerField(default=0)

    @property
    def score_percent(self):
        if self.total_questions == 0:
            return 0.0
        return round((self.correct_count / self.total_questions) * 100, 1)

    def __str__(self):
        return f"{self.user.username} | {self.session_type} | {self.score_percent}%"


class SessionAnswer(models.Model):
    session = models.ForeignKey(PracticeSession, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.CharField(max_length=1, blank=True)
    is_correct = models.BooleanField(default=False)
    time_spent_secs = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('session', 'question')

    def __str__(self):
        return f"{self.session.id} | {self.question.id} | {self.is_correct}"
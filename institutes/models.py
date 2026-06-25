from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum
from decimal import Decimal



class Institute(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name='owned_institute')
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True, null=True, blank=True)
    subdomain_active = models.BooleanField(default=True)
    logo = models.ImageField(upload_to='institute_logos/', null=True, blank=True)
    contact_email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # White-label details
    tagline = models.CharField(max_length=255, blank=True)
    primary_color = models.CharField(max_length=7, default='#1976d2') # HEX color
    accent_color = models.CharField(max_length=7, default='#ff9800')
    custom_domain = models.CharField(max_length=255, blank=True, null=True, unique=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    established_year = models.PositiveIntegerField(null=True, blank=True)
    
    login_bg_image = models.ImageField(upload_to='custom_login/', null=True, blank=True)
    login_image_1 = models.ImageField(upload_to='custom_login/', null=True, blank=True)
    login_image_2 = models.ImageField(upload_to='custom_login/', null=True, blank=True)
    login_image_3 = models.ImageField(upload_to='custom_login/', null=True, blank=True)

    def __str__(self):
        return self.name


class Message(models.Model):
    """
    Represents a message (notification) sent from an institute to one or more students.
    This is the single, correct, and simplified definition.
    """
    institute = models.ForeignKey('Institute', on_delete=models.CASCADE, related_name='sent_messages')
    subject = models.CharField(max_length=255)
    body = models.TextField()
    image = models.ImageField(upload_to='message_images/', null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    
    # Standard ManyToManyFields - Django will create the necessary tables automatically.
    recipients = models.ManyToManyField(User, related_name='received_messages')
    read_by = models.ManyToManyField(User, related_name='read_messages', blank=True)

    def __str__(self):
        return f"Message from {self.institute.name}: {self.subject}"

from django.utils import timezone

#-- NEW FEE MANAGEMENT MODELS ---

class FeeItem(models.Model):
    """Represents a single fee item assigned to a student (e.g., Tuition, Exam Fee)."""
    FEE_TYPE_CHOICES = [
        ('tuition', 'Tuition'), ('examination', 'Examination'), ('library', 'Library'),
        ('sports', 'Sports'), ('transport', 'Transport'), ('other', 'Other'),
    ]
    student_profile = models.ForeignKey('questionbank.UserProfile', on_delete=models.CASCADE, related_name='fee_items')
    description = models.CharField(max_length=255)
    fee_type = models.CharField(max_length=20, choices=FEE_TYPE_CHOICES, default='tuition')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    is_paid = models.BooleanField(default=False) # Per-item flag (can be synced or deprecated)

    @property
    def total_paid(self):
        paid = self.payments.aggregate(total=Sum('amount'))['total']
        return paid or Decimal('0.00')

    @property
    def status(self):
        paid = self.total_paid
        if paid >= self.amount:
            return 'paid'
        elif paid > 0:
            return 'partial'
        if self.due_date < timezone.localdate():
            return 'overdue'
        return 'unpaid'

    def __str__(self):
        return f"{self.description} for {self.student_profile.user.username}"

class Payment(models.Model):
    """Represents a single payment made by a student towards a specific fee item."""
    fee_item = models.ForeignKey('FeeItem', on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    student_profile = models.ForeignKey('questionbank.UserProfile', on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50, default='Offline')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Payment of {self.amount} by {self.student_profile.user.username}"



# institutes/models.py

# ... (at the end of the file)
class InstituteJoinRequest(models.Model):
    """
    Represents a student's request to join an institute.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
    ]

    student_profile = models.ForeignKey('questionbank.UserProfile', on_delete=models.CASCADE, related_name='join_requests')
    institute = models.ForeignKey('Institute', on_delete=models.CASCADE, related_name='join_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # A student can only have one pending request for a specific institute at a time
        unique_together = ('student_profile', 'institute')

    def __str__(self):
        return f"{self.student_profile.user.username}'s request to join {self.institute.name}"


class Batch(models.Model):
    """Represents a student batch in the coaching center."""
    institute = models.ForeignKey('Institute', on_delete=models.CASCADE, related_name='batches')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.institute.name}"


class BatchMembership(models.Model):
    """Associates a student profile to a specific batch."""
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='memberships')
    student_profile = models.ForeignKey('questionbank.UserProfile', on_delete=models.CASCADE, related_name='batch_memberships')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('batch', 'student_profile')

    def __str__(self):
        return f"{self.student_profile.user.username} in {self.batch.name}"


class Attendance(models.Model):
    """Tracks daily student attendance for a batch."""
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused')
    ]
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='attendance_records')
    student_profile = models.ForeignKey('questionbank.UserProfile', on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('batch', 'student_profile', 'date')

    def __str__(self):
        return f"{self.student_profile.user.username} - {self.date} - {self.status}"


class Note(models.Model):
    """Uploaded study materials or PDFs scoped by institute and optionally batch."""
    institute = models.ForeignKey('Institute', on_delete=models.CASCADE, related_name='notes')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='notes', null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='study_notes/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
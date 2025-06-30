from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum
from decimal import Decimal



class Institute(models.Model):
    # ... your Institute model remains the same ...
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name='owned_institute')
    name = models.CharField(max_length=255, unique=True)
    logo = models.ImageField(upload_to='institute_logos/', null=True, blank=True)
    contact_email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
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
    is_paid = models.BooleanField(default=False) # We can track status per item

    def __str__(self):
        return f"{self.description} for {self.student_profile.user.username}"

class Payment(models.Model):
    """Represents a single payment made by a student towards their total balance."""
    student_profile = models.ForeignKey('questionbank.UserProfile', on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50, default='Offline')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Payment of {self.amount} by {self.student_profile.user.username}"



class FeeStructure(models.Model):
    """
    Defines the fee structure for a specific student in an institute.
    """
    student_profile = models.OneToOneField('questionbank.UserProfile', on_delete=models.CASCADE, related_name='fee_structure')
    total_fees = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    due_date = models.DateField(null=True, blank=True)
    
    @property
    def amount_paid(self):
        paid = self.transactions.aggregate(total=Sum('amount'))['total']
        # CORRECTED: Return a Decimal('0.00') instead of a float 0.00
        return paid or Decimal('0.00')
    
    @property
    def balance_due(self):
        # This will now correctly subtract a Decimal from a Decimal
        return self.total_fees - self.amount_paid

    def __str__(self):
        if self.student_profile and self.student_profile.user:
            return f"Fee Structure for {self.student_profile.user.username}"
        return f"Fee Structure {self.id}"

class PaymentTransaction(models.Model):
    """
    Records a single payment made by a student.
    """
    # Using a string reference is a best practice for ForeignKeys.
    fee_structure = models.ForeignKey('FeeStructure', on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50, default='Offline')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Payment of {self.amount} on {self.payment_date.strftime('%Y-%m-%d')}"


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
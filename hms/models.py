import uuid
import logging
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.core.validators import MinLengthValidator
from django.contrib.auth.models import AbstractUser, Group, Permission


logger = logging.getLogger('hms')


# Custom User Model (if needed)
class CustomUser(AbstractUser):
    user_type_choices = (
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
        ('admin', 'Admin'),
    )
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    )
    
    user_type = models.CharField(max_length=10, choices=user_type_choices, default='patient')
    full_name = models.CharField(max_length=255,blank=True, null=True)  # Add full name field
    contact_number = models.CharField(max_length=15, blank=True, null=True)  # Add contact number
    address = models.TextField(blank=True, null=True)  # Add address
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)  # Add this field
    groups = models.ManyToManyField(Group, related_name="customuser_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="customuser_permissions", blank=True)

    def __str__(self):
        return self.username


# Patient Model
class Patient(models.Model):
    patient_code = models.CharField(max_length=10, unique=True, editable=False, blank=True, null=True)
    created_at = models.DateTimeField(default=now)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    date_of_birth = models.DateField(blank=True, null=True)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], blank=True, null=True)
    aadhar_number = models.CharField(max_length=12, unique=True, validators=[MinLengthValidator(12)], blank=True, null=True)
    blood_group = models.CharField(max_length=3, blank=True, null=True, choices=[
        ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'), 
        ('O+', 'O+'), ('O-', 'O-'), ('AB+', 'AB+'), ('AB-', 'AB-')
    ])
    email = models.EmailField(unique=True, blank=True, null=True)

    # Guarantor Details
    guarantor_name = models.CharField(max_length=255, blank=True, null=True)
    guarantor_address = models.TextField(blank=True, null=True)
    guarantor_mobile = models.CharField(max_length=15, blank=True, null=True)
    guarantor_relationship = models.CharField(max_length=50, blank=True, null=True)
    guarantor_gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], blank=True, null=True)

    def save(self, *args, **kwargs):
        """Override save method to log patient creation and updates"""
        try:
            if not self.patient_code:
                self.patient_code = str(uuid.uuid4().hex[:10]).upper()
                logger.info(f"Generated new patient code: {self.patient_code} for {self.user.full_name}")
            
            super().save(*args, **kwargs)

            logger.info(f"Patient saved successfully: {self.user.full_name} (Code: {self.patient_code})")

        except Exception as e:
            logger.error(f"Error saving patient {self.user.full_name}: {e}")
            raise e  # Re-raise the exception to ensure Django handles it

    def __str__(self):
        return f"{self.user.full_name} ({self.patient_code})"

# Doctor Model
class Doctor(models.Model):
    created_at = models.DateTimeField(default=now)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    specialization = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=15)
    availability = models.CharField(max_length=255, default="9 AM - 5 PM")

    def __str__(self):
        return f"Dr. {self.user.username} - {self.specialization}"

# Appointment Model
class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    date = models.DateTimeField(default=now)  # Allows scheduling in the future
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    # created_at = models.DateTimeField(auto_now_add=True)  # Track when the appointment was booked

    def clean(self):
        """ Ensure the appointment is not scheduled in the past """
        if self.date < now():
            raise ValidationError("Appointment date cannot be in the past.")

    def save(self, *args, **kwargs):
        """ Validate before saving """
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient.user.full_name} - {self.doctor.user.full_name} ({self.get_status_display()})"

# Emergency Ward Model
class Emergency(models.Model):
    created_at = models.DateTimeField(default=now)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    admitted_at = models.DateTimeField(auto_now_add=True)
    condition = models.TextField()

    def __str__(self):
        return f"Emergency case for {self.patient.user.username}"

# IPD Model
class IPD(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    room_number = models.CharField(max_length=10)
    admitted_on = models.DateTimeField(auto_now_add=True)
    discharge_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"IPD - {self.patient.user.username} - Room {self.room_number}"

# OPD Model
class OPD(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    visit_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(default=now)
    diagnosis = models.TextField()

    def __str__(self):
        return f"OPD Visit - {self.patient.user.username}"

# Billing Model
class Billing(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('paid', 'Paid'), ('pending', 'Pending')], default='pending')
    generated_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Billing for {self.patient.user.username} - {self.total_amount}"

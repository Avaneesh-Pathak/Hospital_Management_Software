import uuid
import logging
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.core.validators import MinLengthValidator
from django.contrib.auth.models import AbstractUser, Group, Permission

logger = logging.getLogger('hms')


# Custom User Model
class CustomUser(AbstractUser):

    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    )
    full_name = models.CharField(max_length=255, blank=True, null=True)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)

    groups = models.ManyToManyField(Group, related_name="customuser_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="customuser_permissions", blank=True)

    def __str__(self):
        return self.username


# Patient Model
class Patient(models.Model):
    patient_code = models.CharField(max_length=10, unique=True, editable=False, blank=True, null=True)
    created_at = models.DateTimeField(default=now)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="patient")
    date_of_birth = models.DateField(blank=True, null=True)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=CustomUser.GENDER_CHOICES, blank=True, null=True)
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
    guarantor_gender = models.CharField(max_length=10, choices=CustomUser.GENDER_CHOICES, blank=True, null=True)

    def save(self, *args, **kwargs):
        """Ensure a unique patient_code is assigned"""
        if not self.patient_code:
            self.patient_code = uuid.uuid4().hex[:10].upper()
            while Patient.objects.filter(patient_code=self.patient_code).exists():
                self.patient_code = uuid.uuid4().hex[:10].upper()
            logger.info(f"Generated patient code: {self.patient_code}")

        super().save(*args, **kwargs)
        logger.info(f"Patient {self.user.full_name} saved successfully.")

    def __str__(self):
        return f"{self.user.full_name} ({self.patient_code})"


# Doctor Model
class Doctor(models.Model):
    created_at = models.DateTimeField(default=now)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="doctor")
    specialization = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=15)
    availability = models.CharField(max_length=255, default="9 AM - 5 PM")

    def __str__(self):
        return f"Dr. {self.user.full_name} - {self.specialization}"


# Appointment Model

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="appointments")
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="appointments")
    date = models.DateField()  # Only allow selecting a date
    time = models.TimeField(blank=True, null=True)  # Auto-assigned
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    class Meta:
        unique_together = ("doctor", "date","patient")  # Prevent double booking at the same time

    def clean(self):
        """ Validate appointment date and prevent multiple bookings for the patient on the same date """
        if self.date < now().date():
            raise ValidationError("Appointment date cannot be in the past.")

        # Check if the patient already has an appointment on this date
        if Appointment.objects.filter(patient=self.patient, date=self.date).exists():
            raise ValidationError("You already have an appointment booked for this date.")

    def get_next_available_time(self):
        """ Find the next available time slot for the selected doctor on the given date """
        available_slots = [
            "09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00"
        ]

        # Get booked time slots for this doctor on the selected date
        booked_slots = Appointment.objects.filter(doctor=self.doctor, date=self.date).values_list('time', flat=True)
        booked_slots = [slot.strftime('%H:%M') for slot in booked_slots if slot]

        # Find first available slot
        for slot in available_slots:
            if slot not in booked_slots:
                return slot

        return None  # No available slots

    def save(self, *args, **kwargs):
        """ Assign an available time slot automatically """
        self.clean()  # Ensure validations

        if not self.time:  # If time is not already set
            next_slot = self.get_next_available_time()
            if not next_slot:
                raise ValidationError("No available slots for this doctor on the selected date.")
            self.time = next_slot

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient.user.full_name} - {self.doctor.user.full_name} ({self.date} {self.time})"

# IPD Model
class IPD(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="ipd_records")
    room_number = models.CharField(max_length=10)
    admitted_on = models.DateTimeField(auto_now_add=True)
    discharge_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"IPD - {self.patient.user.full_name} - Room {self.room_number}"


# OPD Model
class OPD(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="opd_visits")
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="opd_visits")
    visit_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(default=now)
    diagnosis = models.TextField()

    def __str__(self):
        return f"OPD Visit - {self.patient.user.full_name}"


# Billing Model
class Billing(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="bills")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('paid', 'Paid'), ('pending', 'Pending')], default='pending')
    generated_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Billing for {self.patient.user.full_name} - {self.total_amount}"


# Billing Item Model (New)
class BillingItem(models.Model):
    bill = models.ForeignKey(Billing, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.description} - {self.amount}"


# Emergency Ward Model
class Emergency(models.Model):
    created_at = models.DateTimeField(default=now)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="emergencies")
    admitted_at = models.DateTimeField(auto_now_add=True)
    condition = models.TextField()

    def __str__(self):
        return f"Emergency case for {self.patient.user.full_name}"

import uuid
import logging
from django.utils import timezone
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
        return f"{self.patient.user.full_name} - {self.doctor.user.full_name} ({self.get_status_display()})"

# Emergency Ward Model
class EmergencyCase(models.Model):
    EMERGENCY_TYPES = [
        ('accident', 'Accident'),
        ('cardiac', 'Cardiac Arrest'),
        ('stroke', 'Stroke'),
        ('respiratory', 'Respiratory Emergency'),
        ('other', 'Other'),
    ]

    patient = models.OneToOneField(Patient, on_delete=models.CASCADE)
    referred_by = models.CharField(max_length=255, null=True, blank=True)
    referrer_contact = models.CharField(max_length=15, null=True, blank=True)
    emergency_type = models.CharField(max_length=20, choices=EMERGENCY_TYPES)
    case_description = models.TextField()
    admitted_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Emergency Case - {self.patient.user.full_name}"



#Room Model
class Room(models.Model):
    ROOM_TYPES = [
        ('general', 'General Ward'),
        ('semi-private', 'Semi-Private'),
        ('private', 'Private'),
        ('icu', 'ICU'),
    ]
    
    room_number = models.CharField(max_length=10, unique=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"Room {self.room_number} - {self.get_room_type_display()}"
    



# IPD Model
class IPD(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, limit_choices_to={'is_available': True},null=True, blank=True)
    admitted_on = models.DateTimeField(auto_now_add=True)
    discharge_date = models.DateTimeField(null=True, blank=True)
    reason_for_admission = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        """ Mark room as unavailable when a patient is admitted """
        if self.room:
            self.room.is_available = False
            self.room.save()
        super().save(*args, **kwargs)

    def discharge(self):
        """ Discharge patient and mark room as available again """
        self.discharge_date = timezone.now()
        self.room.is_available = True
        self.room.save()
        self.save()

    def __str__(self):
        return f"IPD - {self.patient.user.full_name} - {self.room.room_number}"

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
class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('medicine', 'Medicine'),
        ('injection', 'Injection'),
        ('resource', 'Resource'),
        ('doctor_fee', 'Doctor Fee'),
        ('surgery', 'Surgery'),
        ('checkup', 'Checkup'),
        ('other', 'Other'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES,null=True)
    description = models.TextField(null=True)  # Description of the expense
    cost = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.patient.patient_code} - {self.category} - ₹{self.cost}"

class Billing(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=[('paid', 'Paid'), ('pending', 'Pending')], default='pending')
    generated_on = models.DateTimeField(auto_now_add=True)

    def update_total(self):
        """Automatically update total amount based on expenses."""
        self.total_amount = Expense.objects.filter(patient=self.patient).aggregate(models.Sum('cost'))['cost__sum'] or 0
        self.save()

    def __str__(self):
        return f"Billing for {self.patient.patient_code} - ₹{self.total_amount} (Paid: ₹{self.paid_amount})"






class Employee(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    role = models.CharField(max_length=100)  # Example: Nurse, Receptionist, Admin
    contact_number = models.CharField(max_length=15)
    hired_date = models.DateField(default=now)

    def __str__(self):
        return f"{self.user.full_name} - {self.role}"

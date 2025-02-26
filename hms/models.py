import uuid
import os
import logging
from django.db import models
from django.utils import timezone
from django.utils.timezone import now
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.utils.translation import gettext_lazy as _
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

    def save(self, *args, **kwargs):
        # Fetch the existing user object if it exists
        if self.pk:
            existing_user = CustomUser.objects.filter(pk=self.pk).first()
            if existing_user and existing_user.password != self.password:
                self.set_password(self.password)  # Hash only if password changed
        else:
            if self.password and not self.password.startswith('pbkdf2_'):  # Prevent double hashing
                self.set_password(self.password)

        super().save(*args, **kwargs)

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

    # ✅ Profile Picture Field
    profile_picture = models.ImageField(upload_to='patient_profiles/', blank=True, null=True)

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



class PatientReport(models.Model):
    patient = models.ForeignKey('hms.Patient', on_delete=models.CASCADE, related_name="reports")
    file_name = models.CharField(max_length=255, help_text="Enter a name for this report")  # Custom file name
    report_file = models.FileField(upload_to="patient_reports/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.file_name} ({self.patient.patient_code})"

    def get_filename(self):
        return os.path.basename(self.report_file.name)

    def save(self, *args, **kwargs):
        """Override save method to set a unique file path."""
        if self.report_file and not self.report_file.name.startswith("patient_reports/"):
            ext = self.report_file.name.split('.')[-1]
            filename = f"{self.patient.patient_code}_{now().strftime('%Y%m%d%H%M%S')}.{ext}"
            self.report_file.name = os.path.join("patient_reports/", filename)
        super().save(*args, **kwargs)


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
    date = models.DateField()
    time = models.TimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    class Meta:
        unique_together = ("doctor", "date", "patient")

    def clean(self):
        if self.date < now().date():
            raise ValidationError("Appointment date cannot be in the past.")

        # Prevent duplicate appointments only when creating a new one
        if self.pk is None:  # This ensures validation runs only when creating an appointment
            if Appointment.objects.filter(patient=self.patient, date=self.date, doctor=self.doctor).exists():
                raise ValidationError("You already have an appointment booked for this date.")


    def get_next_available_time(self):
        available_slots = ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00"]
        booked_slots = Appointment.objects.filter(doctor=self.doctor, date=self.date).values_list('time', flat=True)
        booked_slots = [slot.strftime('%H:%M') for slot in booked_slots if slot]
        for slot in available_slots:
            if slot not in booked_slots:
                return slot
        return None

    def save(self, *args, **kwargs):
        self.clean()
        if not self.time:
            next_slot = self.get_next_available_time()
            if not next_slot:
                raise ValidationError("No available slots for this doctor on the selected date.")
            self.time = next_slot
        super().save(*args, **kwargs)
        if self.status == "confirmed":
            OPD.objects.get_or_create(
                patient=self.patient,
                doctor=self.doctor,
                defaults={"diagnosis": "Pending diagnosis"},
            )

    def __str__(self):
        return f"{self.patient.user.full_name} - {self.doctor.user.full_name} ({self.get_status_display()})"

# Emergency Ward Model
class EmergencyCase(models.Model):
    class Status(models.TextChoices):
        PENDING = "Pending", _("Pending")
        ADMITTED = "Admitted", _("Admitted")
        DISCHARGED = "Discharged", _("Discharged")

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
    severity = models.IntegerField(default=1, help_text="Severity Level (1-5)")
    admitted_on = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

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
    total_beds = models.IntegerField(default=1,null=True)
    available_beds = models.IntegerField(default=1,null=True)
    bed_price_per_day = models.DecimalField(max_digits=10, decimal_places=2,null=True)
    occupied_beds = models.JSONField(default=list)  # Store occupied bed numbers in a list

    def __str__(self):
        return f"Room {self.room_number} - {self.get_room_type_display()}"

    def update_availability(self):
        """Update room availability based on occupied beds."""
        self.available_beds = self.total_beds - len(self.occupied_beds)
        self.is_available = self.available_beds > 0
        self.save()

    def admit_patient_to_bed(self):
        """Assign an available bed to a patient and update availability."""
        for bed_number in range(1, self.total_beds + 1):
            if bed_number not in self.occupied_beds:
                self.occupied_beds.append(bed_number)
                self.update_availability()
                return bed_number
        return None  # No available beds

    def discharge_patient_from_bed(self, bed_number):
        """Release a bed when a patient is discharged."""
        if bed_number in self.occupied_beds:
            self.occupied_beds.remove(bed_number)
            self.update_availability()

    def calculate_total_cost(self, stay_days):
        """Calculate total cost based on stay duration and bed pricing."""
        return self.bed_price_per_day * stay_days
    



# IPD Model
class IPD(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, limit_choices_to={'is_available': True},null=True, blank=True)
    admitted_on = models.DateTimeField(auto_now_add=True)
    discharge_date = models.DateTimeField(null=True, blank=True)
    reason_for_admission = models.TextField(null=True, blank=True)
    # ✅ Added Fields
    bed_number = models.IntegerField(null=True, blank=True)
    bed_price_per_day = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
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

class Prescription(models.Model):
    ipd = models.ForeignKey(IPD, on_delete=models.CASCADE, related_name="prescriptions")
    medication = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100)
    timing = models.DateTimeField()

    def __str__(self):
        return f"Prescription for {self.ipd.patient.user.full_name} - {self.medication} ({self.dosage}) at {self.timing})"


# OPD Model
class OPD(models.Model):
    # Basic Fields
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="opd_visits")
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="opd_visits")
    visit_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(default=now)
    diagnosis = models.TextField()

    # Additional Fields
    symptoms = models.TextField(blank=True, null=True)  # Symptoms described by the patient
    prescription = models.TextField(blank=True, null=True)  # Prescribed medication or treatment
    follow_up_date = models.DateField(blank=True, null=True)  # Date for the next follow-up visit
    VISIT_TYPE_CHOICES = [
        ('new', 'New Visit'),
        ('follow_up', 'Follow-up Visit'),
        ('emergency', 'Emergency Visit'),
    ]
    visit_type = models.CharField(max_length=20, choices=VISIT_TYPE_CHOICES, default='new')  # Type of visit
    PAYMENT_STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('pending', 'Pending'),
    ]
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')  # Payment status
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Amount paid for the visit

    def __str__(self):
        return f"OPD Visit - {self.patient.user.full_name} ({self.visit_date.strftime('%Y-%m-%d')})"


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
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Monthly salary
    last_payment_date = models.DateField(null=True, blank=True)  # Date when last salary was paid
    next_due_date = models.DateField(null=True, blank=True)  # Next due date for salary payment

    def __str__(self):
        return f"{self.user.full_name} - {self.role}"

    def pay_salary(self, payment_date):
        """
        Method to pay salary and update payment and due dates.
        """
        if payment_date:
            # Convert payment_date from string to datetime.date object
            payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
            self.last_payment_date = payment_date
            self.next_due_date = payment_date + timedelta(days=30)  # Assuming monthly salary
            self.save()



class License(models.Model):
    LICENSE_TYPES = [
        ('Medical', 'Medical'),
        ('Pharmacy', 'Pharmacy'),
        ('Fire Safety', 'Fire Safety'),
        ('Other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Expired', 'Expired'),
        ('Pending Renewal', 'Pending Renewal'),
    ]
    
    name = models.CharField(max_length=255)
    license_type = models.CharField(max_length=50, choices=LICENSE_TYPES)
    issue_date = models.DateField()
    expiry_date = models.DateField()
    document = models.FileField(upload_to='licenses/', blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="Active")
    renewed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    
    def is_expiring_soon(self):
        
        return (self.expiry_date - now().date()).days <= 30  # Warning if less than 30 days

    def __str__(self):
        return f"{self.name} ({self.license_type})"
    

class Asset(models.Model):
    ASSET_TYPES = [
        ('Medical Equipment', 'Medical Equipment'),
        ('Furniture', 'Furniture'),
        ('Electronics', 'Electronics'),
        ('Other', 'Other'),
    ]
    
    name = models.CharField(max_length=255)
    asset_type = models.CharField(max_length=50, choices=ASSET_TYPES)
    purchase_date = models.DateField()
    warranty_expiry = models.DateField()
    quantity = models.PositiveIntegerField()
    location = models.CharField(max_length=255, help_text="Where is this asset located?")
    
    def is_under_warranty(self):
        return self.warranty_expiry > now().date()

    def __str__(self):
        return f"{self.name} - {self.asset_type} ({self.quantity} units)"


class Maintenance(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="maintenance_logs")
    maintenance_date = models.DateField()
    next_due_date = models.DateField()
    performed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Maintenance for {self.asset.name} on {self.maintenance_date}"

import uuid
import os
import logging
from decimal import Decimal
from django.http import Http404
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.timezone import now
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.auth import get_user_model
logger = logging.getLogger('hms')




# Custom User Model
class CustomUser(AbstractUser):
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    )

    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('doctor', 'Doctor'),
        ('nurse', 'Nurse'),
        ('staff', 'Staff'),
    )

    full_name = models.CharField(max_length=255, blank=True, null=True)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')

    groups = models.ManyToManyField(Group, related_name="customuser_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="customuser_permissions", blank=True)

    def save(self, *args, **kwargs):
        if self.pk:
            existing_user = CustomUser.objects.filter(pk=self.pk).first()
            if existing_user and existing_user.password != self.password:
                self.set_password(self.password)
        else:
            if self.password and not self.password.startswith('pbkdf2_'):
                self.set_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username


# Notification Model
class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"To {self.recipient} - {self.message[:30]}"

class Patient(models.Model):
    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'),
        ('O+', 'O+'), ('O-', 'O-'), ('AB+', 'AB+'), ('AB-', 'AB-')
    ]

    RELATIONSHIP_CHOICES = [
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('son', 'Son'),
        ('daughter', 'Daughter'),
        ('spouse', 'Spouse'),
        ('friend', 'Friend'),
        ('other', 'Other'),
    ]

    # Basic Patient Information
    patient_code = models.CharField(max_length=35, unique=True, editable=False, blank=True, null=True)
    created_at = models.DateTimeField(default=now)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="patient")
    date_of_birth = models.DateField(blank=True, null=True)
    age = models.TextField(blank=True, null=True)  # Age field
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=CustomUser.GENDER_CHOICES, blank=True, null=True)
    aadhar_number = models.CharField(max_length=12, unique=True, validators=[MinLengthValidator(12)], blank=True, null=True)
    blood_group = models.CharField(max_length=3, blank=True, null=True, choices=BLOOD_GROUP_CHOICES)
    weight = models.DecimalField(max_digits=6, decimal_places=2,blank=True,null=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    assigned_doctor = models.ForeignKey('Doctor', on_delete=models.SET_NULL, null=True, blank=True, related_name='patients')
    # Medical Information
    allergies = models.TextField(blank=True, null=True)  # Known allergies
   

    # Emergency Contact Information
    emergency_contact_name = models.CharField(max_length=255, blank=True, null=True)
    emergency_contact_number = models.CharField(max_length=15, blank=True, null=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True, null=True, choices=RELATIONSHIP_CHOICES)
    accompanying_person_address = models.CharField(max_length=50,blank=True, null=True)

  

    # Profile Picture
    profile_picture = models.ImageField(upload_to='patient_profiles/', blank=True, null=True)

    def generate_patient_code(self):
        """Generate a unique patient code based on logic."""
        # Extract date and time components
        now = datetime.now()
        year = now.strftime('%Y')  # 4-digit year
        month = now.strftime('%m')  # 2-digit month
        day = now.strftime('%d')    # 2-digit day
        hour = now.strftime('%H')   # 2-digit hour (24-hour format)
        minute = now.strftime('%M') # 2-digit minute

        # Extract initials from the patient's full name
        initials = ''.join([name[0].upper() for name in self.user.full_name.split()]) if self.user.full_name else 'PT'

        # Generate a unique identifier (last 4 characters of UUID)
        unique_id = uuid.uuid4().hex[-4:].upper()

        # Combine components to create the patient code
        patient_code = f"{year}{month}{day}{hour}{minute}-{initials}-{unique_id}"

        return patient_code

    def save(self, *args, **kwargs):
        """Ensure a unique patient_code is assigned."""
        if not self.patient_code:
            self.patient_code = self.generate_patient_code()
            while Patient.objects.filter(patient_code=self.patient_code).exists():
                self.patient_code = self.generate_patient_code()
            logger.info(f"Generated patient code: {self.patient_code}")

        # Calculate age dynamically
        if self.date_of_birth:
            today = now().date()
            delta = today - self.date_of_birth  # Difference in days

            if delta.days < 30:
                self.age = f"{delta.days} day(s) old" if delta.days > 0 else "Newborn"
            elif delta.days < 365:
                months = delta.days // 30
                self.age = f"{months} month(s) old"
            else:
                years = delta.days // 365
                self.age = f"{years} year(s) old"

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


class Nurse(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='nurse_profile')
    department = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.user.full_name

class Staff(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='staff_profile')
    role_description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.user.full_name
    
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
    ('picu', 'PICU'),
    ('private', 'Private'),
    ('general', 'General Ward'),
    ('nicu', 'NICU'),
    ('icu', 'ICU'),
    ('emergency', 'Emergency Ward'),
    ('other', 'Other'),]
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
    patient = models.ForeignKey("Patient", on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, limit_choices_to={'is_available': True}, null=True, blank=True)
    admitted_on = models.DateTimeField(auto_now_add=True)
    discharge_date = models.DateTimeField(null=True, blank=True)
    reason_for_admission = models.TextField(null=True, blank=True)
    bed_number = models.IntegerField(null=True, blank=True)
    bed_price_per_day = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, editable=False)

    def save(self, *args, **kwargs):
        """Automatically calculate total cost before saving."""
        if self.room and not self.bed_price_per_day:
            self.bed_price_per_day = self.room.bed_price_per_day  # Assign bed price from the room
        
        self.calculate_total_cost()

        super().save(*args, **kwargs)

    def calculate_total_cost(self):
        """Calculate the total cost based on the duration and bed price."""
        if self.admitted_on and self.bed_price_per_day:
            end_date = self.discharge_date or timezone.now()
            stay_duration = (end_date - self.admitted_on).days
            if stay_duration == 0:
                stay_duration = 1  # Ensure at least one day's charge
            self.total_cost = self.bed_price_per_day * stay_duration
        return self.total_cost

    def discharge(self):
        """Discharge patient, mark room as available, and record income."""
        if not self.discharge_date:
            self.discharge_date = timezone.now()

        # Calculate total cost
        self.calculate_total_cost()

        # Mark room and bed as available
        if self.room:
            self.room.discharge_patient_from_bed(self.bed_number)
            self.room.update_availability()
            self.room.save()

        # Save the IPD record
        self.save()

        # Record income in AccountingRecord
        if self.total_cost > 0:
            AccountingRecord.objects.create(
                transaction_type='income',
                source='ipd',
                amount=self.total_cost,
                description=f"IPD charges for {self.patient.user.full_name} (Room {self.room.room_number}, Bed {self.bed_number})",
                patient=self.patient,
                room=self.room,
            )

    def transfer_to_other_hospital(self, hospital_name):
        """Transfer the patient to another hospital and mark the current bed as available."""
        if not hospital_name:
            raise ValueError("Hospital name is required for transfer.")

        # Mark the current bed as available
        if self.room:
            self.room.discharge_patient_from_bed(self.bed_number)
            self.room.update_availability()
            self.room.save()

        # Update the IPD record
        self.transferred_to_hospital = hospital_name
        self.discharge_date = timezone.now()
        self.save()

    def change_bed(self, new_room, new_bed_number):
        """Change the patient's bed to a new bed in a new or same room."""
        if not new_room.is_available:
            raise ValueError("The new room is not available.")

        if new_bed_number in new_room.occupied_beds:
            raise ValueError("The selected bed is already occupied.")

        # Mark the previous bed as available
        if self.room:
            self.room.discharge_patient_from_bed(self.bed_number)
            self.room.update_availability()
            self.room.save()

        # Assign the new bed
        self.room = new_room
        self.bed_number = new_bed_number
        new_room.occupied_beds.append(new_bed_number)
        new_room.update_availability()
        new_room.save()

        # Save the IPD record
        self.save()

    def __str__(self):
        return f"IPD - {self.patient.user.full_name} - {self.room.room_number if self.room else 'No Room'}"




class NICUVitals(models.Model):
    SKIN_COLOR_CHOICES = [
        ('pink', 'Pink (Normal)'),
        ('pallor', 'Pallor (Pale)'),
        ('jaundiced', 'Jaundiced (Yellowish)'),
        ('cyanotic', 'Cyanotic (Bluish)'),
        ('mottled', 'Mottled (Blotchy)'),
        ('erythematous', 'Erythematous (Red/Flushed)'),
        ('grayish', 'Grayish'),
        ('dusky', 'Dusky (Bluish-Gray)'),
    ]
    ipd = models.ForeignKey('IPD', on_delete=models.CASCADE, related_name='nicu_vitals')
    date = models.DateField(auto_now_add=True)
    time = models.TimeField(default=timezone.now)  # New field to record time slots (2-hour interval)
    
    # Vitals
    temperature = models.DecimalField(max_digits=4, decimal_places=1,null=True, blank=True)
    respiratory_rate = models.IntegerField(null=True, blank=True)
    pulse_rate = models.IntegerField(null=True, blank=True)
    cft = models.DecimalField(max_digits=3, decimal_places=1,null=True, blank=True)
    skin_color = models.CharField(max_length=20, choices=SKIN_COLOR_CHOICES,default='pink')
    seizure = models.BooleanField(null=True, blank=True)
    spo2 = models.IntegerField(null=True, blank=True)
    oxygen = models.CharField(max_length=100,help_text="Options: 1. Nasal Prong, 2. Hood, 3. Without O2",null=True, blank=True)
    retraction = models.BooleanField(null=True, blank=True)

    # Fluid Balance
    iv_fluids = models.IntegerField(null=True, blank=True)
    by_nasogastric = models.IntegerField(null=True, blank=True)
    oral = models.IntegerField(null=True, blank=True)
    breastfeeding = models.BooleanField(null=True, blank=True)
    urine = models.CharField(max_length=10, choices=[('nil', 'Nil'), ('ml', 'ML')])
    urine_value = models.FloatField(blank=True, null=True)  # Store ML value
    stool = models.BooleanField(null=True, blank=True)
    ift = models.IntegerField(null=True, blank=True)
    vomiting = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return f"Vitals for {self.ipd.patient.user.full_name} on {self.date}"
    


class PatientTransfer(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="transfers")
    transfer_date = models.DateTimeField(auto_now_add=True)
    transfer_reason = models.TextField()
    transferred_to_hospital = models.CharField(max_length=255)  # New hospital name
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.patient.user.full_name} transferred to {self.transferred_to_hospital}"

import json


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

    def get_prescription_items(self):
        try:
            return json.loads(self.prescription) if self.prescription else []
        except json.JSONDecodeError:
            return []
    
    def __str__(self):
        return f"OPD Visit - {self.patient.user.full_name} ({self.visit_date.strftime('%Y-%m-%d')})"


from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator

User = get_user_model()

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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        AccountingRecord.objects.create(
            transaction_type='income',
            source='IPD',
            amount=self.cost,
            description=f"{self.get_category_display()} expense for {self.patient.user.full_name}",
            patient=self.patient,
        )
        billing, _ = BillingBase.objects.get_or_create(patient=self.patient)
        billing.calculate_totals()

    def __str__(self):
        return f"{self.patient.patient_code} - {self.category} - ₹{self.cost}"

# new model of billing and payment
class BillingBase(models.Model):
    """Abstract base model for common billing fields"""
    BILL_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('paid', 'Paid'),
        ('partially_paid', 'Partially Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    bill_number = models.CharField(max_length=20, unique=True, editable=False)
    patient = models.ForeignKey("Patient", on_delete=models.PROTECT)
    generated_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=BILL_STATUS_CHOICES, default='draft')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    balance_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        abstract = True
    
    def calculate_totals(self):
        """Calculate all financial fields"""
        self.subtotal = Decimal(self.calculate_subtotal())
        self.tax_amount = Decimal(self.calculate_tax())
        self.discount_amount = Decimal(self.discount_amount)
        self.paid_amount = Decimal(self.paid_amount)

        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        self.balance_amount = self.total_amount - self.paid_amount

        # Update status based on payment
        if self.paid_amount <= Decimal('0.00'):
            self.status = 'generated'
        elif self.paid_amount >= self.total_amount:
            self.status = 'paid'
        else:
            self.status = 'partially_paid'
    @property
    def get_final_amount(self):
        return self.subtotal + self.tax_amount - self.discount_amount
    
    def calculate_subtotal(self):
        """To be implemented by child classes"""
        return Decimal('0.00')
    
    def calculate_tax(self):
        """Default tax calculation (5%) - can be overridden"""
        return self.subtotal * Decimal('0.05')
    @property
    def billing_type(self):
        # Return the billing type based on the model class
        if isinstance(self, OPDBilling):
            return 'OPD'
        elif isinstance(self, IPDBilling):
            return 'IPD'
        else:
            return 'Other'
        
    def save(self, *args, **kwargs):
        if not self.bill_number:
            # Generate bill number specific to model type:
            date_part = timezone.now().strftime('%Y%m%d')
            # Use model-specific prefix
            prefix = ''
            if isinstance(self, OPDBilling):
                prefix = 'OPD'
            elif isinstance(self, IPDBilling):
                prefix = 'IPD'
            else:
                prefix = 'BILL'

            # Get last bill number for this model only
            last_bill = self.__class__.objects.filter(bill_number__startswith=prefix).order_by('-id').first()
            seq_num = (last_bill.id + 1) if last_bill else 1
            self.bill_number = f"{prefix}-{date_part}-{seq_num:04d}"
        
        if not self.due_date:
            self.due_date = timezone.now() + timezone.timedelta(days=7)
        
        self.calculate_totals()
        super().save(*args, **kwargs)

class OPDBilling(BillingBase):
    """Billing model for Outpatient Department"""
    opd_visit = models.ForeignKey("OPD", on_delete=models.PROTECT)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    procedure_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    medication_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    other_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_paid = models.BooleanField(default=False)
    def calculate_subtotal(self):
        return (
            self.consultation_fee + 
            self.procedure_fee + 
            self.medication_fee + 
            self.other_fee
        )
    @property
    def calculated_paid_amount(self):
        # Automatically calculate the paid amount as subtotal
        return self.calculate_subtotal()
    
    @property
    def bill_type(self):
        return 'OPD'
    
    def save(self, *args, **kwargs):
        # Auto-populate fees from OPD visit if not set
        
        if not self.consultation_fee and hasattr(self.opd_visit, 'doctor'):
            self.consultation_fee = self.opd_visit.doctor.consultation_fee or Decimal('0.00')
        # Automatically mark bill as paid if it's marked for payment
        if self.is_paid:
            self.paid_amount = self.calculate_subtotal()

        super().save(*args, **kwargs)

        # Create accounting record if paid and not already recorded
        if self.is_paid and self.paid_amount > 0:
            # from AccountingRecord.models import AccountingRecord  # avoid circular import
            AccountingRecord.objects.get_or_create(
                transaction_type='income',
                source='opd',
                amount=self.paid_amount,
                description=f"OPD payment for {self.opd_visit.patient.user.full_name}",
                patient=self.opd_visit.patient,
                billing_reference=self  # optional, if you have such a field
            )

class IPDBilling(BillingBase):
    """Billing model for Inpatient Department"""
    ipd_admission = models.ForeignKey("IPD", on_delete=models.PROTECT)
    room_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    nursing_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    procedure_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    medication_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    lab_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    other_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    def calculate_subtotal(self):
        return (
            self.room_charges +
            self.nursing_charges +
            self.procedure_charges +
            self.medication_charges +
            self.lab_charges +
            self.other_charges
        )
    @property
    def bill_type(self):
        return 'IPD'
    
    def save(self, *args, **kwargs):
        # Calculate room charges based on IPD stay duration
        if not self.room_charges and self.ipd_admission:
            self.room_charges = self.ipd_admission.calculate_total_cost()
        super().save(*args, **kwargs)

class BillingItem(models.Model):
    """Line items for detailed billing"""
    BILLING_TYPE_CHOICES = [
        ('opd', 'OPD'),
        ('ipd', 'IPD'),
    ]
    
    billing_type = models.CharField(max_length=10, choices=BILLING_TYPE_CHOICES)
    opd_billing = models.ForeignKey(OPDBilling, on_delete=models.CASCADE, null=True, blank=True)
    ipd_billing = models.ForeignKey(IPDBilling, on_delete=models.CASCADE, null=True, blank=True)
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)  # 5% default tax
    amount = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    
    def save(self, *args, **kwargs):
        subtotal = self.unit_price * self.quantity

        discount_amount = subtotal * (self.discount / Decimal('100'))
        discounted_total = subtotal - discount_amount

        tax_amount = discounted_total * (self.tax_rate / Decimal('100'))
        final_amount = discounted_total + tax_amount

        # Round to 2 decimal places
        self.amount = final_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        super().save(*args, **kwargs)

        # Update parent billing totals
        if self.opd_billing:
            self.opd_billing.calculate_totals()
            self.billing_type = 'opd'
            self.opd_billing.save()
        elif self.ipd_billing:
            self.ipd_billing.calculate_totals()
            self.billing_type = 'ipd'
            self.ipd_billing.save()

    def __str__(self):
        return f"{self.description} - {self.amount}"

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class Payment(models.Model):
    """Payment records for billing"""
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('insurance', 'Insurance'),
        ('bank_transfer', 'Bank Transfer'),
        ('upi', 'UPI'),
        ('cheque', 'Cheque'),
    ]
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    object_id = models.PositiveIntegerField( null=True)
    billing = GenericForeignKey('content_type', 'object_id')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    received_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True)
    notes = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Update billing payment fields
        all_payments = Payment.objects.filter(
            content_type=self.content_type,
            object_id=self.object_id
        )
        self.billing.paid_amount = sum(p.amount for p in all_payments)
        self.billing.calculate_totals()
        self.billing.save()

        AccountingRecord.objects.create(
            transaction_type='income',
            source=self.billing._meta.model_name.lower(),
            amount=self.amount,
            description=f"Payment for bill {self.billing.bill_number}",
            patient=self.billing.patient,
            
        )

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
        if payment_date:
            payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
            self.last_payment_date = payment_date
            self.next_due_date = payment_date + timedelta(days=30)
            self.save()
            AccountingRecord.objects.create(
                transaction_type='expense',
                source='salary',
                amount=self.salary,
                description=f"Salary payment for {self.user.full_name}",
                employee=self,
            )



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


#Daybook

class Balance(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    carryover_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Add this field
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True) 

    def __str__(self):
        logger.info(f"Balance created with amount: {self.amount} and carryover amount: {self.carryover_amount}")
        return f"Balance: {self.amount}"
    
    def save(self, *args, **kwargs):
        # Log when the balance is saved (either created or updated)
        action = "created" if self.pk is None else "updated"
        super().save(*args, **kwargs)
        logger.info(f"Balance {action} with amount: {self.amount} and carryover amount: {self.carryover_amount}")

class Daybook(models.Model):
    ACTIVITY_CHOICES = [
        ('pantry', 'Pantry'),
        ('fuel', 'Fuel'),
        ('office_expense', 'Office Expense'),
        ('site_development', 'Site Development'),
        ('site_visit', 'Site Visit'),
        ('printing', 'Printing'),
        ('utility', 'Utility'),
        ('others', 'Others'),
    ]

    date = models.DateField(default=timezone.now)
    activity = models.CharField(max_length=50, choices=ACTIVITY_CHOICES,null=True)
    custom_activity = models.CharField(max_length=100, blank=True, null=True)  # For "Others"
    amount = models.DecimalField(max_digits=10, decimal_places=2,null=True,blank=True)
    remark = models.TextField(blank=True, null=True)
    # Balance field to keep track of remaining balance
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        # Log whenever __str__ is called (representing the Daybook entry)
        activity_display = self.custom_activity if self.activity == 'others' else self.activity
        logger.info(f"Daybook entry created: {self.date} - {activity_display} - Amount: {self.amount}")
        return f"{self.date} - {activity_display} - {self.amount}"

    def save(self, *args, **kwargs):
        # Calculate the new balance after the transaction
        previous_balance = self.__class__.objects.filter(id=self.id).first().current_balance if self.pk else 0
        if self.amount:  # If there's an amount for the transaction, update the balance
            self.current_balance = previous_balance + self.amount
        
        activity_display = self.custom_activity if self.activity == 'others' else self.activity
        action = "created" if self.pk is None else "updated"
        
        super().save(*args, **kwargs)
        
        # Log and send SMS after save
        logger.info(f"Daybook entry {action} with date: {self.date}, activity: {activity_display}, amount: {self.amount}, remaining balance: {self.current_balance}")



class AccountingRecord(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]

    SOURCE_CHOICES = [
        ('opd', 'OPD'),
        ('ipd', 'IPD'),
        ('emergency', 'Emergency'),
        ('salary', 'Salary'),
        ('other', 'Other'),
    ]

    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    date = models.DateTimeField(auto_now_add=True)
    patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True, related_name="financial_records")
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="salary_payments")
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name="room_charges")

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.get_source_display()} - ₹{self.amount}"

    class Meta:
        ordering = ['-date']




class Medicine(models.Model):
    MEDICINE_TYPE_CHOICES = [
        ("syrup", "Syrup"),
        ("injection", "Injection"),
        ("tablet", "Tablet"),
        ("drop", "Drop"),
        ("suspension", "Suspension"),
        ("fluid", "Fluid"),
        ("oral", "Oral"),
        ("other", "Other"),
    ]

    ROUTE_CHOICES = [
        ("oral", "Oral"),
        ("iv", "Intravenous"),
        ("im", "Intramuscular"),
        ("sc", "Subcutaneous"),
        ("topical", "Topical"),
        ("inhalation", "Inhalation"),
        ("nasal", "Nasal"),
        ("rectal", "Rectal"),
        ("other", "Other"),
    ]

    DURATION_FREQUENCY_CHOICES = [
    ("24H", "Once daily (Every 24 hours)"),
    ("12H", "Twice daily (Every 12 hours)"),
    ("8H", "Thrice daily (Every 8 hours)"),
    ("6H", "Four times daily (Every 6 hours)"),
    ("4H", "Every 4 hours"),
    ("SOS", "As needed (SOS)"),
    ("STAT", "Immediately (STAT)"),
    ("PRN", "Pro re nata (As required)"),
    ("OTHER", "Other (Specify)"),
    ]


    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, blank=True, null=True)
    medicine_type = models.CharField(max_length=20, choices=MEDICINE_TYPE_CHOICES, default="other")
    route = models.CharField(max_length=20, choices=ROUTE_CHOICES, blank=True, null=True)
    duration = models.CharField(blank=True, null=True, help_text="Duration in days",choices=DURATION_FREQUENCY_CHOICES)
    is_liquid_injection = models.BooleanField(default=False, help_text="Only for injections: Check if this is a ready-to-use liquid injection")
    standard_dose_per_kg = models.FloatField(help_text="Standard dose per kg (mg/kg/day)", null=True, blank=True)
    tablet_strength= models.FloatField(help_text="Standard dose per kg (mg/kg/day)", null=True, blank=True)
    concentration_mg_per_ml = models.FloatField(help_text="Concentration of the medicine (mg/mL)", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_medicine_type_display()})"
    

class Prescription(models.Model):
    DOSE_FREQUENCY_CHOICES = [
        ("OD", "Once a day (OD)"),
        ("BD", "Twice a day (BD)"),
        ("TDS", "Three times a day (TDS)"),
        ("QID", "Four times a day (QID)"),
        ("SOS", "As needed (SOS)"),
        ("STAT", "Immediately (STAT)"),
        ("OTHER", "Other"),
    ]
    ipd = models.ForeignKey(IPD, on_delete=models.CASCADE, related_name="prescriptions")
    dose_frequency = models.CharField(max_length=10, choices=DOSE_FREQUENCY_CHOICES, default="OD")
    concentration_mg_per_ml = models.FloatField(help_text="Concentration of the medicine (mg/mL)", null=True, blank=True)
    medication = models.CharField(max_length=255)
    medication_fk = models.ForeignKey(Medicine, on_delete=models.CASCADE, null=True, blank=True)
    dosage = models.CharField(max_length=100)
    timing = models.DateTimeField()

    def __str__(self):
        return f"Prescription for {self.ipd.patient.user.full_name} - {self.medication} ({self.dosage}) at {self.timing})"
    
    
class MedicineVial(models.Model):
    medicine = models.ForeignKey(Medicine, related_name='vials', on_delete=models.CASCADE)
    strength_mg = models.FloatField(help_text="Total mg in the vial (e.g., 500)")
    volume_ml = models.FloatField(help_text="Total mL in the vial (e.g., 2)")
    
    @property
    def concentration(self):
        return round(self.strength_mg / self.volume_ml, 2)  # mg per mL

    def __str__(self):
        return f"{self.medicine.name} {int(self.strength_mg)}mg/{self.volume_ml}mL"

class Diluent(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        
        return self.name

class Vial(models.Model):
    VIAL_TYPE_CHOICES = [
        ("mg", "mg"),
        ("ml", "mL"),
    ]

    size = models.FloatField(help_text="Size of the vial (e.g., 1000, 500, 250, etc.)")
    unit = models.CharField(max_length=2, choices=VIAL_TYPE_CHOICES, default="mg", help_text="Unit (mg or mL)")


    def get_vial_size_in_ml(self):
        if self.unit == "mg":
            return self.size / 100  # Convert mg to mL (1 mL = 100 mg)
        return self.size
    
    def __str__(self):
        return f"{self.size} {self.get_unit_display()}"


class NICUMedicationRecord(models.Model):
    ROUTE_CHOICES = [
        ("IV", "Intravenous (IV)"),
        ("IM", "Intramuscular (IM)"),
        ("SC", "Subcutaneous (SC)"),
        ("PO", "Oral (PO)"),
    ]

    DOSE_FREQUENCY_CHOICES = [
        ("OD", "Once a day (OD)"),
        ("BD", "Twice a day (BD)"),
        ("TDS", "Three times a day (TDS)"),
        ("QID", "Four times a day (QID)"),
        ("SOS", "As needed (SOS)"),
        ("STAT", "Immediately (STAT)"),
        ("OTHER", "Other"),
    ]

    patient = models.ForeignKey("Patient", on_delete=models.CASCADE)
    ipd_admission = models.ForeignKey("IPD", on_delete=models.CASCADE, related_name="nicu_medications", null=True)
    prescription = models.ForeignKey("Prescription", on_delete=models.CASCADE, related_name="Prescription", null=True)
    medicine = models.ForeignKey("Medicine", on_delete=models.CASCADE)
    diluent = models.ForeignKey("Diluent", on_delete=models.SET_NULL, null=True, blank=True)
    vial = models.ForeignKey("Vial", on_delete=models.SET_NULL, null=True, blank=True)
    medicine_vial = models.ForeignKey("MedicineVial", on_delete=models.SET_NULL, null=True, blank=True)
    route = models.CharField(max_length=10, choices=ROUTE_CHOICES)
    dilution_volume = models.FloatField(help_text="User-defined dilution volume (mL)", null=True, blank=True)

    # Calculated Fields
    calculated_dose_per_day = models.FloatField(editable=False, null=True)
    calculated_dose_per_dose = models.FloatField(editable=False, null=True)
    calculated_diluent_volume = models.FloatField(editable=False, null=True)
    calculated_infusion_rate = models.FloatField(editable=False, null=True)
    total_volume_ml = models.FloatField(editable=False, null=True)
    calculated_dose_per_hour = models.FloatField(editable=False, null=True)
    calculated_mg_per_kg_per_dose = models.FloatField(editable=False, null=True)
    calculated_ml_per_kg_per_dose = models.FloatField(editable=False, null=True)
    calculated_ml = models.FloatField(editable=False, null=True)
    frequency_of_dose = models.IntegerField(blank=True, null=True)
    frequency_of_dose_given = models.FloatField(editable=False, null=True)
    take_from_medicine_vial = models.FloatField(editable=False, null=True)
    calculated_dose_per_dose_ml = models.FloatField(editable=False, null=True)
    dose_per_day_mg = models.FloatField(editable=False, null=True)
    take = models.FloatField(editable=False, null=True)
    set_in_mchine = models.FloatField(editable=False,null=True)
    dose_frequency = models.CharField(max_length=10, choices=DOSE_FREQUENCY_CHOICES, default="OD")
    other_frequency = models.CharField(max_length=100, blank=True, null=True)
    sign = models.CharField(max_length=100, help_text="Doctor's Signature",null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def get_dose_frequency_per_day(self):
        """Returns the number of times the dose is given per day based on frequency."""
        frequency_map = {
            "OD": 1, "BD": 2, "TDS": 3, "QID": 4, "SOS": 1, "STAT": 1, "OTHER": 1
        }
        return frequency_map.get(self.dose_frequency, 1)

    
    def clean(self):
        """Validate inputs before saving."""
        if not self.patient or not self.patient.weight or self.patient.weight <= 0:
            raise ValidationError("Patient weight must be provided and greater than zero.")
        if not self.medicine:
            raise ValidationError("Medicine must be selected.")
        if self.route == "IV" and not self.get_dose_frequency_per_day():
            raise ValidationError("Frequency is required for IV medications.")

    def save(self, *args, **kwargs): 
        try:
            
            print("🚀 Starting save method")
            self.clean()
            print("✅ Cleaned successfully")
            print(f"medicine_vial value before saving: {self.medicine_vial}")

            patient_weight = self.patient.weight
            print(f"👶 Patient weight: {patient_weight} kg")

            daily_doses = self.get_dose_frequency_per_day()
            print(f"📅 Daily doses: {daily_doses}")

            self.calculated_dose_per_day = round(Decimal(patient_weight) * Decimal(self.medicine.standard_dose_per_kg), 2)
            print(f"💊 Dose per day: {self.calculated_dose_per_day} mg/day")

            self.calculated_dose_per_dose = round(self.calculated_dose_per_day / daily_doses, 2)
            print(f"💉 Dose per dose: {self.calculated_dose_per_dose} mg/dose")

            if patient_weight > 0:
                self.calculated_mg_per_kg_per_dose = round(self.calculated_dose_per_dose / patient_weight, 2)
                print(f"📐 mg/kg/dose: {self.calculated_mg_per_kg_per_dose}")
            
            if self.medicine.medicine_type in ["syrup", "suspension", "oral"]:
                print(f"⛔ Skipping dilution calculations for {self.medicine.medicine_type}")
                self.vial = None
                self.calculated_dose_per_dose_ml = None
                self.dilution_volume = None
                self.diluent = None
                self.calculated_ml = None
                self.calculated_infusion_rate = None
                self.frequency_of_dose = None
                self.frequency_of_dose_given = None
                self.set_in_mchine = None
                self.calculated_dose_per_dose = self.calculated_dose_per_day
                self.calculated_mg_per_kg_per_dose = round(self.calculated_dose_per_dose / patient_weight, 2)

            else:
                if self.vial:
                    if self.vial.unit == "mg":
                        self.calculated_dose_per_dose_ml = self.vial.size / 100
                        print(f"🧪 Vial size: {self.vial.size} mg")
                        print(f"🧮 Dose per dose in mL: {self.calculated_dose_per_dose_ml}")
                else:
                    print("⚠️ No vial selected")

                self.take = self.calculated_dose_per_day / 100
                print(f"📤 Total daily take: {self.take} units")

                if self.medicine.medicine_type == "injection":
                    if self.medicine.is_liquid_injection:
                        print("💉 Liquid injection – skipping dilution")
                        # self.dilution_volume = None
                        # self.diluent = None
                        # self.vial = None
                        # self.take = None
                        # self.calculated_dose_per_dose_ml = None
                        # print("medicne vial",self.medicine_vial)
                        print("Selected vial:",self.medicine_vial)

                        self.required_dose = self.calculated_dose_per_day
                        print(f"💊 Required dose per dose: {self.required_dose} mg")
                        if self.medicine_vial:
                            print(f"Selected vial: {self.medicine_vial}")
                        else:
                            print("No vial selected.")

                        # Fetch concentration from the selected vial (either Medicine or MedicineVial)
                        if self.medicine_vial:
                            # self.take = None
                            concentration_per_ml = self.medicine_vial.concentration  # Concentration from the selected vial
                            concentration_in_point = concentration_per_ml/10
                            self.take_from_medicine_vial = self.required_dose/Decimal(concentration_in_point)
                            print(f"💉 Concentration per ml from vial: {concentration_per_ml} mg/ml")
                            print(f"💉 concentration_in_point per ml from vial: {concentration_in_point} mg/ml")
                            print(f"💉 take_from_medicine_vial : {self.take_from_medicine_vial} mg/ml")
                            print(f"🧪 Draw {self.take_from_medicine_vial:.2f} points (i.e., {self.take_from_medicine_vial * Decimal('0.1'):.2f} mL) from vial")
                            

                        else:
                            concentration_per_ml = self.medicine.concentration_mg_per_ml  # Fallback to the concentration in Medicine
                            print(f"💉 Fallback concentration per ml from Medicine: {concentration_per_ml} mg/ml")

                        # Step 2: Calculate the required volume (based on vial concentration)
                        # Use the concentration to determine the required volume to be administered
                        required_ml = round((Decimal(self.required_dose) * Decimal('0.1')) / Decimal(concentration_per_ml), 2)  # Adjusted for concentration
                        print(f"🧪 Required volume from vial: {required_ml} ml")
                        
                        # Step 3: Calculate the diluent volume (if applicable)
                        if self.dilution_volume:
                            self.calculated_ml = float(self.take_from_medicine_vial) + self.dilution_volume  # Add dilution volume to the required volume
                            print(f"💧 Volume after dilution: {self.calculated_ml} ml")
                        else:
                            self.calculated_ml = self.take_from_medicine_vial  # If no dilution, just use the required volume
                            print(f"💧 Volume to administer: {self.calculated_ml} ml")



                        self.calculated_ml_day = round(float(self.calculated_dose_per_dose) / (self.medicine_vial.concentration or 1), 2)
                        print(f"Calculated mL/day: {self.calculated_ml_day}")
                        self.calculated_ml = self.calculated_ml_day/24
                        print(f"Calculated mL/hour: {self.calculated_ml}")
                        self.after_dilution = float(self.dilution_volume) + float(self.calculated_ml)
                        print(f"Calculated mL/hour after_dilution: {self.after_dilution}")
                        self.frequency_of_dose_given = round(self.calculated_ml / (self.frequency_of_dose or 1), 2)
                        print(f"Frequency of dose given (mL): {self.frequency_of_dose_given}")
                        self.set_in_mchine = round(self.frequency_of_dose_given * 60, 2)
                        print(f"Infusion rate (mL/hour) set in machine: {self.set_in_mchine}")
                        self.calculated_infusion_rate = round(self.after_dilution / 24, 2)
                        print(f"Infusion rate (mL/hour) calculated_infusion_rate: {self.calculated_infusion_rate}")
                        self.frequency_of_dose_given = round(self.calculated_infusion_rate / (self.frequency_of_dose or 1), 2)
                        self.set_in_mchine = round(self.frequency_of_dose_given * 60, 2)
                    else:
                        self.calculated_ml = (self.dilution_volume) + float((self.calculated_dose_per_dose / 100))
                        self.frequency_of_dose_given = round(self.calculated_ml / (self.frequency_of_dose or 1), 2)
                        self.set_in_mchine = round(self.frequency_of_dose_given * 60, 2)

                    print(f"💧 Calculated ML: {self.calculated_ml}")
                    print(f"🕒 Frequency of dose given: {self.frequency_of_dose_given}")
                    print(f"⚙️ Set in machine: {self.set_in_mchine}")

                elif self.medicine.medicine_type == "drop":
                    DROP_VOLUME_ML = 0.05
                    if self.medicine.concentration_mg_per_ml:
                        self.calculated_ml = round(self.calculated_dose_per_dose / self.medicine.concentration_mg_per_ml, 2)
                        self.calculated_drops = round(self.calculated_ml / DROP_VOLUME_ML)
                    else:
                        self.calculated_ml = 0
                        self.calculated_drops = 0
                    print(f"💧 Drops: {self.calculated_drops}")

                elif self.medicine.medicine_type == "tablet":
                    self.calculated_tablets = round(self.calculated_dose_per_dose / (self.medicine.concentration_mg_per_ml or 1), 1)
                    print(f"💊 Tablets per dose: {self.calculated_tablets}")

                elif self.medicine.name.lower() in ['dopamine', 'dobutamine']:
                    dose_mcg_per_kg_min = self.medicine.standard_dose_per_kg
                    weight_kg = patient_weight
                    concentration_mg_per_ml = self.medicine.concentration_mg_per_ml or 5
                    concentration_mcg_per_ml = concentration_mg_per_ml * 1000

                    infusion_rate_ml_hr = dose_mcg_per_kg_min * weight_kg * 1.444
                    self.calculated_infusion_rate = round(infusion_rate_ml_hr, 2)
                    self.calculated_ml = round(infusion_rate_ml_hr * 24, 2)
                    self.set_in_mchine = round(self.calculated_ml, 2)

                    print(f"🧪 {self.medicine.name} infusion rate: {self.calculated_infusion_rate} mL/hr")
                    print(f"📦 24-hour volume: {self.calculated_ml}")

                # Final infusion rate for IV if not set already
                if self.route == "IV":
                    if not self.calculated_infusion_rate and self.calculated_ml:
                        self.calculated_infusion_rate = round(self.calculated_ml / 60, 2)
                        print(f"⚗️ Final IV infusion rate: {self.calculated_infusion_rate}")
                    elif not self.calculated_ml:
                        self.calculated_infusion_rate = 0
                        print("⚠️ No ML calculated, infusion rate set to 0")

            print("✅ Save completed. Saving to database...")
            super().save(*args, **kwargs)
            print("🧾 Saved successfully")

        except Exception as e:
            print(f"❌ Error in save(): {str(e)}")
            raise  # Optional: re-raise for visibility in logs or debugging



def __str__(self):
    return f"{self.medicine.name} ({self.get_route_display()}) - {self.timestamp}"






class FluidRequirement(models.Model):
    patient = models.ForeignKey("Patient", on_delete=models.CASCADE, null=True)
    ipd_admission = models.ForeignKey("IPD", on_delete=models.CASCADE, related_name="fluid_requirements", null=True)
    medicine = models.ForeignKey(
        "Medicine",
        on_delete=models.CASCADE,
        limit_choices_to={"medicine_type": "fluid"},
        related_name="fluid_requirements",
        null=True
    )

    # These are auto-filled
    birth_weight_category = models.CharField(max_length=20, choices=[("≤1500g", "≤1500g"), (">1500g", ">1500g")])
    day_after_birth = models.IntegerField()
    fluid_ml_per_kg_per_day = models.FloatField()
    calculated_ml = models.FloatField(null=True, blank=True)
    calculated_ml_hr = models.FloatField(null=True, blank=True,editable=False)

    def save(self, *args, **kwargs):
        patient = self.ipd_admission.patient

        weight = patient.weight
        dob = patient.date_of_birth
        days_after_birth = (timezone.now().date() - dob).days

        # Determine weight category
        weight_category = "≤1500g" if weight <= 1.5 else ">1500g"

        # After 6 days, default to 150 mL/kg/day
        if days_after_birth > 6:
            ml_per_kg = 150
        else:
            # Get reference fluid value (no IPD or medicine assigned)
            reference = FluidRequirement.objects.filter(
                birth_weight_category=weight_category,
                day_after_birth=days_after_birth,
                ipd_admission__isnull=True,
                medicine__isnull=True
            ).first()
            ml_per_kg = reference.fluid_ml_per_kg_per_day if reference else 150  # fallback
            print("refrence",reference)
            print("ml_per_kg",ml_per_kg)

        self.birth_weight_category = weight_category
        self.day_after_birth = days_after_birth
        self.fluid_ml_per_kg_per_day = ml_per_kg
        self.calculated_ml = round(float(ml_per_kg) * float(weight), 2)
        self.calculated_ml_hr = round(self.calculated_ml / 24, 2)

        super().save(*args, **kwargs)

    def __str__(self):
        if self.ipd_admission and self.ipd_admission.patient and self.ipd_admission.patient.user:
            patient_name = self.ipd_admission.patient.user.full_name or "Unnamed Patient"
        else:
            patient_name = "Unknown Patient"
        
        return f"{patient_name} - Day {self.day_after_birth}"


# FluidRequirement.objects.bulk_create([
#     # For preterm neonates birth weight ≤1500g
#     FluidRequirement(birth_weight_category="≤1500g", day_after_birth=1, fluid_ml_per_kg_per_day=80),
#     FluidRequirement(birth_weight_category="≤1500g", day_after_birth=2, fluid_ml_per_kg_per_day=90),
#     FluidRequirement(birth_weight_category="≤1500g", day_after_birth=3, fluid_ml_per_kg_per_day=100),
#     FluidRequirement(birth_weight_category="≤1500g", day_after_birth=4, fluid_ml_per_kg_per_day=120),
#     FluidRequirement(birth_weight_category="≤1500g", day_after_birth=5, fluid_ml_per_kg_per_day=140),
#     FluidRequirement(birth_weight_category="≤1500g", day_after_birth=6, fluid_ml_per_kg_per_day=150),
    
#     # For term/preterm neonates birth weight >1500g
#     FluidRequirement(birth_weight_category=">1500g", day_after_birth=1, fluid_ml_per_kg_per_day=60),
#     FluidRequirement(birth_weight_category=">1500g", day_after_birth=2, fluid_ml_per_kg_per_day=80),
#     FluidRequirement(birth_weight_category=">1500g", day_after_birth=3, fluid_ml_per_kg_per_day=100),
#     FluidRequirement(birth_weight_category=">1500g", day_after_birth=4, fluid_ml_per_kg_per_day=120),
#     FluidRequirement(birth_weight_category=">1500g", day_after_birth=5, fluid_ml_per_kg_per_day=140),
#     FluidRequirement(birth_weight_category=">1500g", day_after_birth=6, fluid_ml_per_kg_per_day=160),
import uuid
import os
import logging
from decimal import Decimal
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
    weight = models.PositiveBigIntegerField(blank=True,null=True)
    email = models.EmailField(unique=True, blank=True, null=True)

    # Medical Information
    allergies = models.TextField(blank=True, null=True)  # Known allergies
    medical_history = models.TextField(blank=True, null=True)  # Past medical history
    current_medications = models.TextField(blank=True, null=True)  # Current medications

    # Emergency Contact Information
    emergency_contact_name = models.CharField(max_length=255, blank=True, null=True)
    emergency_contact_number = models.CharField(max_length=15, blank=True, null=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True, null=True, choices=RELATIONSHIP_CHOICES)

    # Accompanying Person Details (Replaces Guarantor)
    accompanying_person_name = models.CharField(max_length=255, blank=True, null=True)
    accompanying_person_contact = models.CharField(max_length=15, blank=True, null=True)
    accompanying_person_relationship = models.CharField(max_length=50, blank=True, null=True, choices=RELATIONSHIP_CHOICES)
    accompanying_person_address = models.TextField(blank=True, null=True)

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

    def save(self, *args, **kwargs):
        if isinstance(self.payment_amount, str):
            try:
                self.payment_amount = Decimal(self.payment_amount)
            except ValueError:
                self.payment_amount = Decimal(0)  # Set to 0 if conversion fails
        
        super().save(*args, **kwargs)

        if self.payment_status == 'paid' and self.payment_amount > 0:
            AccountingRecord.objects.create(
                transaction_type='income',
                source='opd',
                amount=self.payment_amount,
                description=f"OPD payment for {self.patient.user.full_name}",
                patient=self.patient,
            )

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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        AccountingRecord.objects.create(
            transaction_type='income',
            source='IPD',
            amount=self.cost,
            description=f"{self.get_category_display()} expense for {self.patient.user.full_name}",
            patient=self.patient,
        )

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
        ("other", "Other"),
    ]

    name = models.CharField(max_length=100, unique=True)
    medicine_type = models.CharField(max_length=20, choices=MEDICINE_TYPE_CHOICES, default="other")
    # Standard dose is given in mg/kg/day (e.g., 5 mg/kg/day)
    standard_dose_per_kg = models.FloatField(help_text="Standard dose per kg (mg/kg/day)", null=True)
    # For liquids, the concentration tells how many mg per mL
    concentration_mg_per_ml = models.FloatField(help_text="Concentration of the medicine (mg/mL)", null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.get_medicine_type_display()})"


class Diluent(models.Model):
    name = models.CharField(max_length=100, unique=True)
    compatible_medicine_types = models.ManyToManyField(Medicine, related_name="compatible_diluents", blank=True)
    standard_volume_per_kg = models.FloatField(help_text="Standard diluent volume per kg (mL/kg)", null=True)

    def __str__(self):
        return self.name



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
    route = models.CharField(max_length=10, choices=ROUTE_CHOICES)
    medicine = models.ForeignKey("Medicine", on_delete=models.CASCADE)
    diluent = models.ForeignKey("Diluent", on_delete=models.SET_NULL, null=True, blank=True)
    dilution_volume = models.FloatField(help_text="User-defined dilution volume (mL)", null=True, blank=True)

    # Calculated Fields:
    calculated_dose_per_day = models.FloatField(editable=False, null=True)
    calculated_dose_per_dose = models.FloatField(editable=False, null=True)
    calculated_volume_per_day = models.FloatField(editable=False, null=True)
    calculated_volume_per_dose = models.FloatField(editable=False, null=True)
    calculated_diluent_volume = models.FloatField(editable=False, null=True)
    calculated_infusion_rate = models.FloatField(editable=False, null=True)
    total_volume_ml = models.FloatField(editable=False, null=True)
    calculated_dose_per_hour = models.FloatField(editable=False, null=True)
    calculated_mg_per_kg_per_dose = models.FloatField(editable=False, null=True)
    calculated_ml_per_kg_per_dose = models.FloatField(editable=False, null=True)

    duration = models.FloatField(help_text="Duration of administration (hours)", null=True)
    dose_frequency = models.CharField(max_length=10, choices=DOSE_FREQUENCY_CHOICES, default="OD")
    other_frequency = models.CharField(max_length=100, blank=True, null=True)
    sign = models.CharField(max_length=100, help_text="Doctor's Signature")
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
        if self.route in ["IV"] and not self.duration:
            raise ValidationError("Duration is required for IV medications.")

    def save(self, *args, **kwargs):
        """Perform pediatric dose calculations before saving."""
        self.clean()  # Validate inputs

        patient_weight = self.patient.weight
        daily_doses = self.get_dose_frequency_per_day()

        # -------------------------------------------
        # Calculate Total Daily Dose (mg/day)
        # -------------------------------------------
        if self.medicine.standard_dose_per_kg:
            self.calculated_dose_per_day = round(patient_weight * self.medicine.standard_dose_per_kg, 2)
        else:
            self.calculated_dose_per_day = 0

        # -------------------------------------------
        # Calculate Per Dose Amount (mg/dose)
        # -------------------------------------------
        if daily_doses > 0:
            self.calculated_dose_per_dose = round(self.calculated_dose_per_day / daily_doses, 2)
        else:
            self.calculated_dose_per_dose = 0

        # -------------------------------------------
        # Calculate Total Volume Per Day (mL/day)
        # -------------------------------------------
        if self.medicine.concentration_mg_per_ml:
            self.calculated_volume_per_day = round(self.calculated_dose_per_day / self.medicine.concentration_mg_per_ml, 2)
        else:
            self.calculated_volume_per_day = 0

        # -------------------------------------------
        # Calculate Volume Per Dose (mL/dose)
        # -------------------------------------------
        if daily_doses > 0:
            self.calculated_volume_per_dose = round(self.calculated_volume_per_day / daily_doses, 2)
        else:
            self.calculated_volume_per_dose = 0

        # -------------------------------------------
        # Handle Different Routes
        # -------------------------------------------
        if self.route in ["IV"]:
            # Infusion Rate Calculation
            if self.duration:
                self.calculated_infusion_rate = round(self.calculated_volume_per_day / self.duration, 2)
            else:
                self.calculated_infusion_rate = 0

            # Dilution Volume
            if self.calculated_infusion_rate and self.duration:
                self.dilution_volume = round(self.calculated_infusion_rate * self.duration, 2)
            else:
                self.dilution_volume = self.calculated_volume_per_day

        elif self.route in ["IM", "SC"]:
            # IM & SC do not have an infusion rate
            self.calculated_infusion_rate = 0  

            # Use the provided dilution volume or assume undiluted
            self.calculated_diluent_volume = round(self.dilution_volume, 2) if self.dilution_volume else 0 

            # Ensure safe injection volume limits
            if self.calculated_volume_per_dose > 5 and self.route == "IM":
                raise ValidationError("IM injection volume exceeds 5 mL limit per site.")
            elif self.calculated_volume_per_dose > 1.5 and self.route == "SC":
                raise ValidationError("SC injection volume exceeds 1.5 mL limit per site.")

        # -------------------------------------------
        # Calculate Dose Per Hour (mg/hr)
        # -------------------------------------------
        if self.duration:
            self.calculated_dose_per_hour = round(self.calculated_dose_per_day / self.duration, 2)
        else:
            self.calculated_dose_per_hour = 0

        # -------------------------------------------
        # Calculate mg per kg per dose (mg/kg/dose)
        # -------------------------------------------
        if patient_weight and daily_doses > 0:
            self.calculated_mg_per_kg_per_dose = round(self.medicine.standard_dose_per_kg / daily_doses, 2)
        else:
            self.calculated_mg_per_kg_per_dose = 0

        # -------------------------------------------
        # Calculate mL per kg per dose (mL/kg/dose)
        # -------------------------------------------
        if self.medicine.concentration_mg_per_ml and daily_doses > 0:
            self.calculated_ml_per_kg_per_dose = round((self.medicine.standard_dose_per_kg / daily_doses) / self.medicine.concentration_mg_per_ml, 2)
        else:
            self.calculated_ml_per_kg_per_dose = 0

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.medicine.name} ({self.get_route_display()}) - {self.timestamp}"

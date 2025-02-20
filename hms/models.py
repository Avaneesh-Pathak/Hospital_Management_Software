from django.db import models
from django.utils.timezone import now
from django.contrib.auth.models import AbstractUser, Group, Permission

# Custom User Model (if needed)
class CustomUser(AbstractUser):
    user_type_choices = (
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
        ('admin', 'Admin'),
    )
    user_type = models.CharField(max_length=10, choices=user_type_choices, default='patient')

    groups = models.ManyToManyField(Group, related_name="customuser_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="customuser_permissions", blank=True)

    def __str__(self):
        return self.username

# Patient Model
class Patient(models.Model):
    created_at = models.DateTimeField(default=now)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    contact_number = models.CharField(max_length=15)
    address = models.TextField()
    medical_history = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.user.username

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
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('completed', 'Completed')], default='pending')

    def __str__(self):
        return f"Appointment with {self.doctor} on {self.date}"

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

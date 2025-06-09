from django.contrib import admin
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth import get_user_model
from django.template.response import TemplateResponse
from django.urls import path
from django.shortcuts import render
from django.utils.timezone import now
from datetime import datetime, timedelta
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate

# Import your models
from .models import (
    Patient, Asset, License, Maintenance, Doctor, Appointment, 
    AccountingRecord, EmergencyCase, IPD, OPD, BillingBase, 
    Room, Expense, Employee, PatientReport, Daybook, Balance, NICUVitals, 
    NICUMedicationRecord, Medicine, Diluent, Vial, FluidRequirement,
    MedicineVial, IPDBilling, OPDBilling, Payment, CustomUser
)

# Get custom user model
User = get_user_model()

# Define custom admin site
class CustomAdminSite(admin.AdminSite):
    site_header = "Hospital Management Dashboard"
    site_title = "Admin Panel"
    index_title = "Welcome to the Hospital Admin"

# Instantiate custom admin site
admin_site = CustomAdminSite(name='custom_admin')

# Register models with the custom admin
admin_site.register(User, UserAdmin)
admin_site.register(Group, GroupAdmin)
admin_site.register(Permission)

# Hospital Management Models
admin_site.register(Patient)
admin_site.register(Doctor)
admin_site.register(Appointment)
admin_site.register(EmergencyCase)
admin_site.register(IPD)
admin_site.register(OPD)
admin_site.register(OPDBilling)
admin_site.register(IPDBilling)
admin_site.register(Payment)
admin_site.register(Room)
admin_site.register(Asset)
admin_site.register(License)
admin_site.register(Maintenance)
admin_site.register(Expense)
admin_site.register(Employee)
admin_site.register(PatientReport)
admin_site.register(AccountingRecord)
admin_site.register(Daybook)
admin_site.register(Balance)
admin_site.register(NICUVitals)
admin_site.register(NICUMedicationRecord)
admin_site.register(Medicine)
admin_site.register(Diluent)
admin_site.register(Vial)
admin_site.register(MedicineVial)
admin_site.register(FluidRequirement)

# Optionally skip BillingBase if it's abstract or not needed
# admin_site.register(BillingBase)

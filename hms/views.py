# Import Statements
import io
import csv
import base64
import qrcode
import datetime
import logging
from io import BytesIO
from datetime import date
from xhtml2pdf import pisa
from decimal import Decimal
from django.db import models
from itertools import groupby
from django.views import View
from django.db.models import Q
from operator import attrgetter
from django.http import Http404
from django.utils import timezone
from collections import defaultdict
from reportlab.pdfgen import canvas
from django.http import JsonResponse
from django.http import FileResponse
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.http import JsonResponse
from reportlab.pdfgen import canvas
from django.shortcuts import render
from django.contrib import messages
from django.utils.timezone import now
from django.db.models import Count, Sum
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from django.utils.timezone import localdate
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.utils.timezone import localtime
from django.contrib.auth.models import Group
from django.urls import reverse_lazy, reverse
from django.utils.dateparse import parse_time
from django.template.loader import get_template
from django.db.models.functions import TruncDate
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.storage import default_storage
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import ListView, CreateView, UpdateView,DeleteView

# Import Models and Forms
from .models import (
    CustomUser, Patient, Doctor, Appointment,
    BillingBase, OPDBilling, IPDBilling, BillingItem, Payment, Expense,
    EmergencyCase, OPD, IPD, Employee, Room, PatientReport, Prescription,
    License, Asset, Maintenance, AccountingRecord, Daybook, Balance,
    PatientTransfer, NICUVitals, NICUMedicationRecord, Medicine, Diluent,
    Vial, FluidRequirement, MedicineVial,Nurse, Staff
)

from .forms import (
    PatientRegistrationForm, ExpenseForm, OPDBillingForm, IPDBillingForm,
    BillingItemForm, PaymentForm, OPDForm, DoctorForm, EmployeeForm,
    RoomForm, EmergencyCaseForm, ProfileUpdateForm, PatientReportForm,
    PrescriptionForm, LicenseForm, AssetForm, MaintenanceForm,
    BalanceUpdateForm, DaybookEntryForm, NICUVitalsForm, NICUMedicationRecordForm,
    MedicineForm, DiluentForm, VialForm, NICUFluidForm, IPDForm, MedicineVialFormSet
)


# Logger Setup
logger = logging.getLogger(__name__)

# Authentication Views
# Role-Group mapping for consistency and reuse
ROLE_GROUP_MAP = {
    'admin': 'Admin',
    'doctor': 'Doctor',
    'nurse': 'Nurse',
    'staff': 'Staff',
    'patient': 'Patient',
}

def signup(request):
    if request.method == "POST":
        full_name = request.POST.get('full_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        role = request.POST.get('role', '').lower()

        # Basic validation
        if not all([full_name, username, email, password, confirm_password]):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'hms/auth/signup.html')

        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, 'hms/auth/signup.html')

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already taken!")
            return render(request, 'hms/auth/signup.html')

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return render(request, 'hms/auth/signup.html')

        # Create user and set password properly
        user = CustomUser(username=username, email=email, full_name=full_name, role=role if role in ROLE_GROUP_MAP else 'staff')
        user.set_password(password)
        user.save()

        # Add user to group and create related profile models
        if role in ROLE_GROUP_MAP:
            group_name = ROLE_GROUP_MAP[role]
            group, _ = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)

            # Create role-specific profiles
            if role == 'doctor':
                Doctor.objects.create(user=user)
            elif role == 'nurse':
                Nurse.objects.create(user=user)
            elif role == 'staff':
                Staff.objects.create(user=user)

        messages.success(request, "Account created successfully! Please log in.")
        return redirect('login')

    return render(request, 'hms/auth/signup.html')


def user_login(request):
    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

            # Role-based redirection
            if user.is_superuser or user.role == 'admin':
                return redirect('dashboard')
            elif user.groups.filter(name='Doctor').exists():
                return redirect('doctor_dashboard')
            elif user.groups.filter(name='Nurse').exists():
                return redirect('nurse_dashboard')
            elif user.groups.filter(name='Staff').exists():
                return redirect('staff_dashboard')
            elif user.groups.filter(name='Patient').exists():
                return redirect('patient_dashboard')
            else:
                return redirect('hms/dashboard.html')

        messages.error(request, "Invalid username or password!")

    return render(request, 'hms/auth/login.html')

@login_required
def user_logout(request):
    logout(request)
    return redirect('login')

@login_required
def redirect_after_login(request):
    user = request.user
    if user.is_superuser or user.role == 'admin':
        return redirect('dashboard')
    elif user.groups.filter(name='Doctor').exists():
        return redirect('doctor_dashboard')
    elif user.groups.filter(name='Nurse').exists():
        return redirect('nurse_dashboard')
    elif user.groups.filter(name='Staff').exists():
        return redirect('staff_dashboard')
    elif user.groups.filter(name='Patient').exists():
        return redirect('patient_dashboard')
    else:
        return redirect('hms/dashboard.html')
    

# Decorator factory for group-based access control
def group_required(*group_names):
    def in_groups(user):
        return user.is_authenticated and (user.is_superuser or bool(user.groups.filter(name__in=group_names)))
    return user_passes_test(in_groups)

# Example role-based views using the decorator:
from django.utils import timezone
from datetime import timedelta
from collections import Counter
from django.db.models.functions import TruncDate
from django.db.models import Count
@login_required
@group_required('Doctor')
def doctor_dashboard(request):
    doctor = request.user.doctor

    # IPD
    ipd_patients = IPD.objects.filter(patient__assigned_doctor=doctor, discharge_date__isnull=True)

    # Appointments Today
    todays_appointments = Appointment.objects.filter(doctor=doctor, date=date.today()).order_by('time')

    # Last 7 days appointment stats
    seven_days_ago = timezone.now().date() - timedelta(days=6)
    appointments_last_7_days = (
        Appointment.objects.filter(doctor=doctor, date__gte=seven_days_ago)
        .annotate(day=TruncDate('date'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )

    # Prepare labels and counts for Chart.js
    appointment_chart_labels = []
    appointment_chart_counts = []
    for i in range(7):
        day = seven_days_ago + timedelta(days=i)
        appointment_chart_labels.append(day.strftime('%a'))  # Mon, Tue, etc.
        count = next((item['count'] for item in appointments_last_7_days if item['day'] == day), 0)
        appointment_chart_counts.append(count)

    # Vitals
    recent_vitals = NICUVitals.objects.filter(ipd__patient__assigned_doctor=doctor).order_by('-date', '-time')[:5]

    # Medications
    active_medications = NICUMedicationRecord.objects.filter(patient__assigned_doctor=doctor).order_by('-timestamp')[:10]

    # Group medication types for chart
    med_types = [med.medicine.medicine_type if med.medicine else 'Unknown' for med in active_medications]
    med_counter = Counter(med_types)
    med_chart_labels = list(med_counter.keys())
    med_chart_counts = list(med_counter.values())

    # Emergency
    emergency_cases = EmergencyCase.objects.filter(patient__assigned_doctor=doctor, status='Pending')

    context = {
        'doctor': doctor,
        'ipd_patients': ipd_patients,
        'todays_appointments': todays_appointments,
        'recent_vitals': recent_vitals,
        'active_medications': active_medications,
        'emergency_cases': emergency_cases,
        'appointment_chart_labels': appointment_chart_labels,
        'appointment_chart_counts': appointment_chart_counts,
        'med_chart_labels': med_chart_labels,
        'med_chart_counts': med_chart_counts,
    }

    return render(request, 'doctors/dashboard.html', context)


@login_required
@group_required('Nurse')
def nurse_dashboard(request):
    nurse = request.user.nurse_profile
    
    # Get assigned patients (IPD)
    assigned_ipd_patients = IPD.objects.filter(
        patient__assigned_doctor__isnull=False,
        discharge_date__isnull=True
    ).select_related('patient', 'room').order_by('-admitted_on')[:5]
    
    # Get recent OPD visits
    recent_opd_visits = OPD.objects.select_related(
        'patient', 'doctor'
    ).order_by('-visit_date')[:5]
    
    # Get emergency cases
    emergency_cases = EmergencyCase.objects.filter(
        status='Pending'
    ).select_related('patient').order_by('-admitted_on')[:5]
    
    # Get vitals needing attention (last 4 hours)
    four_hours_ago = timezone.now() - timedelta(hours=4)
    critical_vitals = NICUVitals.objects.filter(
        date__gte=four_hours_ago.date(),
        time__gte=four_hours_ago.time()
    ).select_related('ipd', 'ipd__patient').order_by('-date', '-time')[:5]
    
    # Get pending medications
    now = timezone.now()
    one_hour_from_now = now + timedelta(hours=1)
    pending_medications = Prescription.objects.filter(
        timing__gte=now,
        timing__lte=one_hour_from_now,
        # administered=False
    ).select_related('ipd', 'ipd__patient').order_by('timing')[:10]
    
    
    context = {
        'nurse': nurse,
        'assigned_ipd_patients': assigned_ipd_patients,
        'recent_opd_visits': recent_opd_visits,
        'emergency_cases': emergency_cases,
        'critical_vitals': critical_vitals,
        'pending_medications': pending_medications,
        # 'recent_activities': recent_activities,
        'current_time': now,
    }
    
    return render(request, 'hms/nurse/dashboard.html', context)

@login_required
@group_required('Staff')
def staff_dashboard(request):
    total_patients = Patient.objects.count()
    total_doctors = Doctor.objects.count()
    total_appointments = Appointment.objects.count()
    total_revenue = OPDBilling.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    today = datetime.today()
    warning_period = today + timedelta(days=30)
    emergency_cases_today = EmergencyCase.objects.filter(admitted_on__date=today).count()
    upcoming_appointments = Appointment.objects.filter(date__gte=now()).order_by('date')
    
    # Get patient registration trend for the last 7 days
    last_week = today - timedelta(days=6)
    patient_trend = (
        Patient.objects.filter(created_at__date__gte=last_week)
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    date_counts = {entry['date']: entry['count'] for entry in patient_trend}
    labels = []
    data = []
    days = 7
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days-1)

    for day in range(days):
        current_date = start_date + timedelta(days=day)
        labels.append(current_date.strftime('%Y-%m-%d'))
        data.append(date_counts.get(current_date, 0))
    # Room Statistics
    total_rooms = Room.objects.count()
    available_rooms_count = Room.objects.filter(is_available=True).count()  # Fixed
    booked_rooms = total_rooms - available_rooms_count  # Fixed

    room_type_data = {}
    room_type_counts = Room.objects.values('room_type').annotate(total=Count('id'))
    available_rooms = Room.objects.filter(is_available=True).values('room_type').annotate(available=Count('id'))

    for room in room_type_counts:
        total = room['total']
        available = next((r['available'] for r in available_rooms if r['room_type'] == room['room_type']), 0)
        percentage = (available / total) * 100 if total > 0 else 0
        room_type_data[room['room_type']] = {
                'total': total,
                'available': available,
                'percentage': round(percentage)
            }

    expiring_licenses = License.objects.filter(expiry_date__lte=warning_period, expiry_date__gte=today)
    expiring_assets = Asset.objects.filter(warranty_expiry__lte=warning_period, warranty_expiry__gte=today)
    due_maintenance = Maintenance.objects.filter(next_due_date__lte=warning_period, next_due_date__gte=today)
    recent_opd_bills = OPDBilling.objects.select_related('patient__user').order_by('-generated_date')[:5]
    recent_ipd_bills = IPDBilling.objects.select_related('patient__user').order_by('-generated_date')[:5]

    # Combine and sort by created_at
    recent_billings = sorted(
        chain(recent_opd_bills, recent_ipd_bills),
        key=lambda b: b.generated_date,
        reverse=True
    )[:5]
    context = {
        'now': now(),
        'total_patients': total_patients,
        'total_doctors': total_doctors,
        'total_appointments': total_appointments,
        'total_revenue': total_revenue,
        'emergency_cases_today': emergency_cases_today,
        'upcoming_appointments': upcoming_appointments,
        'daily_patient_labels':  json.dumps(labels),
        'daily_patient_data':  json.dumps(data),
        'total_rooms': total_rooms,
        'available_rooms_count': available_rooms_count,  # Fixed
        'booked_rooms': booked_rooms,  # Fixed
        'room_type_data': room_type_data,  # Dictionary of room counts & available rooms by type
        'expiring_licenses': expiring_licenses,
        'expiring_assets': expiring_assets,
        'due_maintenance': due_maintenance,
        'recent_billings': recent_billings,
    }

    return render(request, 'hms/employee/dashboard.html',context)

def patient_stats_api_staff(request):
    days = int(request.GET.get('days', 7))
    today = timezone.now().date()
    start_date = today - timedelta(days=days-1)

    data = (
        Patient.objects.filter(created_at__date__gte=start_date)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )

    labels = [d['day'].strftime('%Y-%m-%d') for d in data]
    counts = [d['count'] for d in data]

    return JsonResponse({'labels': labels, 'data': counts})


@login_required
@group_required('Admin')
def admin_dashboard(request):
    return render(request, 'hms/dashboard.html')



# Profile Views
@login_required
def profile_view(request):
    user = request.user  # Get the logged-in user
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect("profile")
    else:
        form = ProfileUpdateForm(instance=user)

    return render(request, "hms/patient/profile.html", {"form": form})

# Search Functionality
def search(request):
    query = request.GET.get('q')  # Get the search query from the URL
    results = {}

    if query:
        # Search across multiple models
        patients = Patient.objects.filter(
            Q(user__full_name__icontains=query) |
            Q(patient_code__icontains=query) |
            Q(contact_number__icontains=query) |
            Q(email__icontains=query)
        )

        doctors = Doctor.objects.filter(
            Q(user__full_name__icontains=query) |
            Q(specialization__icontains=query) |
            Q(contact_number__icontains=query)
        )

        appointments = Appointment.objects.filter(
            Q(patient__user__full_name__icontains=query) |
            Q(doctor__user__full_name__icontains=query) |
            Q(status__icontains=query)
        )

        ipds = IPD.objects.filter(
            Q(patient__user__full_name__icontains=query) |
            Q(room__room_number__icontains=query)
        )

        opds = OPD.objects.filter(
            Q(patient__user__full_name__icontains=query) |
            Q(doctor__user__full_name__icontains=query)
        )

        emergencies = EmergencyCase.objects.filter(
            Q(patient__user__full_name__icontains=query) |
            Q(emergency_type__icontains=query)
        )

        # Combine results into a dictionary
        results = {
            'patients': patients,
            'doctors': doctors,
            'appointments': appointments,
            'ipds': ipds,
            'opds': opds,
            'emergencies': emergencies,
        }

    return render(request, 'hms/search_results.html', {'results': results, 'query': query})

import json
from itertools import chain 
# Dashboard Views
@login_required
def dashboard(request):
    total_patients = Patient.objects.count()
    total_doctors = Doctor.objects.count()
    total_appointments = Appointment.objects.count()
    total_revenue = OPDBilling.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    today = datetime.today()
    warning_period = today + timedelta(days=30)
    emergency_cases_today = EmergencyCase.objects.filter(admitted_on__date=today).count()
    upcoming_appointments = Appointment.objects.filter(date__gte=now()).order_by('date')
    
    # Get patient registration trend for the last 7 days
    last_week = today - timedelta(days=6)
    patient_trend = (
        Patient.objects.filter(created_at__date__gte=last_week)
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    date_counts = {entry['date']: entry['count'] for entry in patient_trend}
    labels = []
    data = []
    days = 7
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days-1)

    for day in range(days):
        current_date = start_date + timedelta(days=day)
        labels.append(current_date.strftime('%Y-%m-%d'))
        data.append(date_counts.get(current_date, 0))
    # Room Statistics
    total_rooms = Room.objects.count()
    available_rooms_count = Room.objects.filter(is_available=True).count()  # Fixed
    booked_rooms = total_rooms - available_rooms_count  # Fixed

    room_type_data = {}
    room_type_counts = Room.objects.values('room_type').annotate(total=Count('id'))
    available_rooms = Room.objects.filter(is_available=True).values('room_type').annotate(available=Count('id'))

    for room in room_type_counts:
        total = room['total']
        available = next((r['available'] for r in available_rooms if r['room_type'] == room['room_type']), 0)
        percentage = (available / total) * 100 if total > 0 else 0
        room_type_data[room['room_type']] = {
                'total': total,
                'available': available,
                'percentage': round(percentage)
            }

    expiring_licenses = License.objects.filter(expiry_date__lte=warning_period, expiry_date__gte=today)
    expiring_assets = Asset.objects.filter(warranty_expiry__lte=warning_period, warranty_expiry__gte=today)
    due_maintenance = Maintenance.objects.filter(next_due_date__lte=warning_period, next_due_date__gte=today)
    recent_opd_bills = OPDBilling.objects.select_related('patient__user').order_by('-generated_date')[:5]
    recent_ipd_bills = IPDBilling.objects.select_related('patient__user').order_by('-generated_date')[:5]

    # Combine and sort by created_at
    recent_billings = sorted(
        chain(recent_opd_bills, recent_ipd_bills),
        key=lambda b: b.generated_date,
        reverse=True
    )[:5]
    context = {
        'now': now(),
        'total_patients': total_patients,
        'total_doctors': total_doctors,
        'total_appointments': total_appointments,
        'total_revenue': total_revenue,
        'emergency_cases_today': emergency_cases_today,
        'upcoming_appointments': upcoming_appointments,
        'daily_patient_labels':  json.dumps(labels),
        'daily_patient_data':  json.dumps(data),
        'total_rooms': total_rooms,
        'available_rooms_count': available_rooms_count,  # Fixed
        'booked_rooms': booked_rooms,  # Fixed
        'room_type_data': room_type_data,  # Dictionary of room counts & available rooms by type
        'expiring_licenses': expiring_licenses,
        'expiring_assets': expiring_assets,
        'due_maintenance': due_maintenance,
        'recent_billings': recent_billings,
    }

    return render(request, 'hms/dashboard.html', context)

def patient_stats_api(request):
    days = int(request.GET.get('days', 7))
    today = datetime.today()
    start_date = today - timedelta(days=days)

    data = (
        Patient.objects.filter(created_at__gte=start_date)
        .extra(select={'day': 'DATE(created_at)'})
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )

    labels = [str(d['day']) for d in data]
    counts = [d['count'] for d in data]

    return JsonResponse({'labels': labels, 'data': counts})


# Patient Views
@login_required
def patients(request):
    logger.info("Fetching all patients.")
    patients = Patient.objects.all()
    logger.info(f"Total patients retrieved: {len(patients)}")
    return render(request, 'hms/patient/patients.html', {'patients': patients})

@login_required
def patient_detail(request, patient_code):
    logger.info(f"Fetching details for patient with code: {patient_code}")
    patient = get_object_or_404(Patient, patient_code=patient_code)
    logger.info(f"Patient found: {patient.user.full_name}")
    return render(request, 'hms/patient/patient_detail.html', {'patient': patient})



@login_required
def patient_profile(request, patient_code):
    patient = get_object_or_404(Patient, patient_code=patient_code)

    opd_records = OPD.objects.filter(patient=patient)
    ipd_record = IPD.objects.filter(patient=patient, discharge_date__isnull=True).first()
    expenses = Expense.objects.filter(patient=patient)

    # ✅ Fetch bills from OPD and IPD billing tables
    opd_bills = OPDBilling.objects.filter(patient=patient)
    ipd_bills = IPDBilling.objects.filter(patient=patient)

    # Combine and sort bills (optional)
    all_bills = sorted(
        chain(opd_bills, ipd_bills),
        key=lambda bill: bill.generated_date,
        reverse=True
    )
    
    latest_bill = all_bills[0] if all_bills else None

    reports = PatientReport.objects.filter(patient=patient)

    context = {
        'patient': patient,
        'opd_records': opd_records,
        'ipd_record': ipd_record,
        'expenses': expenses,
        'billing': latest_bill,  # Or use `all_bills` if you want a list
        'reports': reports,
        'profile_picture': patient.profile_picture.url if patient.profile_picture else None
    }

    return render(request, 'hms/patient/patient_profile.html', context)

@login_required
def upload_patient_report(request, patient_code):
    patient = get_object_or_404(Patient, patient_code=patient_code)

    # Fetch the latest IPD record for the patient
    ipd_record = IPD.objects.filter(patient=patient).order_by('-admitted_on').first()

    if not ipd_record:
        messages.error(request, "No IPD record found for this patient.")
        return redirect('patient_profile', patient_code=patient_code)  # Redirect back to profile if no IPD record

    if request.method == "POST":
        form = PatientReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.patient = patient
            report.save()
            return redirect('view_ipd_report', ipd_id=ipd_record.id)  # ✅ Correct redirect
    else:
        form = PatientReportForm()

    context = {'form': form, 'patient': patient}
    return render(request, 'hms/patient/upload_patient_report.html', context)


@login_required
def register_patient(request):
    if request.method == "POST":
        logger.info("Received patient registration form submission.")
        form = PatientRegistrationForm(request.POST, request.FILES)

        if form.is_valid():
            try:
                # Create a new user with the provided details
                user = CustomUser.objects.create(
                    full_name=form.cleaned_data['full_name'],
                    email=form.cleaned_data['email'],
                    contact_number=form.cleaned_data['contact_number'],
                    address=form.cleaned_data['address'],
                    gender=form.cleaned_data['gender'],
                    username=form.cleaned_data['email'],  # Using email as username
                )
                user.set_password("pass123")  # You can generate a random password instead
                user.save()
                logger.info(f"New user created: {user.full_name} ({user.email})")

                # Create a new patient and link the newly created user
                patient = Patient.objects.create(
                    user=user,  # Linking newly created user
                    date_of_birth=form.cleaned_data['date_of_birth'],
                    aadhar_number=form.cleaned_data['aadhar_number'],
                    blood_group=form.cleaned_data['blood_group'],
                    weight=form.cleaned_data.get('weight'),  # ✅ Add this line
                    allergies=form.cleaned_data.get('allergies', ''),
                    medical_history=form.cleaned_data.get('medical_history', ''),
                    current_medications=form.cleaned_data.get('current_medications', ''),
                    emergency_contact_name=form.cleaned_data.get('emergency_contact_name', ''),
                    emergency_contact_number=form.cleaned_data.get('emergency_contact_number', ''),
                    emergency_contact_relationship=form.cleaned_data.get('emergency_contact_relationship', ''),
                    accompanying_person_name=form.cleaned_data.get('accompanying_person_name', ''),
                    accompanying_person_contact=form.cleaned_data.get('accompanying_person_contact', ''),
                    accompanying_person_relationship=form.cleaned_data.get('accompanying_person_relationship', ''),
                    accompanying_person_address=form.cleaned_data.get('accompanying_person_address', ''),
                    profile_picture=form.cleaned_data.get('profile_picture', None),
                    contact_number=form.cleaned_data['contact_number'],
                    gender=form.cleaned_data['gender'],
                    email=form.cleaned_data['email'],
                )
                logger.info(f"New patient registered: {patient.user.full_name} (Code: {patient.patient_code})")

                messages.success(request, "Patient registered successfully!")
                return redirect('patients')

            except Exception as e:
                logger.error(f"Error occurred during patient registration: {e}")
                messages.error(request, f"Error occurred: {str(e)}")
        else:
            logger.warning("Patient registration form is invalid.")
            logger.error(f"Form errors: {form.errors}")
            messages.error(request, "There were errors in your submission. Please check the form.")

    else:
        form = PatientRegistrationForm()

    return render(request, 'hms/patient/register_patient.html', {'form': form})

@login_required
def fetch_patients(request):
    patients = Patient.objects.select_related("user").values(
        "patient_code", "user__full_name", "user__email", "user__contact_number", "user__gender",
        "date_of_birth", "blood_group", "aadhar_number", "emergency_contact_name", "emergency_contact_number"
    )
    return JsonResponse({"patients": list(patients)}, safe=False)

# Doctor Views
@login_required
def doctors(request):
    user = request.user
    if user.groups.filter(name='admin').exists():
        doctors = Doctor.objects.all()
    elif user.groups.filter(name='doctor').exists():
        doctors = Doctor.objects.filter(user=user)
    else:
        doctors = []  # or raise 403
    return render(request, 'hms/doctor/doctors.html', {'doctors': doctors})

@login_required
def doctor_detail(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)

    if request.user.groups.filter(name='doctor').exists() and doctor.user != request.user:
        return HttpResponseForbidden("You are not authorized to view this doctor's profile.")
    
    return render(request, 'hms/doctor/doctor_detail.html', {'doctor': doctor})

@login_required
@user_passes_test(lambda u: u.groups.filter(name='admin').exists())
def add_doctor(request):
    if request.method == 'POST':
        form = DoctorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('doctors')
    else:
        form = DoctorForm()
    return render(request, 'hms/doctor/add_doctor.html', {'form': form})

@login_required
def update_doctor(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    if request.user.groups.filter(name='doctor').exists() and doctor.user != request.user:
        return HttpResponseForbidden("You cannot edit another doctor's profile.")
                                     
    if request.method == 'POST':
        form = DoctorForm(request.POST, instance=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Doctor details updated successfully!')
            return redirect('doctors')
    else:
        form = DoctorForm(instance=doctor)
    return render(request, 'hms/doctor/update_doctor.html', {'form': form, 'doctor': doctor})

@login_required
@user_passes_test(lambda u: u.groups.filter(name='Doctor').exists())
def doctor_dashboard(request):
    doctor = request.user.doctor  # ✅ Use related_name="doctor"
    patients = Patient.objects.filter(assigned_doctor=doctor)
    today = timezone.now().date()
    appointments_today = Appointment.objects.filter(doctor=doctor, date=today)

    return render(request, 'hms/doctor/doctor_dashboard.html', {
        'doctor': doctor,
        'patients': patients,
        'appointments_today': appointments_today
    })


# Appointment Views
def appointments_update(request):
    doctors  = Doctor.objects.all()  
    appointments = Appointment.objects.all()
    print("Doctors in view:", doctors)  # Debugging line
    return render(request, 'hms/apt/appointments.html', {'appointments': appointments, 'doctors': doctors })

@login_required
def appointments(request):
    doctors  = Doctor.objects.all()  
    appointments = Appointment.objects.all()
    print("Doctors in view:", doctors)  # Debugging line
    return render(request, 'hms/apt/appointment_list.html', {'appointments': appointments, 'doctors': doctors })

def fetch_appointments(request):
    appointments = Appointment.objects.select_related("doctor__user", "patient__user").values(
        "id", "doctor__user__full_name", "patient__user__full_name", "date", "time", "status"
    )
    return JsonResponse({"appointments": list(appointments)}, safe=False)

@login_required
def available_doctors(request):
    doctors = Doctor.objects.exclude(availability="").order_by("user__full_name")  # Assuming you have an 'is_available' field
    return render(request, 'hms/doctor/available_doctors.html', {'doctors': doctors})

@login_required
def book_appointment(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)

    # Get the logged-in user's patient profile
    try:
        patient = request.user.patient  # Assuming OneToOne relation with CustomUser
    except Patient.DoesNotExist:
        messages.error(request, "You must be a registered patient to book an appointment.")
        return redirect("dashboard")  # Redirect to a relevant page

    if request.method == "POST":
        selected_date = request.POST.get("date")
        selected_time = request.POST.get("time")

        if not selected_date or not selected_time:
            messages.error(request, "Please fill in all the required fields.")
            return redirect('book_appointment', doctor_id=doctor.id)

        try:
            selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect('book_appointment', doctor_id=doctor.id)

        if selected_date < now().date():
            messages.error(request, "You cannot book an appointment for a past date.")
            return redirect('book_appointment', doctor_id=doctor.id)

        if Appointment.objects.filter(patient=patient, date=selected_date, time=selected_time).exists():
            messages.error(request, "You already have an appointment booked for this date and time.")
            return redirect('book_appointment', doctor_id=doctor.id)

        # Create the appointment
        appointment = Appointment(
            patient=patient,
            doctor=doctor,
            date=selected_date,
            time=selected_time,
            status="pending"
        )
        appointment.save()

        messages.success(request, f"Appointment booked for {selected_date} at {selected_time}.")
        return redirect('appointment_success', doctor_id=doctor_id)

    return render(request, 'hms/apt/book_appointment.html', {'doctor': doctor, 'patient': patient})

def appointment_success(request, doctor_id):
    return render(request, 'hms/apt/appointment_success.html', {'doctor_id': doctor_id})

@login_required
def update_appointment_status(request):
    if request.method == "POST":
        appointment_id = request.POST.get("appointment_id")
        new_status = request.POST.get(f"status_{appointment_id}")
        print(new_status)

        appointment = get_object_or_404(Appointment, id=appointment_id)
        appointment.status = new_status
        appointment.save()  # OPD record will be created automatically if status is 'confirmed'

        messages.success(request, f"Appointment status updated to {new_status}.")
        return redirect("appointments")  # Redirect to the appointments list

    return redirect("appointments")


@login_required
def generate_ipd_bill(request, ipd_id):
    ipd_admission = get_object_or_404(IPD, id=ipd_id)
    
    # Create or get existing billing
    bill, created = IPDBilling.objects.get_or_create(
        ipd_admission=ipd_admission,
        defaults={
            'patient': ipd_admission.patient,
            'due_date': timezone.now() + timezone.timedelta(days=7)
        }
    )
    
    # Add standard items if new bill
    if created:
        # Room charges
        BillingItem.objects.create(
            billing_type='ipd',
            ipd_billing=bill,
            description=f"Room Charges ({ipd_admission.room.room_type}) - Bed #{ipd_admission.bed_number}",
            quantity=max(1, (timezone.now() - ipd_admission.admitted_on).days),
            unit_price=ipd_admission.room.bed_price_per_day,
        )
        
        # Nursing charges (example)
        BillingItem.objects.create(
            billing_type='ipd',
            ipd_billing=bill,
            description="Nursing Charges",
            quantity=max(1, (timezone.now() - ipd_admission.admitted_on).days),
            unit_price=Decimal('500.00'),  # Daily nursing charge
        )
    
    return render(request, 'hms/bills/ipd_bill.html', {'bill': bill})
@login_required
def generate_opd_bill(request, opd_id):
    opd_visit = get_object_or_404(OPD, id=opd_id)
    
    bill, created = OPDBilling.objects.get_or_create(
        opd_visit=opd_visit,
        defaults={
            'patient': opd_visit.patient,
            'due_date': timezone.now() + timezone.timedelta(days=7)
        }
    )
    
    if created:
        # Consultation fee
        BillingItem.objects.create(
            billing_type='opd',
            opd_billing=bill,
            description=f"Consultation with Dr. {opd_visit.doctor.user.full_name}",
            quantity=1,
            unit_price=opd_visit.doctor.consultation_fee,
        )
    
    return render(request, 'hms/bills/opd_bill.html', {'bill': bill})


@login_required
def view_bill_pdf(request, bill_number):
    # Try to find bill in both OPD and IPD tables
    bill = None
    try:
        bill = OPDBilling.objects.get(bill_number=bill_number)
    except OPDBilling.DoesNotExist:
        try:
            bill = IPDBilling.objects.get(bill_number=bill_number)
        except IPDBilling.DoesNotExist:
            raise Http404("Bill not found")
    
    template_path = 'hms/bills/bill_pdf.html'
    context = {'bill': bill}
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{bill.bill_number}.pdf"'
    
    template = get_template(template_path)
    html = template.render(context)
    
    # Create PDF
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error generating PDF')
    
    return response


@login_required
def record_payment(request, bill_number):
    bill = None
    try:
        bill = OPDBilling.objects.get(bill_number=bill_number)
    except OPDBilling.DoesNotExist:
        try:
            bill = IPDBilling.objects.get(bill_number=bill_number)
        except IPDBilling.DoesNotExist:
            raise Http404("Bill not found")
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.billing = bill
            payment.received_by = request.user
            payment.save()
            
            messages.success(request, f"Payment of ₹{payment.amount} recorded successfully")
            return redirect('view_bill', bill_number=bill.bill_number)
    else:
        form = PaymentForm()
    
    return render(request, 'hms/bills/record_payment.html', {
        'bill': bill,
        'form': form,
        'balance': bill.balance_amount
    })

@login_required
def bill_list(request):
    opd_bills = list(OPDBilling.objects.select_related('patient__user'))
    ipd_bills = list(IPDBilling.objects.select_related('patient__user'))

    

    # Merge and sort
    bills = opd_bills + ipd_bills
    bills.sort(key=lambda b: b.generated_date, reverse=True)

    # Paginate
    paginator = Paginator(bills, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'hms/bills/billing_list.html', {
        'page_obj': page_obj,
        'bills': page_obj.object_list,
    })

@login_required
def create_opd_bill(request):
    if request.method == 'POST':
        form = OPDBillingForm(request.POST)
        if form.is_valid():
            bill = form.save(commit=False)
            bill.patient = bill.opd_visit.patient
            bill.save()
            messages.success(request, 'OPD bill created successfully!')
            return redirect('view_bill', bill_number=bill.bill_number)
    else:
        form = OPDBillingForm()
    
    return render(request, 'hms/bills/create_opd_bill.html', {'form': form})
@login_required
def create_ipd_bill(request):
    if request.method == 'POST':
        form = IPDBillingForm(request.POST)
        if form.is_valid():
            bill = form.save(commit=False)
            bill.patient = bill.ipd_admission.patient

            # Auto-fetch room charges from IPD
            if not bill.room_charges:
                bill.room_charges = bill.ipd_admission.calculate_total_cost()

            bill.save()
            messages.success(request, 'IPD bill created successfully!')
            return redirect('view_bill', bill_number=bill.bill_number)
    else:
        form = IPDBillingForm()

    return render(request, 'hms/bills/create_ipd_bill.html', {'form': form})

# def view_bill(request, bill_number=None, patient_id=None):

@login_required
def view_bill(request, bill_number=None, patient_id=None):
    if bill_number:
        # Show a single OPD or IPD bill
        bill = None
        bill_type = None
        opd_bill = None
        ipd_bill = None

        try:
            bill = OPDBilling.objects.select_related('patient__user').get(bill_number=bill_number)
            opd_bill = bill
            bill_type = 'OPD'
        except OPDBilling.DoesNotExist:
            try:
                bill = IPDBilling.objects.select_related('patient__user').get(bill_number=bill_number)
                ipd_bill = bill
                bill_type = 'IPD'
            except IPDBilling.DoesNotExist:
                raise Http404("Bill not found")

        return render(request, 'hms/bills/view_bill.html', {
            'bill': bill,
            'opd_bill': opd_bill,
            'ipd_bill': ipd_bill,
            'bill_type': bill_type
        })

    elif patient_id:
        # Show all bills for a patient
        patient = get_object_or_404(Patient, id=patient_id)
        opd_bills = OPDBilling.objects.filter(patient=patient)
        ipd_bills = IPDBilling.objects.filter(patient=patient)

        return render(request, 'hms/bills/view_bill.html', {
            'patient': patient,
            'opd_bills': opd_bills,
            'ipd_bills': ipd_bills,
        })

    else:
        raise Http404("Invalid request")

from django.http import HttpResponse, Http404
from django.template.loader import get_template
from xhtml2pdf import pisa
from .models import OPDBilling, IPDBilling

def view_bill_pdf(request, bill_number):
    # Try to find the bill in both OPD and IPD tables
    bill = None
    bill_type = None

    try:
        bill = OPDBilling.objects.get(bill_number=bill_number)
        bill_type = 'OPD'
    except OPDBilling.DoesNotExist:
        try:
            bill = IPDBilling.objects.get(bill_number=bill_number)
            bill_type = 'IPD'
        except IPDBilling.DoesNotExist:
            raise Http404("Bill not found")
    
    # Set item_offset based on static items in the template
    item_offset = 4 if bill_type == 'OPD' else 6

    # Additional context for rendering
    context = {
        'bill': bill,
        'bill_type': bill_type,
        'item_offset': item_offset,
        'hospital_name': 'Nelson Hospital',
        'hospital_address': '123 Nelson Street, Health City',
        'hospital_phone': '+91-9876543210',
        'hospital_email': 'contact@nelsonhospital.com',
        'billing_contact': 'billing@nelsonhospital.com',
    }

    # Render HTML template
    template_path = 'hms/bills/bill_pdf.html'
    template = get_template(template_path)
    html = template.render(context)

    # Generate PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{bill.bill_number}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('Error generating PDF')

    return response


def add_billing_item(request, bill_number):
    bill = None
    billing_type = None
    
    try:
        bill = OPDBilling.objects.get(bill_number=bill_number)
        billing_type = 'opd'
    except OPDBilling.DoesNotExist:
        try:
            bill = IPDBilling.objects.get(bill_number=bill_number)
            billing_type = 'ipd'
        except IPDBilling.DoesNotExist:
            raise Http404("Bill not found")
    
    if request.method == 'POST':
        form = BillingItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            # Assign foreign key and billing_type based on parent bill
            if billing_type == 'opd':
                item.opd_billing = bill
            else:
                item.ipd_billing = bill
            
            # billing_type set automatically in BillingItem.save()
            item.save()
            
            messages.success(request, 'Billing item added successfully!')
            return redirect('view_bill', bill_number=bill.bill_number)
    else:
        form = BillingItemForm()
    
    return render(request, 'hms/bills/add_billing_item.html', {
        'form': form,
        'bill': bill,
        'billing_type': billing_type,
    })

def record_payment(request, bill_number):
    # Find bill
    try:
        bill = OPDBilling.objects.get(bill_number=bill_number)
    except OPDBilling.DoesNotExist:
        try:
            bill = IPDBilling.objects.get(bill_number=bill_number)
        except IPDBilling.DoesNotExist:
            raise Http404("Bill not found")

    if request.method == 'POST':
        form = PaymentForm(request.POST, max_amount=bill.balance_amount)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.billing = bill
            payment.received_by = request.user
            payment.save()

            messages.success(request, f"Payment of ₹{payment.amount} recorded successfully!")
            return redirect('payment_receipt', pk=payment.id)
        else:
            # For debugging, you can print errors here or pass them to template
            print(form.errors)
    else:
        form = PaymentForm(max_amount=bill.balance_amount)

    return render(request, 'hms/bills/record_payment.html', {
        'bill': bill,
        'form': form
    })

def expense_list(request):
    expenses = Expense.objects.all().order_by('-created_at')
    return render(request, 'hms/bills/expense_list.html', {'expenses': expenses})

def add_expense(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save()
            messages.success(request, 'Expense added successfully!')
            return redirect('expense_list')
    else:
        form = ExpenseForm()
    
    return render(request, 'hms/bills/add_expense.html', {'form': form})

def edit_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense updated successfully!')
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense)
    
    return render(request, 'hms/bills/edit_expense.html', {'form': form})

def delete_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    if request.method == 'POST':
        expense.delete()
        messages.success(request, 'Expense deleted successfully!')
        return redirect('expense_list')
    
    return render(request, 'hms/bills/delete_expense.html', {'expense': expense})
@login_required
def payment_list(request):
    payments = Payment.objects.all().order_by('-payment_date')

    # Add billing type manually
    for payment in payments:
        billing_model = payment.billing.__class__.__name__.replace('Billing', '').upper()  # OPD, IPD, etc.
        payment.billing_type = billing_model

    return render(request, 'hms/bills/payment_list.html', {'payments': payments})

@login_required
def payment_detail(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    return render(request, 'hms/bills/payment_detail.html', {'payment': payment})



@login_required
def payment_receipt(request, pk):
    payment = get_object_or_404(Payment, pk=pk)

    billing_model = payment.billing.__class__.__name__
    billing_type = "OPD" if billing_model == "OPDBilling" else "IPD" if billing_model == "IPDBilling" else "Other"

    # Generate QR code (optional: use payment ID, transaction ID, or bill link)
    qr_data = f"Payment ID: {payment.id} | Bill No: {payment.billing.bill_number}"
    qr = qrcode.make(qr_data)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode()
    qr_image_url = f"data:image/png;base64,{img_str}"

    context = {
        'payment': payment,
        'qr_image_url': qr_image_url,
        'hospital_name': 'Nelson Health Connect',
        'hospital_logo_url': '/static/images/hospital_logo.png',  # adjust path as needed
    }

    template_path = 'hms/bills/payment_receipt.html'
    html = get_template(template_path).render(context)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="payment_receipt_{payment.id}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("Error generating PDF")
    return response




# Emergency Views
@login_required
def emergency(request):
    emergencies = EmergencyCase.objects.all()
    return render(request, 'hms/emergency/emergency.html', {'emergencies': emergencies})

def emergency_s(request):
    query = request.GET.get('q', '').strip()
    emergencies = EmergencyCase.objects.all()

    if query:
        emergencies = emergencies.filter(
            Q(patient__full_name__icontains=query) |
            Q(emergency_type__icontains=query) |
            Q(status__icontains=query) |
            Q(case_description__icontains=query) |
            Q(referred_by__icontains=query) |
            Q(referrer_contact__icontains=query)
        )

    emergencies_list = list(emergencies.values(
        'id', 'patient__full_name', 'emergency_type', 'status', 'case_description', 'severity'
    ))

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(emergencies_list, safe=False)

    return render(request, 'hms/emergency/emergency.html', {'emergencies': emergencies_list})

@login_required
def add_emergency_case(request):
    if request.method == "POST":
        form = EmergencyCaseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Emergency case added successfully!")
            return redirect("emergency")
    else:
        form = EmergencyCaseForm()
    return render(request, "hms/emergency/add_emergency.html", {"form": form})

@login_required
def edit_emergency_case(request, emergency_id):
    emergency = get_object_or_404(EmergencyCase, id=emergency_id)
    if request.method == "POST":
        form = EmergencyCaseForm(request.POST, instance=emergency)
        if form.is_valid():
            form.save()
            messages.success(request, "Emergency case updated successfully!")
            return redirect("emergency")
    else:
        form = EmergencyCaseForm(instance=emergency)
    return render(request, "hms/emergency/edit_emergency.html", {"form": form})

@login_required
def delete_emergency_case(request, emergency_id):
    emergency = get_object_or_404(EmergencyCase, id=emergency_id)

    if request.method == 'POST':
        # Delete the emergency case
        emergency.delete()
        messages.success(request, "Emergency case deleted successfully!")
        return redirect("emergency")

    # Render the confirmation page for GET requests
    return render(request, 'hms/emergency/delete_emergency.html', {'emergency': emergency})

@login_required
def admit_emergency_patient(request, emergency_id):
    emergency_case = get_object_or_404(EmergencyCase, id=emergency_id)

    # Find a room that has available beds
    available_room = Room.objects.filter(available_beds__gt=0).first()

    if available_room:
        # Assign an available bed from the room
        assigned_bed = available_room.admit_patient_to_bed()

        if assigned_bed is not None:
            # Create an IPD record for the patient
            ipd = IPD.objects.create(
                patient=emergency_case.patient,
                room=available_room,
                bed_number=assigned_bed,  # Store the assigned bed number
                reason_for_admission=emergency_case.case_description
            )

            # Update emergency case status
            emergency_case.status = "Admitted"
            emergency_case.save()

            messages.success(request, f"Patient admitted to IPD successfully in Room {available_room.room_number}, Bed {assigned_bed}!")
            return redirect("ipd")

    messages.error(request, "No available beds for admission!")
    return redirect("emergency")

# IPD Views
@login_required
def ipd(request):
    ipds = IPD.objects.all().order_by('-admitted_on')
    room = Room.objects.all()
    return render(request, 'hms/ipd/ipd.html', {'ipds': ipds, 'room': room})


@login_required
def add_ipd(request):
    available_rooms = Room.objects.filter(available_beds__gt=0)

    if request.method == "POST":
        print("POST weight:", request.POST.get('weight'))
        room_id = request.POST.get("room")
        bed_number = request.POST.get("bed_number")
        patient_id = request.POST.get("patient")
        reason = request.POST.get("reason_for_admission")

        if not all([room_id, bed_number, patient_id]):
            messages.error(request, "Please fill all required fields.")
            return redirect("add_ipd")

        room = get_object_or_404(Room, id=room_id)
        bed_number = int(bed_number)

        if bed_number in room.occupied_beds:
            messages.error(request, "This bed is already occupied.")
            return redirect("add_ipd")

        room.occupied_beds.append(bed_number)
        room.update_availability()

        patient = get_object_or_404(Patient, id=patient_id)
        print("patient",patient)

        ipd = IPD.objects.create(
            patient=patient,
            room=room,
            bed_number=bed_number,
            reason_for_admission=reason,
            bed_price_per_day=room.bed_price_per_day
        )

        messages.success(request, f"Patient admitted to Room {room.room_number}, Bed {bed_number}.")
        return redirect("ipd")

    patients = Patient.objects.all()
    return render(request, "hms/ipd/add_ipd.html", {
        "rooms": available_rooms,
        "patients": patients
    })


def get_available_beds(request):
    room_id = request.GET.get("room_id")
    try:
        room = Room.objects.get(id=room_id)
        occupied = room.occupied_beds or []
        available_beds = []

        for i in range(1, room.total_beds + 1):
            if i not in occupied:
                available_beds.append({
                    "id": i,
                    "bed_number": f"Bed {i}"
                })

        return JsonResponse({"beds": available_beds})
    except Room.DoesNotExist:
        return JsonResponse({"beds": []})



def get_ipd_data(request):
    ipds = IPD.objects.all()

    ipd_data = []
    for ipd in ipds:
        ipd_data.append({
            'id': ipd.id,
            'patient__user__full_name': ipd.patient.user.full_name,
            'room__room_number': ipd.room.room_number if ipd.room else "N/A",
            'patient__patient_code': ipd.patient.patient_code,
            'bed_number': ipd.bed_number,
            'admitted_on': ipd.admitted_on.strftime('%Y-%m-%d %H:%M:%S'),  
            'reason_for_admission': ipd.reason_for_admission,
            'total_cost': float(ipd.calculate_total_cost()),  # Call the method and convert it
        })

    return JsonResponse(ipd_data, safe=False)

# View IPD Report
def view_ipd_report(request, ipd_id):
    ipd = get_object_or_404(IPD, id=ipd_id)
    rooms = Room.objects.all()
    prescriptions = Prescription.objects.filter(ipd=ipd).order_by('-timing')
    reports = PatientReport.objects.filter(patient=ipd.patient).order_by('-uploaded_at')  # Fetch reports
    return render(request, 'hms/ipd/view_ipd_report.html', {'ipd': ipd, 'rooms': rooms,'prescriptions':prescriptions,'reports': reports})

# Update IPD Room
def update_ipd_room(request, ipd_id):
    ipd = get_object_or_404(IPD, id=ipd_id)
    if request.method == "POST":
        room_id = request.POST.get("room")
        bed_number = request.POST.get("bed_number")
        ipd.room_id = room_id
        ipd.bed_number = bed_number
        ipd.save()
        messages.success(request, "Room and bed updated successfully.")
    return redirect('view_ipd_report', ipd_id=ipd.id)


def discharge_summary_view(request, patient_code):
    """
    Renders the discharge summary template with a download button.
    """
    patient = get_object_or_404(Patient, patient_code=patient_code)

    context = {
        "patient": patient,
        "opd_visits": OPD.objects.filter(patient=patient).order_by('-visit_date'),
        "ipd_records": IPD.objects.filter(patient=patient),
        "prescriptions": Prescription.objects.filter(ipd__patient=patient).order_by('-timing'),
        "action": "Discharged",
    }

    return render(request, "hms/ipd/discharge_summary.html", context)


def transfer_summary_view(request, patient_code):
    """
    Renders the transfer summary template with a download button.
    """
    patient = get_object_or_404(Patient, patient_code=patient_code)

    context = {
        "patient": patient,
        "opd_visits": OPD.objects.filter(patient=patient).order_by('-visit_date'),
        "ipd_records": IPD.objects.filter(patient=patient),
        "prescriptions": Prescription.objects.filter(ipd__patient=patient).order_by('-timing'),
        "transfer": PatientTransfer.objects.filter(patient=patient).order_by('-transfer_date').first(),
    }

    return render(request, "hms/ipd/transfer_summary.html", context)


def render_to_pdf(template_src, context_dict):
    """
    Utility function to generate a PDF from a template.
    """
    template = get_template(template_src)
    html = template.render(context_dict)
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="report.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        logger.error(f"PDF generation failed for template {template_src}")
        return HttpResponse("Error generating PDF", status=500)

    return response


def discharge_summary_pdf(request, patient_code):
    """
    Generates and downloads the discharge summary as a PDF.
    """
    patient = get_object_or_404(Patient, patient_code=patient_code)

    context = {
        "patient": patient,
        "opd_visits": OPD.objects.filter(patient=patient).order_by('-visit_date'),
        "ipd_records": IPD.objects.filter(patient=patient),
        "prescriptions": Prescription.objects.filter(ipd__patient=patient).order_by('-timing'),
        "action": "Discharged",
    }

    return render_to_pdf("hms/ipd/discharge_summary.html", context)


def transfer_summary_pdf(request, patient_code):
    """
    Generates and downloads the transfer summary as a PDF.
    """
    patient = get_object_or_404(Patient, patient_code=patient_code)

    context = {
        "patient": patient,
        "opd_visits": OPD.objects.filter(patient=patient).order_by('-visit_date'),
        "ipd_records": IPD.objects.filter(patient=patient),
        "prescriptions": Prescription.objects.filter(ipd__patient=patient).order_by('-timing'),
        "transfer": PatientTransfer.objects.filter(patient=patient).order_by('-transfer_date').first(),
    }

    return render_to_pdf("hms/ipd/transfer_summary.html", context)

def add_prescription(request, ipd_id):
    ipd = get_object_or_404(IPD, id=ipd_id)

    if request.method == "POST":
        form = PrescriptionForm(request.POST)
        if form.is_valid():
            prescription = form.save(commit=False)
            prescription.ipd = ipd
            prescription.save()
            messages.success(request, "Prescription added successfully.")
            return redirect('view_ipd_report', ipd_id=ipd_id)

    else:
        form = PrescriptionForm()

    return render(request, 'hms/opd/add_prescription.html', {'form': form, 'ipd': ipd})

# OPD Views
@login_required
def opd(request):
    opds = OPD.objects.all()
    return render(request, 'hms/opd/opd.html', {'opds': opds})

def fetch_opd(request):
    try:
        # Fetch OPD records with related patient and doctor details
        opd_records = OPD.objects.select_related("patient__user", "doctor__user").values(
            "id", 
            "patient__user__full_name", 
            'patient__patient_code',
            "doctor__user__full_name", 
            "doctor__specialization", 
            "created_at",   # Use 'created_at' instead of 'visit_date'
            "diagnosis", 
            "symptoms", 
            "prescription", 
            "visit_type", 
             
            "follow_up_date"
        )

        # Format the data for JSON response
        formatted_records = []
        for record in opd_records:
            formatted_records.append({
                "id": record["id"],
                "patient__user__full_name": record["patient__user__full_name"],
                "patient__patient_code": record["patient__patient_code"],
                "doctor__user__full_name": record["doctor__user__full_name"],
                "doctor__specialization": record["doctor__specialization"],
                "created_at": record["created_at"].strftime("%Y-%m-%d %H:%M:%S"),  # Format datetime
                "diagnosis": record["diagnosis"],
                "symptoms": record["symptoms"] or "N/A",  # Handle null values
                "prescription": record["prescription"] or "N/A",  # Handle null values
                "visit_type": record["visit_type"],
                # "payment_status": record["payment_status"],
                # "payment_amount": float(record["payment_amount"]),  # Convert Decimal to float
                "follow_up_date": record["follow_up_date"].strftime("%Y-%m-%d") if record["follow_up_date"] else "N/A"  # Format date
            })

        return JsonResponse({"opds": formatted_records}, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@login_required
def add_opd(request):
    if request.method == "POST":
        patient_id = request.POST.get("patient")
        doctor_id = request.POST.get("doctor")
        diagnosis = request.POST.get("diagnosis")

        patient = Patient.objects.get(id=patient_id)
        doctor = Doctor.objects.get(id=doctor_id)

        OPD.objects.create(patient=patient, doctor=doctor, diagnosis=diagnosis)
        messages.success(request, "OPD visit added successfully!")
        return redirect("opd")  # Redirect to OPD list page

    patients = Patient.objects.all()
    doctors = Doctor.objects.all()
    return render(request, "hms/opd/add_opd.html", {"patients": patients, "doctors": doctors})

@login_required
def update_opd(request, opd_id):
    opd = get_object_or_404(OPD, id=opd_id)

    if request.method == "POST":
        doctor_id = request.POST.get("doctor")
        diagnosis = request.POST.get("diagnosis")
        symptoms = request.POST.get("symptoms")
        prescription = request.POST.get("prescription")
        follow_up_date = request.POST.get("follow_up_date")
        visit_type = request.POST.get("visit_type")
        # payment_status = request.POST.get("payment_status")
        # payment_amount = request.POST.get("payment_amount")

        opd.doctor = Doctor.objects.get(id=doctor_id)
        opd.diagnosis = diagnosis
        opd.symptoms = symptoms
        opd.prescription = prescription
        opd.follow_up_date = follow_up_date
        opd.visit_type = visit_type
        # opd.payment_status = payment_status
        # opd.payment_amount = payment_amount
        opd.save()

        messages.success(request, "OPD visit updated successfully!")
        return redirect("opd")

    doctors = Doctor.objects.all()
    return render(request, "hms/opd/update_opd.html", {"opd": opd, "doctors": doctors})



def calculate_age(date_of_birth):
    """Returns the age in days, months, or years based on the date of birth."""
    if not date_of_birth:
        return "N/A"
    
    today = date.today()
    delta = today - date_of_birth  # Difference in days

    if delta.days < 30:
        return f"{delta.days} day(s) old" if delta.days > 0 else "Newborn"
    elif delta.days < 365:
        months = delta.days // 30
        return f"{months} month(s) old"
    else:
        years = delta.days // 365
        return f"{years} year(s) old"


def opd_report_template(request, patient_id):
    # Fetch the OPD record for the specific patient
    opd = get_object_or_404(OPD, id=patient_id)
    patient = opd.patient
    
    # Calculate age dynamically
    patient_age = calculate_age(patient.date_of_birth)

    # Prepare the context with all fields from the OPD model
    opd_visits = [
        {
            'created_at': opd.created_at.strftime("%Y-%m-%d %H:%M:%S"),  # Include time for precision
            'doctor': opd.doctor.user.full_name,
            'diagnosis': opd.diagnosis,
            'symptoms': opd.symptoms,
            'prescription': opd.prescription,
            'visit_type': opd.get_visit_type_display(),  # Get the display value for the choice field
            'follow_up_date': opd.follow_up_date.strftime("%Y-%m-%d") if opd.follow_up_date else "N/A",  # Format date or show "N/A"
        },
    ]
    
    context = {
        'current_date': timezone.now().strftime("%Y-%m-%d %H:%M:%S"),  # Include time for precision
        'patient_name': opd.patient.user.full_name,
        'patient_gender': opd.patient.gender,
        'patient_contact': opd.patient.contact_number,
        'opd_visits': opd_visits,
        'patient_age': patient_age,  # Pass dynamically calculated age
    }
    return render(request, 'hms/opd/opd_report_template.html', context)

@login_required
def admit_patient(request, opd_id):
    opd = get_object_or_404(OPD, id=opd_id)
    available_rooms = Room.objects.filter(available_beds__gt=0)  # Only rooms with available beds

    if request.method == "POST":
        room_id = request.POST.get("room")
        bed_number = request.POST.get("bed")

        room = get_object_or_404(Room, id=room_id)

        if not bed_number:
            messages.error(request, "Please select a bed.")
            return redirect("admit_patient", opd_id=opd_id)

        bed_number = int(bed_number)

        if bed_number in room.occupied_beds:
            messages.error(request, "This bed is already occupied.")
            return redirect("admit_patient", opd_id=opd_id)

        # Assign the selected bed
        room.occupied_beds.append(bed_number)
        room.update_availability()

        # Create an IPD record for the patient
        ipd = IPD.objects.create(
            patient=opd.patient,
            room=room,
            reason_for_admission=opd.diagnosis,
            bed_number=bed_number,
            bed_price_per_day=room.bed_price_per_day
        )

        messages.success(request, f"Patient admitted to Room {room.room_number}, Bed {bed_number}.")
        return redirect("ipd")

    return render(request, "hms/ipd/admit_patient.html", {"opd": opd, "rooms": available_rooms})

def get_available_beds(request):
    room_id = request.GET.get("room_id")
    if room_id:
        room = get_object_or_404(Room, id=room_id)
        available_beds = [bed for bed in range(1, room.total_beds + 1) if bed not in room.occupied_beds]
        return JsonResponse({"beds": [{"id": bed, "bed_number": f"Bed {bed}"} for bed in available_beds]})
    return JsonResponse({"beds": []})

@login_required
def move_appointments_to_opd():
    """Automatically move confirmed appointments to OPD."""
    confirmed_appointments = Appointment.objects.filter(status='confirmed')
    for appointment in confirmed_appointments:
        OPD.objects.get_or_create(
            patient=appointment.patient,
            doctor=appointment.doctor,
            diagnosis="Pending diagnosis"
        )
        appointment.status = 'completed'
        appointment.save()

# Room Views@login_required
def room_overview(request):
    rooms = Room.objects.all()

    for room in rooms:
        room.total_beds_list = list(range(1, room.total_beds + 1))
        room.bed_patient_info = {}

        for bed_number in room.occupied_beds:
            # Find the patient admitted to this bed in the IPD model
            ipd_record = IPD.objects.filter(room=room, bed_number=bed_number).first()
            if ipd_record:
                room.bed_patient_info[bed_number] = {
                    "name": ipd_record.patient.user.full_name,
                    "admit_date": ipd_record.admitted_on,
                    "cost": room.bed_price_per_day,
                }

    return render(request, 'hms/room/room_overview.html', {'rooms': rooms})

@login_required
def add_room(request):
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Room added successfully!")  # ✅ Success Message
            return redirect('add_room')
    else:
        form = RoomForm()

    return render(request, 'hms/room/add_room.html', {'form': form})

# Employee Views
@login_required
def add_employee(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('employee_list')
    else:
        form = EmployeeForm()
    return render(request, 'hms/employee/add_employee.html', {'form': form})

@login_required
def employee_list(request):
    employees = Employee.objects.all()
    return render(request, 'hms/employee/employee_list.html', {'employees': employees})

@login_required
def edit_employee(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == "POST":
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            return redirect('employee_list')
    else:
        form = EmployeeForm(instance=employee)
    return render(request, 'hms/employee/add_employee.html', {'form': form})

@login_required
def delete_employee(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == "POST":
        employee.delete()
        return redirect('employee_list')
    return render(request, 'hms/employee/confirm_delete.html', {'object': employee})

@login_required
def pay_salary(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        payment_date = request.POST.get('payment_date')  # Get payment date from form
        employee.pay_salary(payment_date)  # Pass payment_date to the method
        return redirect('employee_list')
    return render(request, 'hms/salary/pay_salary.html', {'employee': employee})

# License Views
def license_list(request):
    licenses = License.objects.all()
    return render(request, 'hms/license/license_list.html', {'licenses': licenses})

def add_license(request):
    if request.method == 'POST':
        form = LicenseForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('license_list')
    else:
        form = LicenseForm()
    return render(request, 'hms/license/license_form.html', {'form': form})

def edit_license(request, id):
    license_instance = get_object_or_404(License, id=id)
    if request.method == 'POST':
        form = LicenseForm(request.POST, request.FILES, instance=license_instance)
        if form.is_valid():
            form.save()
            return redirect('license_list')
    else:
        form = LicenseForm(instance=license_instance)
    return render(request, 'hms/license/license_form.html', {'form': form})

def delete_license(request, id):
    license = get_object_or_404(License, id=id)
    license.delete()
    return redirect('license_list')

# Asset Views
def asset_list(request):
    assets = Asset.objects.all()
    return render(request, 'hms/asset/asset_list.html', {'assets': assets})

def add_asset(request):
    if request.method == 'POST':
        form = AssetForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('asset_list')
    else:
        form = AssetForm()
    return render(request, 'hms/asset/asset_form.html', {'form': form, 'title': 'Add Asset'})

def edit_asset(request, id):
    asset = get_object_or_404(Asset, id=id)
    if request.method == 'POST':
        form = AssetForm(request.POST, instance=asset)
        if form.is_valid():
            form.save()
            return redirect('asset_list')
    else:
        form = AssetForm(instance=asset)
    return render(request, 'hms/asset/asset_form.html', {'form': form, 'title': 'Edit Asset'})

def delete_asset(request, id):
    asset = get_object_or_404(Asset, id=id)
    asset.delete()
    return redirect('asset_list')

# Maintenance Views
def maintenance_list(request):
    maintenance_records = Maintenance.objects.all()
    return render(request, 'hms/maintenance/maintenance_list.html', {'maintenance_records': maintenance_records})

def add_maintenance(request):
    if request.method == 'POST':
        form = MaintenanceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('maintenance_list')
    else:
        form = MaintenanceForm()
    return render(request, 'hms/maintenance/maintenance_form.html', {'form': form, 'title': 'Add Maintenance'})

def edit_maintenance(request, id):
    maintenance = get_object_or_404(Maintenance, id=id)
    if request.method == 'POST':
        form = MaintenanceForm(request.POST, instance=maintenance)
        if form.is_valid():
            form.save()
            return redirect('maintenance_list')
    else:
        form = MaintenanceForm(instance=maintenance)
    return render(request, 'hms/maintenance/maintenance_form.html', {'form': form, 'title': 'Edit Maintenance'})

def delete_maintenance(request, id):
    maintenance = get_object_or_404(Maintenance, id=id)
    maintenance.delete()
    return redirect('maintenance_list')

@login_required
def accounting_summary(request):
    # Default dates
    today = timezone.now().date()
    start_date = request.GET.get('start_date', today)
    end_date = request.GET.get('end_date', today)

    # Convert to date objects if strings
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    if end_date < start_date:
        messages.error(request, "End date cannot be before start date.")
        return redirect('accounting_summary')

    # Income calculations:

    opd_income = OPDBilling.objects.filter(
        generated_date__date__range=(start_date, end_date),
        status='paid'
    ).aggregate(total_income=Sum('paid_amount'))['total_income'] or 0

    ipd_income = IPDBilling.objects.filter(
        generated_date__date__range=(start_date, end_date),
        status='paid'
    ).aggregate(total_income=Sum('paid_amount'))['total_income'] or 0

    # You can remove the IPD income from IPD admissions unless you want it separately.

    billing_income = opd_income + ipd_income

    # Expenses calculations:

    daybook_expenses = Daybook.objects.filter(
        date__range=(start_date, end_date)
    ).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0

    salary_expenses = AccountingRecord.objects.filter(
        transaction_type='expense',
        source='salary',
        date__date__range=(start_date, end_date)
    ).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0

    other_expenses = AccountingRecord.objects.filter(
        transaction_type='expense',
        date__date__range=(start_date, end_date)
    ).exclude(source='salary').aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0

    total_expenses = daybook_expenses + salary_expenses + other_expenses

    net_profit = billing_income - total_expenses

    # Daily profit calculation
    daily_profit = []
    date_labels = []
    current_date = start_date
    while current_date <= end_date:
        opd_total = OPDBilling.objects.filter(generated_date__date=current_date, is_paid='True').aggregate(total=Sum('total_amount'))['total'] or 0
        ipd_total = IPDBilling.objects.filter(generated_date__date=current_date).aggregate(total=Sum('total_amount'))['total'] or 0
        # billing_total = BillingBase.objects.filter(generated_on__date=current_date, status='paid').aggregate(total=Sum('paid_amount'))['total'] or 0
        daily_income = opd_total + ipd_total 

        daybook_total = Daybook.objects.filter(date=current_date).aggregate(total=Sum('amount'))['total'] or 0
        accounting_total = AccountingRecord.objects.filter(transaction_type='expense', date=current_date).aggregate(total=Sum('amount'))['total'] or 0
        daily_expenses = daybook_total + accounting_total

        daily_net_profit = float(daily_income - daily_expenses)
        daily_profit.append(daily_net_profit)
        date_labels.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)


    context = {
        'start_date': start_date.strftime("%Y-%m-%d"),
        'end_date': end_date.strftime("%Y-%m-%d"),
        'opd_income': opd_income,
        'ipd_income': ipd_income,
        'billing_income': billing_income,
        'total_income': billing_income,
        'daybook_expenses': daybook_expenses,
        'salary_expenses': salary_expenses,
        'other_expenses': other_expenses,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'daily_profit': daily_profit,
        'date_labels': date_labels,
    }
    return render(request, 'hms/accounting_summary.html', context)


# Daybook Views
class DaybookCreateView(LoginRequiredMixin, View):
    login_url = '/login/'
    template_name = 'hms/daybook/daybook_form.html'

    def get(self, request, *args, **kwargs):
        form = DaybookEntryForm()
        return render(request, self.template_name, {'form': form, 'today': timezone.now().date()})

    def post(self, request, *args, **kwargs):
        form = DaybookEntryForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user  # Assign the current user
            balance, created = Balance.objects.get_or_create(user=request.user, defaults={'amount': 0})

            if balance.amount >= expense.amount:
                balance.amount -= expense.amount
                action_message = "added"
            else:
                messages.error(request, "Daily limit reached. Expense exceeds available balance.")
                return render(request, self.template_name, {'form': form, 'today': timezone.now().date()})

            expense.save()
            balance.save()

            remaining_balance = balance.amount
            message = f"Daybook Entry {action_message}:\nDate: {expense.date}\nActivity: {expense.activity}\nAmount: {expense.amount}\nRemaining Balance: {remaining_balance}"
            if expense.remark:
                message += f"\nRemark: {expense.remark}"

            messages.success(request, f"Expense of {expense.amount} has been successfully added.")
            return redirect('daybook_list')
        return render(request, self.template_name, {'form': form, 'today': timezone.now().date()})

class DaybookListView(LoginRequiredMixin, View):
    template_name = 'hms/daybook/daybook_list.html'

    def get(self, request, *args, **kwargs):
        today = timezone.now().date()
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        search_query = request.GET.get('search')
        show_all = request.GET.get('show_all') == 'true'

        # Filter entries based on user role
        if request.user.is_superuser or request.user.is_staff:
            # Admin or superuser can see all entries
            daybook_entries = Daybook.objects.all()
        else:
            # Regular users can only see their own entries
            daybook_entries = Daybook.objects.filter(user=request.user)  # Filter by user

        if start_date:
            daybook_entries = daybook_entries.filter(date__gte=start_date)
        if end_date:
            daybook_entries = daybook_entries.filter(date__lte=end_date)
        if search_query:
            daybook_entries = daybook_entries.filter(
                Q(activity__icontains=search_query) |
                Q(custom_activity__icontains=search_query) |
                Q(remark__icontains=search_query)
            )

        if not show_all:
            daybook_entries = daybook_entries.filter(date=today)

        # Pagination
        paginator = Paginator(daybook_entries, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Aggregations
        todays_expenses = daybook_entries.filter(date=today)
        total_todays_expenses = sum(expense.amount for expense in todays_expenses)
        total_expenses = daybook_entries.aggregate(total_amount=Sum('amount'))['total_amount'] or 0

        # Balance and carryover
        current_balance_record = Balance.objects.filter(user=request.user).first()
        current_balance = current_balance_record.amount if current_balance_record else 0
        carryover_amount = current_balance_record.carryover_amount if current_balance_record else 0

        context = {
            'page_obj': page_obj,
            'total_balance': current_balance,
            'carryover_amount': carryover_amount,
            'todays_expense': total_todays_expenses,
            'total_expenses': total_expenses,
            'start_date': start_date,
            'end_date': end_date,
            'show_all': show_all,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        if 'reset_expenses' in request.POST:
            Daybook.objects.filter(user=request.user).delete()
            Balance.objects.filter(user=request.user).delete()
            return redirect('daybook/daybook_list')

def export_daybook_to_csv(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="daybook.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Activity', 'Custom Activity', 'Amount', 'Remark'])

    daybook_entries = Daybook.objects.filter(user=request.user)  # Filter by user
    if start_date:
        daybook_entries = daybook_entries.filter(date__gte=start_date)
    if end_date:
        daybook_entries = daybook_entries.filter(date__lte=end_date)

    for entry in daybook_entries:
        writer.writerow([entry.date, entry.activity, entry.custom_activity or '', entry.amount, entry.remark or ''])

    return response

class BalanceUpdateView(LoginRequiredMixin, View):
    template_name = 'hms/daybook/update_balance.html'

    def get(self, request, *args, **kwargs):
        form = BalanceUpdateForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = BalanceUpdateForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            action = form.cleaned_data['action']
            balance, created = Balance.objects.get_or_create(user=request.user, defaults={'amount': 0})

            if action == 'add':
                balance.amount += amount
                action_message = "added"
            elif action == 'deduct':
                balance.amount = max(0, balance.amount - amount)
                action_message = "deducted"

            balance.save()
            message = f"Balance has been {action_message} by {amount}. Current balance: {balance.amount}"
            messages.success(request, message)
            return redirect('daybook_list')
        return render(request, self.template_name, {'form': form})

# NICU Vitals Views

@login_required
def add_nicu_vitals(request, ipd_id):
    ipd = get_object_or_404(IPD, id=ipd_id)
    today = localdate()

    TIME_SLOTS = [
        ("08:00", "08 AM"),
        ("10:00", "10 AM"),
        ("12:00", "12 PM"),
        ("14:00", "2 PM"),
        ("16:00", "4 PM"),
        ("18:00", "6 PM"),
        ("20:00", "8 PM"),
        ("22:00", "10 PM"),
        ("23:59", "12 AM"),
        ("02:00", "2 AM"),
        ("04:00", "4 AM"),
        ("06:00", "6 AM"),
    ]
    
    # Fetch existing vitals for today
    existing_vitals = NICUVitals.objects.filter(ipd=ipd, date=today)
    existing_vitals_dict = {f"{vital.time.strftime('%H:%M')}": vital for vital in existing_vitals}

    URINE_CHOICES = [('', ''), ('nil', 'Nil'), ('ml', 'ML')]
    numeric_fields = ['temperature', 'respiratory_rate', 'pulse_rate', 'cft', 'spo2', 'oxygen', 'iv_fluids', 'by_nasogastric', 'oral', 'ift']
    boolean_fields = ['seizure', 'retraction', 'breastfeeding', 'stool', 'vomiting']
    dropdown_fields = ['skin_color', 'urine']  # Adding skin_color dropdown field

    SKIN_COLOR_CHOICES = [
        ('', ''),
        ('pink', 'Pink (Normal)'),
        ('pallor', 'Pallor (Pale)'),
        ('jaundiced', 'Jaundiced (Yellowish)'),
        ('cyanotic', 'Cyanotic (Bluish)'),
        ('mottled', 'Mottled (Blotchy)'),
        ('erythematous', 'Erythematous (Red/Flushed)'),
        ('grayish', 'Grayish'),
        ('dusky', 'Dusky (Bluish-Gray)'),
    ]

    if request.method == "POST":
        for time, label in TIME_SLOTS:
            time_obj = datetime.strptime(time, "%H:%M").time()  # Convert string to time object
            # Get or create a NICUVitals entry for this time slot
            vitals, created = NICUVitals.objects.get_or_create(ipd=ipd, date=today, time=time_obj)

            # Handle Urine Output
            urine_value = request.POST.get(f"urine_{time}", "").strip()
            ml_value = request.POST.get(f"urine_ml_{time.replace(':', '')}", "").strip()

            if urine_value:
                vitals.urine = urine_value
                if urine_value == "ml" and ml_value:
                    vitals.urine_value = float(ml_value)
                else:
                    vitals.urine_value = None
            else:
                # Preserve existing urine value if no new value is provided
                if not created:
                    existing_vital = existing_vitals_dict.get(time)
                    if existing_vital:
                        vitals.urine = existing_vital.urine
                        vitals.urine_value = existing_vital.urine_value

            # Debugging: Print urine values for each time slot
            print(f"Time: {time}, Urine: {vitals.urine}, Urine Value: {vitals.urine_value}")

            # Update fields safely from request.POST
            for field in numeric_fields:
                field_name = f"{field}_{time}"
                value = request.POST.get(field_name, "").strip()  # Get value, handle missing values
                if value:  # If value is not empty
                    setattr(vitals, field, float(value))
                else:
                    setattr(vitals, field, None)  # Default to NULL

            for field in boolean_fields:
                field_name = f"{field}_{time}"
                setattr(vitals, field, request.POST.get(field_name) == "on")  # Checkbox handling

            # Update dropdown fields
            for field in dropdown_fields:
                field_name = f"{field}_{time}"
                setattr(vitals, field, request.POST.get(field_name, ""))

            vitals.save()

        messages.success(request, "NICU Vitals recorded successfully.")
        return redirect('view_nicu_vitals', ipd_id=ipd.id)

    return render(request, 'hms/vitals/add_vitals.html', {
        'ipd': ipd,
        'existing_vitals': existing_vitals,
        'existing_vitals_dict': existing_vitals_dict,  # Pass existing data
        'time_slots': TIME_SLOTS,
        'numeric_fields': numeric_fields,
        'boolean_fields': boolean_fields,
        'dropdown_fields': dropdown_fields,  # Passing dropdown fields
        'skin_color_choices': SKIN_COLOR_CHOICES,  # Passing choices for template
        'urine_choices': URINE_CHOICES,  # Fixed variable name
    })

@login_required
def view_nicu_vitals(request, ipd_id):
    ipd = get_object_or_404(IPD, id=ipd_id)
    vitals_list = NICUVitals.objects.filter(ipd=ipd).order_by('-date')
    fluid_totals = calculate_total_fluids(vitals_list)
    grouped_vitals = {date: list(group) for date, group in groupby(vitals_list, key=attrgetter('date'))}
    patient = ipd.patient
    age = patient.age
    weight = patient.weight

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':  # Check if AJAX request
        vitals_data = [
            {
                "temperature": vital.temperature,
                "respiratory_rate": vital.respiratory_rate,
                "pulse_rate": vital.pulse_rate,
                "cft": vital.cft,
                "skin_color": vital.get_skin_color_display(),  # Get human-readable choice
                "seizure": "Yes" if vital.seizure else "No",
                "spo2": vital.spo2,
                "oxygen": vital.oxygen or "N/A",
                "retraction": "Yes" if vital.retraction else "No",
                "iv_fluids": vital.iv_fluids,
                "by_nasogastric": vital.by_nasogastric,
                "oral": vital.oral,
                "breastfeeding": "Yes" if vital.breastfeeding else "No",
                "urine": vital.urine,
                "urine_value": vital.urine_value,
                "stool": "Yes" if vital.stool else "No",
                "ift": vital.ift,
                "vomiting": "Yes" if vital.vomiting else "No",
            }
            for vital in vitals_list
        ]
        return JsonResponse({"vitals": vitals_data, "fluid_totals": fluid_totals, "age": age, "weight": weight})
    
    return render(request, 'hms/vitals/view_vitals.html', {
        'vitals_list': vitals_list,
        'ipd': ipd,
        'fluid_totals': fluid_totals,
        'age': age,
        'weight': weight,
        'grouped_vitals':grouped_vitals
    })

def calculate_total_fluids(vitals_list):
    """
    Calculate total input and output of fluids in specific time groups, grouped by date.
    """
    time_groups = {
        "Morning (08 AM - 12 PM)": ["08:00", "10:00", "12:00"],
        "Afternoon (02 PM - 06 PM)": ["14:00", "16:00", "18:00"],
        "Night (08 PM - 12 AM)": ["20:00", "22:00", "23:59"],
        "Early Morning (02 AM - 06 AM)": ["02:00", "04:00", "06:00"],
    }

    # Group vitals by date
    date_wise_totals = defaultdict(lambda: {group: {"input": 0, "output": 0} for group in time_groups})

    for vital in vitals_list:
        date_str = vital.date.strftime("%Y-%m-%d")  # Extract the date
        time_str = vital.time.strftime("%H:%M")  # Extract the time

        # Find the time group for the current vital
        for group, times in time_groups.items():
            if time_str in times:
                # Calculate input and output for the current time group and date
                date_wise_totals[date_str][group]["input"] += (
                    (vital.iv_fluids or 0) + 
                    (vital.by_nasogastric or 0) + 
                    (vital.oral or 0) + 
                    (vital.ift or 0)
                )
                date_wise_totals[date_str][group]["output"] += vital.urine_value or 0

    return dict(date_wise_totals)  # Convert defaultdict to a regular dictionary

# NICU Medication Views
class NICUMedicationRecordListView(ListView):
    """View to list all medications for a specific IPD admission."""
    model = NICUMedicationRecord
    template_name = "hms/nicumedication/nicu_medication_list.html"
    context_object_name = "medications"

    def get_queryset(self):
        """Fetch all medications for the given IPD admission."""
        ipd_id = self.kwargs.get("ipd_id")
        return NICUMedicationRecord.objects.filter(ipd_admission_id=ipd_id)

    def get_context_data(self, **kwargs):
        """Pass additional context: patient info and IPD ID."""
        context = super().get_context_data(**kwargs)
        ipd_id = self.kwargs.get("ipd_id")

        # Get the first medication to find the patient
        medications = context["medications"]
        first_medication = medications.first() if medications.exists() else None

        # Fetch the patient either from medication or directly from IPD
        patient = first_medication.patient if first_medication else None
        if not patient:
            try:
                patient = Patient.objects.get(ipd__id=ipd_id)
            except Patient.DoesNotExist:
                patient = None

        # Add patient details to the context
        context["patient"] = patient
        context["patient_name"] = patient.user.full_name if patient else "Unknown Patient"
        context["ipd_id"] = ipd_id  # For the "Add Medication" button
        context['fluid_data'] = FluidRequirement.objects.filter(ipd_admission=ipd_id)


        return context

class NICUMedicationRecordCreateView(CreateView):
    """View to add a new NICU medication record."""
    model = NICUMedicationRecord
    form_class = NICUMedicationRecordForm
    template_name = "hms/nicumedication/nicu_medication_form.html"

    def get_success_url(self):
        """Redirect to medication list after adding a record."""
        return reverse_lazy("nicu_medication_list", kwargs={"ipd_id": self.kwargs["ipd_id"]})

    def get_initial(self):
        """Set initial data for the form, including IPD and patient."""
        ipd = get_object_or_404(IPD, id=self.kwargs["ipd_id"])
        print(f"IPD: {ipd}, Patient: {getattr(ipd, 'patient', None)}")  # Debugging output
        return {
            "ipd_admission": ipd,
            "patient": ipd.patient,  # Ensure patient is set
        }

    def get_context_data(self, **kwargs):
        """Pass IPD ID to the template for better form handling."""
        context = super().get_context_data(**kwargs)
        ipd = get_object_or_404(IPD, id=self.kwargs["ipd_id"]) 
        context["ipd_id"] = self.kwargs["ipd_id"]
        context["prescriptions"] = Prescription.objects.filter(ipd=ipd)
        return context

    def form_valid(self, form):
        """Assign IPD and patient to the form instance before saving."""
        ipd = get_object_or_404(IPD, id=self.kwargs["ipd_id"])
        form.instance.ipd_admission = ipd  # Assign IPD admission
        form.instance.patient = ipd.patient  # Assign patient from IPD
        print(f"Form data before saving: {form.cleaned_data}")  # Debugging output
        return super().form_valid(form)

    def get_form_kwargs(self):
        """Pass IPD admission explicitly to the form."""
        kwargs = super().get_form_kwargs()
        ipd = get_object_or_404(IPD, id=self.kwargs["ipd_id"])
        kwargs["ipd_admission"] = ipd  # Pass IPD admission to the form
        return kwargs

class NICUMedicationRecordUpdateView(UpdateView):
    """View to update an existing NICU medication record."""
    model = NICUMedicationRecord
    form_class = NICUMedicationRecordForm
    template_name = "hms/nicumedication/nicu_medication_form.html"

    def get_success_url(self):
        """Redirect to medication list after successful update."""
        ipd_admission = getattr(self.object, 'ipd_admission', None)
        if ipd_admission:
            return reverse("nicu_medication_list", kwargs={"ipd_id": ipd_admission.id})
        return reverse("nicu_medication_list")

    def get_form_kwargs(self):
        """Pass IPD admission to the form for validation."""
        kwargs = super().get_form_kwargs()
        record = self.get_object()
        if not record.ipd_admission:
            raise ValueError("IPD admission is missing for this record.")
        kwargs["ipd_admission"] = record.ipd_admission
        return kwargs

    def get_context_data(self, **kwargs):
        """Add IPD ID to the template context for better UI handling."""
        context = super().get_context_data(**kwargs)
        context["ipd_id"] = getattr(self.object.ipd_admission, 'id', None)
        return context

def delete_nicu_medication(request, pk):
    """Delete a NICU medication record."""
    record = get_object_or_404(NICUMedicationRecord, pk=pk)
    ipd_id = record.ipd_admission.id

    if request.method == "POST":
        record.delete()
        return redirect("nicu_medication_list", ipd_id=ipd_id)

    return render(request, "hms/nicumedication/nicu_medication_confirm_delete.html", {"record": record})

# Medicine and Diluent Views
def manage_medicine_diluent(request):
    medicine_form = MedicineForm()
    diluent_form = DiluentForm()
    vial_form = VialForm()
    
    medicines = Medicine.objects.all()
    diluents = Diluent.objects.all()
    vials = Vial.objects.all()
    vial_formset = None  # Initialized only if needed

    if request.method == "POST":
        # Add Medicine
        if "add_medicine" in request.POST:
            medicine_form = MedicineForm(request.POST)
            if medicine_form.is_valid():
                medicine_form.save()
                messages.success(request, "Medicine added successfully!")
                return redirect('manage_medicine_diluent')
            else:
                messages.error(request, "Failed to add medicine. Please check the form for errors.")

        # Add Vials to Existing Medicine
        elif "add_vials_to_medicine" in request.POST:
            selected_medicine_id = request.POST.get('selected_medicine')
            if selected_medicine_id:
                try:
                    selected_medicine = Medicine.objects.get(id=selected_medicine_id)
                    vial_formset = MedicineVialFormSet(request.POST, instance=selected_medicine)
                    if vial_formset.is_valid():
                        vial_formset.save()
                        messages.success(request, "Vials added to medicine successfully!")
                        return redirect('manage_medicine_diluent')
                    else:
                        messages.error(request, "Vial formset is invalid. Please check the fields.")
                except Medicine.DoesNotExist:
                    messages.error(request, "Selected medicine not found.")
            else:
                messages.error(request, "Please select a medicine to attach vials.")

        # Add Diluent
        elif "add_diluent" in request.POST:
            diluent_form = DiluentForm(request.POST)
            if diluent_form.is_valid():
                diluent_form.save()
                messages.success(request, "Diluent added successfully!")
                return redirect('manage_medicine_diluent')
            else:
                messages.error(request, "Failed to add diluent. Please check the form for errors.")

        # Add Vial (independent)
        elif "add_vial" in request.POST:
            vial_form = VialForm(request.POST)
            if vial_form.is_valid():
                vial_form.save()
                messages.success(request, "Vial added successfully!")
                return redirect('manage_medicine_diluent')
            else:
                messages.error(request, "Failed to add vial. Please check the form for errors.")

    context = {
        'medicine_form': medicine_form,
        'diluent_form': diluent_form,
        'vial_form': vial_form,
        'vial_formset': vial_formset or MedicineVialFormSet(),
        'medicines': medicines,
        'diluents': diluents,
        'vials': vials,
    }
    return render(request, 'hms/medice_&_diluent/add_medicine_diluent.html', context)

def get_vials_for_medicine(request):
    medicine_id = request.GET.get('medicine_id')
    vials = MedicineVial.objects.filter(medicine_id=medicine_id)

    # Group vials by medicine and return a single medicine with all its vials
    vial_data = [{
        "id": vial.id,
        "label": vial.medicine.name,
        "strength_mg": vial.strength_mg,
        "volume_ml": vial.volume_ml
    } for vial in vials]
    
    # Assuming there is only one medicine selected, so returning it once with all vials
    return JsonResponse({"vials": vial_data})

def filter_medicines(request):
    medicine_type = request.GET.get('type')
    medicines = Medicine.objects.filter(medicine_type=medicine_type).distinct()

    # Prepare medicines data (grouped)
    medicine_data = [{"id": medicine.id, "name": medicine.name} for medicine in medicines]
    
    return JsonResponse({"medicines": medicine_data})

def medicine_list_api(request):
    medicine_type = request.GET.get('type')
    medicines = Medicine.objects.all()
    
    if medicine_type:
        medicines = medicines.filter(medicine_type=medicine_type)
    
    data = [{'id': m.id, 'name': m.name} for m in medicines]
    return JsonResponse(data, safe=False)

def medicine_detail_api(request, pk):
    try:
        medicine = Medicine.objects.get(pk=pk)
        data = {
            'id': medicine.id,
            'name': medicine.name,
            'medicine_type': medicine.medicine_type
        }
        return JsonResponse(data)
    except Medicine.DoesNotExist:
        return JsonResponse({'error': 'Medicine not found'}, status=404)
    

    
def delete_medicine(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    medicine.delete()
    return redirect('manage_medicine_diluent')

def delete_diluent(request, pk):
    diluent = get_object_or_404(Diluent, pk=pk)
    diluent.delete()
    return redirect('manage_medicine_diluent')

def delete_vial(request, pk):
    vial = get_object_or_404(Vial, pk=pk)
    vial.delete()
    messages.success(request, "Vial deleted successfully!")
    return redirect('manage_medicine_diluent')



class NICUFluidListView(ListView):
    model = FluidRequirement
    template_name = "hms/nicumedication/nicu_medication_list.html"
    context_object_name = "fluid_data"

    def get_queryset(self):
        ipd_id = self.kwargs.get("ipd_id")
        return FluidRequirement.objects.filter(ipd_admission_id=ipd_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ipd_id = self.kwargs.get("ipd_id")
        context["ipd_id"] = ipd_id
        context["fluid_data"] = FluidRequirement.objects.filter(ipd_admission_id=ipd_id)  # Ensure this key is used in template
        return context

class NICUFluidAddView(CreateView):
    model = FluidRequirement
    form_class = NICUFluidForm
    template_name = "hms/nicumedication/nicu_fluid_form.html"

    def get_success_url(self):
        return reverse_lazy("nicu_medication_list", kwargs={"ipd_id": self.kwargs["ipd_id"]})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ipd_id"] = self.kwargs["ipd_id"]
        return context

    def form_valid(self, form):
        ipd_id = self.kwargs.get("ipd_id")
        form.instance.ipd_admission_id = ipd_id
        return super().form_valid(form)


class NICUFluidUpdateView(UpdateView):
    model = FluidRequirement
    form_class = NICUFluidForm
    template_name = "hms/nicumedication/nicu_fluid_form.html"

    def get_success_url(self):
        ipd_id = self.object.ipd_admission_id
        return reverse_lazy("nicu_medication_list", kwargs={"ipd_id": ipd_id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ipd_id"] = self.object.ipd_admission_id
        return context




class NICUFluidDeleteView(DeleteView):
    model = FluidRequirement
    template_name = "hms/nicumedication/nicu_fluid_confirm_delete.html"

    def get_success_url(self):
        ipd_id = self.object.ipd_admission_id
        return reverse_lazy("nicu_medication_list", kwargs={"ipd_id": ipd_id})



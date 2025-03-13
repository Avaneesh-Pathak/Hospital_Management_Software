import io
import csv
import datetime
import logging
from xhtml2pdf import pisa
from decimal import Decimal
from django.db import models
from django.views import View
from django.db.models import Q
from django.utils import timezone
from reportlab.pdfgen import canvas
from django.http import JsonResponse
from django.http import FileResponse
from django.urls import reverse_lazy
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from django.shortcuts import render
from django.contrib import messages
from django.utils.timezone import now
from django.db.models import Count,Sum
from datetime import datetime ,timedelta
from reportlab.lib.pagesizes import letter
from django.utils.timezone import localdate
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.utils.dateparse import parse_time
from django.template.loader import get_template
from django.db.models.functions import TruncDate
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect,get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView
from .models import (
    CustomUser, Patient, Doctor, Appointment, Billing, EmergencyCase, OPD, IPD, Expense, Employee, Room, PatientReport,Prescription,
    License,Asset,Maintenance,AccountingRecord,Daybook,Balance,PatientTransfer,NICUVitals,NICUMedicationRecord
    
)
from .forms import (
    PatientRegistrationForm, ExpenseForm, BillingForm, OPDForm, DoctorForm, EmployeeForm, RoomForm, EmergencyCaseForm, ProfileUpdateForm,PatientReportForm,
    PrescriptionForm,LicenseForm,AssetForm,MaintenanceForm,BalanceUpdateForm,DaybookEntryForm,NICUVitalsForm,NICUMedicationRecordForm
)

logger = logging.getLogger(__name__)


def signup(request):
    if request.method == "POST":
        full_name = request.POST['full_name']
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password == confirm_password:
            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already taken!")
            elif User.objects.filter(email=email).exists():
                messages.error(request, "Email already registered!")
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                user.first_name = full_name
                user.save()
                messages.success(request, "Account created successfully! You can now log in.")
                return redirect('login')
        else:
            messages.error(request, "Passwords do not match!")

    return render(request, 'hms/auth/signup.html')


def user_login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')  # Redirect to dashboard after login
        else:
            messages.error(request, "Invalid username or password!")

    return render(request, 'hms/auth/login.html')


def user_logout(request):
    logout(request)
    return redirect('login')


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

    return render(request, "hms/profile.html", {"form": form})

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

@login_required
def dashboard(request):
    total_patients = Patient.objects.count()
    total_doctors = Doctor.objects.count()
    total_appointments = Appointment.objects.count()
    total_revenue = Billing.objects.aggregate(total=Sum('total_amount'))['total'] or 0
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

    # Prepare data for Chart.js
    daily_patient_labels = [entry['date'].strftime('%Y-%m-%d') for entry in patient_trend]
    daily_patient_data = [entry['count'] for entry in patient_trend]

    # 🚀 Room Statistics
    total_rooms = Room.objects.count()
    available_rooms_count = Room.objects.filter(is_available=True).count()  # ✅ Fixed
    booked_rooms = total_rooms - available_rooms_count  # ✅ Fixed

    # Count rooms by type and available rooms by type
    room_type_data = {}
    room_type_counts = Room.objects.values('room_type').annotate(total=Count('id'))
    available_rooms = Room.objects.filter(is_available=True).values('room_type').annotate(available=Count('id'))

    for room in room_type_counts:
        room_type_data[room['room_type']] = {'total': room['total'], 'available': 0}

    for room in available_rooms:
        if room['room_type'] in room_type_data:
            room_type_data[room['room_type']]['available'] = room['available']

    expiring_licenses = License.objects.filter(expiry_date__lte=warning_period, expiry_date__gte=today)
    expiring_assets = Asset.objects.filter(warranty_expiry__lte=warning_period, warranty_expiry__gte=today)
    due_maintenance = Maintenance.objects.filter(next_due_date__lte=warning_period, next_due_date__gte=today)

    context = {
        'total_patients': total_patients,
        'total_doctors': total_doctors,
        'total_appointments': total_appointments,
        'total_revenue': total_revenue,
        'emergency_cases_today': emergency_cases_today,
        'upcoming_appointments': upcoming_appointments,
        'daily_patient_labels': daily_patient_labels,
        'daily_patient_data': daily_patient_data,
        'total_rooms': total_rooms,
        'available_rooms_count': available_rooms_count,  # ✅ Fixed
        'booked_rooms': booked_rooms,  # ✅ Fixed
        'room_type_data': room_type_data,  # Dictionary of room counts & available rooms by type
        'expiring_licenses': expiring_licenses,
        'expiring_assets': expiring_assets,
        'due_maintenance': due_maintenance,
        
    }

    return render(request, 'hms/dashboard.html', context)



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
    billing = Billing.objects.filter(patient=patient).first()
    reports = PatientReport.objects.filter(patient=patient)

    context = {
        'patient': patient,
        'opd_records': opd_records,
        'ipd_record': ipd_record,
        'expenses': expenses,
        'billing': billing,
        'reports': reports,
        'profile_picture': patient.profile_picture.url if patient.profile_picture else None  # Ensuring profile picture is included
    }
    return render(request, 'hms/patient/patient_profile.html', context)


@login_required
def upload_patient_report(request, patient_code):
    patient = get_object_or_404(Patient, patient_code=patient_code)

    if request.method == "POST":
        form = PatientReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.patient = patient
            report.save()
            return redirect('view_ipd_report', patient_code=patient_code)  # Redirect to profile
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

@login_required
def doctors(request):
    doctors = Doctor.objects.all()
    return render(request, 'hms/doctors.html', {'doctors': doctors})

@login_required
def doctor_detail(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    return render(request, 'hms/doctor_detail.html', {'doctor': doctor})

@login_required
def add_doctor(request):
    if request.method == 'POST':
        form = DoctorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('doctors')
    else:
        form = DoctorForm()
    return render(request, 'hms/add_doctor.html', {'form': form})

@login_required
def update_doctor(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    if request.method == 'POST':
        form = DoctorForm(request.POST, instance=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Doctor details updated successfully!')
            return redirect('doctors')
    else:
        form = DoctorForm(instance=doctor)
    return render(request, 'hms/update_doctor.html', {'form': form, 'doctor': doctor})

def appointments_update(request):
    doctors  = Doctor.objects.all()  
    appointments = Appointment.objects.all()
    print("Doctors in view:", doctors)  # Debugging line
    return render(request, 'hms/appointments.html', {'appointments': appointments, 'doctors': doctors })

@login_required
def appointments(request):
    doctors  = Doctor.objects.all()  
    appointments = Appointment.objects.all()
    print("Doctors in view:", doctors)  # Debugging line
    return render(request, 'hms/appointment_list.html', {'appointments': appointments, 'doctors': doctors })

def fetch_appointments(request):
    appointments = Appointment.objects.select_related("doctor__user", "patient__user").values(
        "id", "doctor__user__full_name", "patient__user__full_name", "date", "time", "status"
    )
    return JsonResponse({"appointments": list(appointments)}, safe=False)

@login_required
def available_doctors(request):
    doctors = Doctor.objects.exclude(availability="").order_by("user__full_name")  # Assuming you have an 'is_available' field
    return render(request, 'hms/available_doctors.html', {'doctors': doctors})


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

    return render(request, 'hms/book_appointment.html', {'doctor': doctor, 'patient': patient})

def appointment_success(request, doctor_id):
    return render(request, 'hms/appointment_success.html', {'doctor_id': doctor_id})


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
def billing(request):
    bills = Billing.objects.all()

    # Add pending_amount calculation for each bill
    for bill in bills:
        bill.pending_amount = bill.total_amount - bill.paid_amount
    return render(request, 'hms/billing.html', {'bills': bills})



@login_required
def generate_bill(request, patient_code):
    patient = get_object_or_404(Patient, patient_code=patient_code)

    # Fetch expenses and total amount
    expenses = Expense.objects.filter(patient=patient)
    total_amount = sum(expense.cost for expense in expenses)

    # Create or update the bill
    bill, created = Billing.objects.get_or_create(patient=patient)
    bill.total_amount = total_amount
    bill.status = "paid" if bill.paid_amount >= total_amount else "pending"
    bill.save()

    # Calculate pending amount
    pending_amount = bill.total_amount - bill.paid_amount

    return render(request, 'hms/generate_bill.html', {
        'patient': patient,
        'expenses': expenses,
        'bill': bill,
        'pending_amount': pending_amount
    })


@login_required
def generate_bill_pdf(request, patient_code):
    # Get the patient
    patient = get_object_or_404(Patient, patient_code=patient_code)

    # Get the related billing information
    bill = get_object_or_404(Billing, patient=patient)

    # Get the patient's expenses
    expenses = Expense.objects.filter(patient=patient)

    # Create the response with PDF content
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="bill_{patient_code}.pdf"'

    # Create the PDF object using ReportLab
    p = canvas.Canvas(response)

    # PDF Title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, 800, "Hospital Bill Receipt")

    # Patient Details (Handling None values)
    p.setFont("Helvetica", 12)
    p.drawString(50, 770, f"Patient Name: {patient.user.full_name or 'N/A'}")
    p.drawString(50, 750, f"Patient Code: {patient.patient_code or 'N/A'}")
    p.drawString(50, 730, f"Phone Number: {patient.contact_number or 'N/A'}")
    p.drawString(50, 710, f"Address: {patient.address or 'N/A'}")
    p.drawString(50, 690, f"Blood Group: {patient.blood_group or 'N/A'}")

    # Table Header
    y_position = 650
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y_position, "Service/Item")
    p.drawString(300, y_position, "Cost (₹)")

    # Table Data (Handling None values)
    p.setFont("Helvetica", 12)
    y_position -= 20
    for expense in expenses:
        p.drawString(50, y_position, str(expense.category) if expense.category else "N/A")
        p.drawString(300, y_position, f"₹{expense.cost:.2f}" if expense.cost else "₹0.00")
        y_position -= 20  # Move to the next line

    # Payment Summary
    y_position -= 30
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y_position, "Total Amount:")
    p.drawString(300, y_position, f"₹{bill.total_amount:.2f}" if bill.total_amount else "₹0.00")

    y_position -= 20
    p.drawString(50, y_position, "Paid Amount:")
    p.drawString(300, y_position, f"₹{bill.paid_amount:.2f}" if bill.paid_amount else "₹0.00")

    y_position -= 20
    pending_amount = bill.total_amount - bill.paid_amount if bill.total_amount and bill.paid_amount else 0.00
    p.drawString(50, y_position, "Pending Amount:")
    p.drawString(300, y_position, f"₹{pending_amount:.2f}")

    # Status
    y_position -= 30
    p.setFont("Helvetica-Bold", 14)
    p.setFillColorRGB(0, 1, 0) if bill.status == "paid" else p.setFillColorRGB(1, 0, 0)
    p.drawString(50, y_position, f"Status: {bill.status.upper()}")

    # Save the PDF
    p.showPage()
    p.save()
    
    return response





@login_required
def add_expense(request):
    if request.method == "POST":
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save()
            
            # Update total amount in Billing
            billing, created = Billing.objects.get_or_create(patient=expense.patient)
            billing.update_total()
            
            messages.success(request, "Expense added successfully!")
            return redirect('billing')
    else:
        form = ExpenseForm()

    return render(request, 'hms/add_expense.html', {'form': form})  



@login_required
def pay_bill(request, billing_id):
    billing = get_object_or_404(Billing, id=billing_id)
    
    # Calculate pending amount in Python, not in the template
    pending_amount = billing.total_amount - billing.paid_amount

    if request.method == "POST":
        paid_amount = Decimal(request.POST.get('paid_amount', 0))
        
        if paid_amount <= 0:
            messages.error(request, "Amount must be greater than zero.")
        else:
            billing.paid_amount += paid_amount
            
            # Ensure that paid amount does not exceed total amount
            if billing.paid_amount >= billing.total_amount:
                billing.paid_amount = billing.total_amount
                billing.status = 'paid'
            else:
                billing.status = 'pending'
            
            billing.save()
            messages.success(request, f"₹{paid_amount} added to the bill!")
            return redirect('billing')

    return render(request, 'hms/pay_bill.html', {'billing': billing, 'pending_amount': pending_amount})




@login_required
def emergency(request):
    emergencies = EmergencyCase.objects.all()
    return render(request, 'hms/emergency.html', {'emergencies': emergencies})


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

    return render(request, 'hms/emergency.html', {'emergencies': emergencies_list})


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
    return render(request, "hms/add_emergency.html", {"form": form})

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
    return render(request, "hms/edit_emergency.html", {"form": form})

@login_required
def delete_emergency_case(request, emergency_id):
    emergency = get_object_or_404(EmergencyCase, id=emergency_id)

    if request.method == 'POST':
        # Delete the emergency case
        emergency.delete()
        messages.success(request, "Emergency case deleted successfully!")
        return redirect("emergency")

    # Render the confirmation page for GET requests
    return render(request, 'hms/delete_emergency.html', {'emergency': emergency})

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





@login_required
def ipd(request):
    ipds = IPD.objects.all()
    room = Room.objects.all()
    return render(request, 'hms/ipd/ipd.html', {'ipds': ipds,'room':room})

# def get_ipd_data(request):
    # ipds = IPD.objects.all().values(
    #     'id',
    #     'patient__user__full_name', 
    #     'room__room_number',
    #     'patient__patient_code',
    #     'calculate_total_cost',  # ✅ Get the room number
    #     'bed_number',         # ✅ Get the bed number
    #     'admitted_on', 
    #     'reason_for_admission'
    # )
    # return JsonResponse(list(ipds), safe=False)

def get_ipd_data(request):
    ipds = IPD.objects.all()

    ipd_data = []
    for ipd in ipds:
        ipd_data.append({
            'id': ipd.id,
            'patient__user__full_name': ipd.patient.user.full_name,
            'room__room_number': ipd.room.room_number if ipd.room else "N/A",
            'patient_code': ipd.patient.patient_code,
            'bed_number': ipd.bed_number,
            'admitted_on': ipd.admitted_on.strftime('%Y-%m-%d %H:%M:%S'),  
            'reason_for_admission': ipd.reason_for_admission,
            'total_cost': float(ipd.calculate_total_cost()),  # ✅ Call the method and convert it
        })

    return JsonResponse(ipd_data, safe=False)

# ✅ View IPD Report
def view_ipd_report(request, ipd_id):
    ipd = get_object_or_404(IPD, id=ipd_id)
    rooms = Room.objects.all()
    prescriptions = Prescription.objects.filter(ipd=ipd).order_by('-timing')
    reports = PatientReport.objects.filter(patient=ipd.patient).order_by('-uploaded_at')  # Fetch reports
    return render(request, 'hms/ipd/view_ipd_report.html', {'ipd': ipd, 'rooms': rooms,'prescriptions':prescriptions,'reports': reports})

    # ✅ Update IPD Room
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



@login_required
def discharge_patient(request, patient_code):
    patient = get_object_or_404(Patient, patient_code=patient_code)
    ipd_record = IPD.objects.filter(patient=patient, discharge_date__isnull=True).first()

    if not ipd_record:
        messages.error(request, "Patient is not currently admitted in IPD.")
        return redirect("patients")

    # Perform discharge
    ipd_record.discharge()
    messages.success(request, f"Patient {patient.user.full_name} has been discharged successfully.")

    # Generate discharge summary PDF and return response
    return discharge_summary_pdf(request, patient_code, action="Discharged")


def transfer_patient(request, patient_code):
    patient = get_object_or_404(Patient, patient_code=patient_code)

    # Fetch OPD visits
    opd_visits = OPD.objects.filter(patient=patient).order_by('-visit_date')

    # Fetch IPD records and prescriptions
    ipd_records = IPD.objects.filter(patient=patient)
    prescriptions = Prescription.objects.filter(ipd__in=ipd_records).order_by('-timing')

    # Fetch Transfer Details
    transfer = PatientTransfer.objects.filter(patient=patient).order_by('-transfer_date').first()

    context = {
        "patient": patient,
        "opd_visits": opd_visits,
        "ipd_records": ipd_records,
        "prescriptions": prescriptions,
        "transfer": transfer,
    }

    return render(request, "hms/transfer_summary.html", context)


def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    html = template.render(context_dict)
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="report.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse("Error generating PDF", status=500)
    
    return response

def discharge_summary_pdf(request, patient_code, action=None):
    patient = get_object_or_404(Patient, patient_code=patient_code)
    opd_visits = OPD.objects.filter(patient=patient).order_by('-visit_date')
    ipd_records = IPD.objects.filter(patient=patient)
    prescriptions = Prescription.objects.filter(ipd__in=ipd_records).order_by('-timing')

    context = {
        "patient": patient,
        "opd_visits": opd_visits,
        "ipd_records": ipd_records,
        "prescriptions": prescriptions,
        "action": action,  # Include action in context if needed
    }

    return render_to_pdf("hms/discharge_summary.html", context)

def transfer_summary_pdf(request, patient_code):
    patient = get_object_or_404(Patient, patient_code=patient_code)
    opd_visits = OPD.objects.filter(patient=patient).order_by('-visit_date')
    ipd_records = IPD.objects.filter(patient=patient)
    prescriptions = Prescription.objects.filter(ipd__in=ipd_records).order_by('-timing')
    transfer = PatientTransfer.objects.filter(patient=patient).order_by('-transfer_date').first()

    context = {
        "patient": patient,
        "opd_visits": opd_visits,
        "ipd_records": ipd_records,
        "prescriptions": prescriptions,
        "transfer": transfer,
    }

    return render_to_pdf("hms/transfer_summary.html", context)


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

    return render(request, 'hms/add_prescription.html', {'form': form, 'ipd': ipd})


@login_required
def opd(request):
    opds = OPD.objects.all()
    return render(request, 'hms/opd.html', {'opds': opds})

def fetch_opd(request):
    try:
        # Fetch OPD records with related patient and doctor details
        opd_records = OPD.objects.select_related("patient__user", "doctor__user").values(
            "id", 
            "patient__user__full_name", 
            "doctor__user__full_name", 
            "created_at",   # Use 'created_at' instead of 'visit_date'
            "diagnosis", 
            "symptoms", 
            "prescription", 
            "visit_type", 
            "payment_status", 
            "payment_amount", 
            "follow_up_date"
        )

        # Format the data for JSON response
        formatted_records = []
        for record in opd_records:
            formatted_records.append({
                "id": record["id"],
                "patient__user__full_name": record["patient__user__full_name"],
                "doctor__user__full_name": record["doctor__user__full_name"],
                "created_at": record["created_at"].strftime("%Y-%m-%d %H:%M:%S"),  # Format datetime
                "diagnosis": record["diagnosis"],
                "symptoms": record["symptoms"] or "N/A",  # Handle null values
                "prescription": record["prescription"] or "N/A",  # Handle null values
                "visit_type": record["visit_type"],
                "payment_status": record["payment_status"],
                "payment_amount": float(record["payment_amount"]),  # Convert Decimal to float
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
    return render(request, "hms/add_opd.html", {"patients": patients, "doctors": doctors})


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
        payment_status = request.POST.get("payment_status")
        payment_amount = request.POST.get("payment_amount")

        opd.doctor = Doctor.objects.get(id=doctor_id)
        opd.diagnosis = diagnosis
        opd.symptoms = symptoms
        opd.prescription = prescription
        opd.follow_up_date = follow_up_date
        opd.visit_type = visit_type
        opd.payment_status = payment_status
        opd.payment_amount = payment_amount
        opd.save()

        messages.success(request, "OPD visit updated successfully!")
        return redirect("opd")

    doctors = Doctor.objects.all()
    return render(request, "hms/update_opd.html", {"opd": opd, "doctors": doctors})



def opd_report_template(request, patient_id):
    # Fetch the OPD record for the specific patient
    opd = get_object_or_404(OPD, id=patient_id)
    
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
    }
    return render(request, 'hms/opd_report_template.html', context)



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

    return render(request, "hms/admit_patient.html", {"opd": opd, "rooms": available_rooms})

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



@login_required
def add_room(request):
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('add_room')
    else:
        form = RoomForm()
    return render(request, 'hms/add_room.html', {'form': form})



@login_required
def add_employee(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('employee_list')
    else:
        form = EmployeeForm()
    return render(request, 'hms/add_employee.html', {'form': form})



# Employee List
@login_required
def employee_list(request):
    employees = Employee.objects.all()
    return render(request, 'hms/employee_list.html', {'employees': employees})



# Edit Employee
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
    return render(request, 'hms/add_employee.html', {'form': form})

# Delete Employee
@login_required
def delete_employee(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == "POST":
        employee.delete()
        return redirect('employee_list')
    return render(request, 'hms/confirm_delete.html', {'object': employee})



@login_required
def pay_salary(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        payment_date = request.POST.get('payment_date')  # Get payment date from form
        employee.pay_salary(payment_date)  # Pass payment_date to the method
        return redirect('employee_list')
    return render(request, 'hms/pay_salary.html', {'employee': employee})




def license_list(request):
    licenses = License.objects.all()
    return render(request, 'hms/license_list.html', {'licenses': licenses})

def add_license(request):
    if request.method == 'POST':
        form = LicenseForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('license_list')
    else:
        form = LicenseForm()
    return render(request, 'hms/license_form.html', {'form': form})

def edit_license(request, id):
    license_instance = get_object_or_404(License, id=id)
    if request.method == 'POST':
        form = LicenseForm(request.POST, request.FILES, instance=license_instance)
        if form.is_valid():
            form.save()
            return redirect('license_list')
    else:
        form = LicenseForm(instance=license_instance)
    return render(request, 'hms/license_form.html', {'form': form})

def delete_license(request, id):
    license = get_object_or_404(License, id=id)
    license.delete()
    return redirect('license_list')


# Asset Views
def asset_list(request):
    assets = Asset.objects.all()
    return render(request, 'hms/asset_list.html', {'assets': assets})

def add_asset(request):
    if request.method == 'POST':
        form = AssetForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('asset_list')
    else:
        form = AssetForm()
    return render(request, 'hms/asset_form.html', {'form': form, 'title': 'Add Asset'})

def edit_asset(request, id):
    asset = get_object_or_404(Asset, id=id)
    if request.method == 'POST':
        form = AssetForm(request.POST, instance=asset)
        if form.is_valid():
            form.save()
            return redirect('asset_list')
    else:
        form = AssetForm(instance=asset)
    return render(request, 'hms/asset_form.html', {'form': form, 'title': 'Edit Asset'})

def delete_asset(request, id):
    asset = get_object_or_404(Asset, id=id)
    asset.delete()
    return redirect('asset_list')


# Maintenance Views
def maintenance_list(request):
    maintenance_records = Maintenance.objects.all()
    return render(request, 'hms/maintenance_list.html', {'maintenance_records': maintenance_records})

def add_maintenance(request):
    if request.method == 'POST':
        form = MaintenanceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('maintenance_list')
    else:
        form = MaintenanceForm()
    return render(request, 'hms/maintenance_form.html', {'form': form, 'title': 'Add Maintenance'})

def edit_maintenance(request, id):
    maintenance = get_object_or_404(Maintenance, id=id)
    if request.method == 'POST':
        form = MaintenanceForm(request.POST, instance=maintenance)
        if form.is_valid():
            form.save()
            return redirect('maintenance_list')
    else:
        form = MaintenanceForm(instance=maintenance)
    return render(request, 'hms/maintenance_form.html', {'form': form, 'title': 'Edit Maintenance'})

def delete_maintenance(request, id):
    maintenance = get_object_or_404(Maintenance, id=id)
    maintenance.delete()
    return redirect('maintenance_list')



def accounting_summary(request):
    today = timezone.now().date()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Convert to date objects if provided
    if start_date and end_date:
        start_date = timezone.datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = timezone.datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        start_date = today
        end_date = today

    # Today's Income and Expense from AccountingRecord
    today_income = AccountingRecord.objects.filter(
        transaction_type='income', date__date=today
    ).aggregate(total_income=Sum('amount'))['total_income'] or 0

    today_expense = AccountingRecord.objects.filter(
        transaction_type='expense', date__date=today
    ).aggregate(total_expense=Sum('amount'))['total_expense'] or 0

    # Today's Income and Expense from Daybook
    daybook_entries_today = Daybook.objects.filter(date=today)
    daybook_expense_today = daybook_entries_today.filter(activity__in=['pantry', 'fuel', 'office_expense', 'site_development', 'site_visit', 'printing', 'utility']).aggregate(total_expense=Sum('amount'))['total_expense'] or 0

    # Total Today's Income and Expense
    total_today_income = today_income
    total_today_expense = today_expense + daybook_expense_today
    total_today_savings = total_today_income - total_today_expense

    # Income & Expense in a Date Range
    range_income = AccountingRecord.objects.filter(
        transaction_type='income', date__date__range=(start_date, end_date)
    ).aggregate(total_income=Sum('amount'))['total_income'] or 0

    range_expense = AccountingRecord.objects.filter(
        transaction_type='expense', date__date__range=(start_date, end_date)
    ).aggregate(total_expense=Sum('amount'))['total_expense'] or 0

    # Excluding IPD and OPD
    excluded_sources = ['ipd', 'opd']
    other_income = AccountingRecord.objects.filter(
        transaction_type='income'
    ).exclude(source__in=excluded_sources).aggregate(total_income=Sum('amount'))['total_income'] or 0

    other_expense = AccountingRecord.objects.filter(
        transaction_type='expense'
    ).exclude(source__in=excluded_sources).aggregate(total_expense=Sum('amount'))['total_expense'] or 0

    # Separate IPD & OPD Reports
    ipd_income = AccountingRecord.objects.filter(
        transaction_type='income', source='ipd', date__date__range=(start_date, end_date)
    ).aggregate(total_income=Sum('amount'))['total_income'] or 0

    opd_income = AccountingRecord.objects.filter(
        transaction_type='income', source='opd', date__date__range=(start_date, end_date)
    ).aggregate(total_income=Sum('amount'))['total_income'] or 0

    # Billing Information
    total_billed = Billing.objects.filter(generated_on__date__range=(start_date, end_date)).aggregate(total_billed=Sum('total_amount'))['total_billed'] or 0
    total_paid = Billing.objects.filter(generated_on__date__range=(start_date, end_date)).aggregate(total_paid=Sum('paid_amount'))['total_paid'] or 0
    total_pending = total_billed - total_paid

    # Daybook Data
    daybook_entries = Daybook.objects.filter(date__range=(start_date, end_date))
    
    daybook_expense = daybook_entries.filter(activity__in=['pantry', 'fuel', 'office_expense', 'site_development', 'site_visit', 'printing', 'utility']).aggregate(total_expense=Sum('amount'))['total_expense'] or 0

    context = {
        'today_income': total_today_income,
        'today_expense': total_today_expense,
        'today_savings': total_today_savings,
        'range_income': range_income,
        'range_expense': range_expense,
        'range_profit': range_income - range_expense,
        'other_income': other_income,
        'other_expense': other_expense,
        'other_profit': other_income - other_expense,
        'ipd_income': ipd_income,
        'opd_income': opd_income,
        'total_billed': total_billed,
        'total_paid': total_paid,
        'total_pending': total_pending,
        'daybook_expense': daybook_expense,
        'start_date': start_date,
        'end_date': end_date,
        'daybook_entries': daybook_entries,
    }

    return render(request, 'hms/accounting_summary.html', context)







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
    

@login_required
def add_nicu_vitals(request, ipd_id):
    ipd = get_object_or_404(IPD, id=ipd_id)
    today = localdate()

    # Fetch existing vitals for today
    existing_vitals = NICUVitals.objects.filter(ipd=ipd, date=today)
    existing_vitals_dict = {f"{vital.time.strftime('%H:%M')}": vital for vital in existing_vitals}

    TIME_SLOTS = [
        ("08:00", "08 AM"),
        # ("09:00", "09 AM"),
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
    URINE_CHOICES = [('', ''), ('nil', 'Nil'), ('ml', 'ML')]
    numeric_fields = ['temperature (°F)', 'respiratory_rate(b/min)', 'pulse_rate(b/min)', 'cft(sec)', 'spo2 %', 'oxygen (lit./min)', 'iv_fluids(ml)', 'by_nasogastric (ml)', 'oral(ml) Katori & Spoon', 'ift(ML)']
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


from django.http import JsonResponse
from django.utils.timezone import localtime
from itertools import groupby
from operator import attrgetter
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



from collections import defaultdict
from datetime import datetime

from collections import defaultdict

from collections import defaultdict

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




class NICUMedicationRecordListView(ListView):
    model = NICUMedicationRecord
    template_name = "hms/nicumedication/nicu_medication_list.html"
    context_object_name = "medications"

    def get_queryset(self):
        ipd_id = self.kwargs.get("ipd_id")
        return NICUMedicationRecord.objects.filter(ipd_admission_id=ipd_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ipd_id = self.kwargs.get("ipd_id")

        # Fetch the first medication record (if exists)
        medications = context["medications"]
        first_medication = medications.first() if medications.exists() else None

        # Fetch the patient associated with the IPD admission
        patient = None
        if first_medication:
            patient = first_medication.patient
        else:
            # If no medication records exist, fetch the patient directly from the IPD admission
            try:
                patient = Patient.objects.get(ipd__id=ipd_id)
            except Patient.DoesNotExist:
                patient = None

        # Add patient details to the context
        context["patient"] = patient
        context["patient_name"] = patient.user.full_name if patient else "Unknown Patient"
        context["ipd_id"] = ipd_id  # Pass IPD ID for 'Add Medication' button
        return context


class NICUMedicationRecordCreateView(CreateView):
    model = NICUMedicationRecord
    form_class = NICUMedicationRecordForm
    template_name = "hms/nicumedication/nicu_medication_form.html"

    def get_success_url(self):
        return reverse_lazy("nicu_medication_list", kwargs={"ipd_id": self.kwargs["ipd_id"]})

    def get_initial(self):
        ipd = get_object_or_404(IPD, id=self.kwargs["ipd_id"])
        return {"ipd_admission": ipd, "patient": ipd.patient}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ipd_id"] = self.kwargs["ipd_id"]  # Pass IPD ID explicitly for the template
        return context

    def form_valid(self, form):
        ipd = get_object_or_404(IPD, id=self.kwargs["ipd_id"])
        form.instance.ipd_admission = ipd
        form.instance.patient = ipd.patient
        return super().form_valid(form)


from django.urls import reverse_lazy, reverse

class NICUMedicationRecordUpdateView(UpdateView):
    model = NICUMedicationRecord
    form_class = NICUMedicationRecordForm
    template_name = "hms/nicumedication/nicu_medication_form.html"

    def get_success_url(self):
        ipd_id = self.object.ipd_admission.id  # Ensure NICUMedicationRecord has a ForeignKey to IPD
        return reverse("nicu_medication_list", kwargs={"ipd_id": ipd_id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ipd_id"] = self.object.ipd_admission.id  # Pass ipd_id to the template
        return context


def delete_nicu_medication(request, pk):
    record = get_object_or_404(NICUMedicationRecord, pk=pk)
    ipd_id = record.ipd_admission.id  # Get the related IPD admission ID

    if request.method == "POST":
        record.delete()
        return redirect("nicu_medication_list", ipd_id=ipd_id)  # Pass ipd_id to the URL

    return render(request, "hms/nicumedication/nicu_medication_confirm_delete.html", {"record": record})









from django.shortcuts import render, redirect, get_object_or_404
from .models import Medicine, Diluent
from .forms import MedicineForm, DiluentForm

def manage_medicine_diluent(request):
    medicine_form = MedicineForm()
    diluent_form = DiluentForm()
    medicines = Medicine.objects.all()
    diluents = Diluent.objects.all()

    if request.method == "POST":
        if "add_medicine" in request.POST:
            print("POST Data:", request.POST)
            medicine_form = MedicineForm(request.POST)
            if medicine_form.is_valid():
                medicine_form.save()
                messages.success(request, "Medicine added successfully!")
                return redirect('manage_medicine_diluent')
            else:
                print("Medicine Form Errors:", medicine_form.errors)  # Debugging
                messages.error(request, "Failed to add medicine. Please check the form for errors.")

        elif "add_diluent" in request.POST:
            diluent_form = DiluentForm(request.POST)
            if diluent_form.is_valid():
                diluent_form.save()
                messages.success(request, "Diluent added successfully!")
                return redirect('manage_medicine_diluent')
            else:
                print("Diluent Form Errors:", diluent_form.errors)  # Debugging
                messages.error(request, "Failed to add diluent. Please check the form for errors.")

    context = {
        'medicine_form': medicine_form,
        'diluent_form': diluent_form,
        'medicines': medicines,
        'diluents': diluents
    }
    return render(request, 'hms/medice_&_diluent/add_medicine_diluent.html', context)



def delete_medicine(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    medicine.delete()
    return redirect('manage_medicine_diluent')


def delete_diluent(request, pk):
    diluent = get_object_or_404(Diluent, pk=pk)
    diluent.delete()
    return redirect('manage_medicine_diluent')

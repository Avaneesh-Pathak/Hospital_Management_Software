import datetime
import logging
from django.utils.timezone import now
from django.contrib import messages
from django.shortcuts import render, redirect,get_object_or_404
from django.db import models
from .models import CustomUser,Patient, Doctor, Appointment, Billing, Emergency,OPD, IPD
from .forms import PatientRegistrationForm

logger = logging.getLogger(__name__)


def dashboard(request):
    total_patients = Patient.objects.count()
    total_doctors = Doctor.objects.count()
    total_appointments = Appointment.objects.count()

    total_revenue = Billing.objects.aggregate(total=models.Sum('total_amount'))['total'] or 0

    today = datetime.date.today()
    emergency_cases_today = Emergency.objects.filter(admitted_at__date=today).count()

    upcoming_appointments = Appointment.objects.filter(date__gte=now()).order_by('date')

    context = {
        'total_patients': total_patients,
        'total_doctors': total_doctors,
        'total_appointments': total_appointments,
        'total_revenue': total_revenue,
        'emergency_cases_today': emergency_cases_today,
        'upcoming_appointments': upcoming_appointments
    }

    return render(request, 'hms/dashboard.html', context)




def patients(request):
    logger.info("Fetching all patients.")
    patients = Patient.objects.all()
    logger.info(f"Total patients retrieved: {len(patients)}")
    return render(request, 'hms/patients.html', {'patients': patients})


def patient_detail(request, patient_code):
    logger.info(f"Fetching details for patient with code: {patient_code}")
    patient = get_object_or_404(Patient, patient_code=patient_code)
    logger.info(f"Patient found: {patient.user.full_name}")
    return render(request, 'hms/patient_detail.html', {'patient': patient})


def register_patient(request):
    if request.method == "POST":
        logger.info("Received patient registration form submission.")
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            try:
                # Create user first
                user = CustomUser.objects.create(
                    full_name=form.cleaned_data['full_name'],
                    email=form.cleaned_data['email'],
                    contact_number=form.cleaned_data['contact_number'],
                    address=form.cleaned_data['address'],
                    username=form.cleaned_data['email']  # Username is email
                )
                user.save()
                logger.info(f"New user created: {user.full_name} ({user.email})")

                # Create the patient instance
                patient = Patient.objects.create(
                    user=user,
                    date_of_birth=form.cleaned_data['date_of_birth'],
                    aadhar_number=form.cleaned_data['aadhar_number'],
                    blood_group=form.cleaned_data['blood_group'],
                    guarantor_name=form.cleaned_data['guarantor_name'],
                    guarantor_address=form.cleaned_data['guarantor_address'],
                    guarantor_mobile=form.cleaned_data['guarantor_mobile'],
                    guarantor_relationship=form.cleaned_data['guarantor_relationship'],
                    guarantor_gender=form.cleaned_data['guarantor_gender'],
                )
                logger.info(f"New patient registered: {patient.user.full_name} (Code: {patient.patient_code})")
                return redirect('patients')  # Redirect to patients list
            except Exception as e:
                logger.error(f"Error occurred during patient registration: {e}")
        else:
            logger.warning("Patient registration form is invalid.")
    else:
        form = PatientRegistrationForm()
    return render(request, 'hms/register_patient.html', {'form': form})



def doctors(request):
    doctors = Doctor.objects.all()
    return render(request, 'hms/doctors.html', {'doctors': doctors})

def doctor_detail(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    return render(request, 'hms/doctor_detail.html', {'doctor': doctor})


def appointments(request):
    appointments = Appointment.objects.all()
    return render(request, 'hms/appointments.html', {'appointments': appointments})

def update_appointment_status(request):
    if request.method == "POST":
        appointment_id = request.POST.get("appointment_id")
        new_status = request.POST.get(f"status_{appointment_id}")

        appointment = get_object_or_404(Appointment, id=appointment_id)
        appointment.status = new_status
        appointment.save()

        messages.success(request, f"Appointment status updated to {new_status}.")
        return redirect("appointments")  # Redirect to appointments list

    return redirect("appointments")

def billing(request):
    bills = Billing.objects.all()
    return render(request, 'hms/billing.html', {'bills': bills})

def emergency(request):
    emergencies = Emergency.objects.all()
    return render(request, 'hms/emergency.html', {'emergencies': emergencies})

def ipd(request):
    ipds = IPD.objects.all()
    return render(request, 'hms/ipd.html', {'ipds': ipds})

def opd(request):
    opds = OPD.objects.all()
    return render(request, 'hms/opd.html', {'opds': opds})

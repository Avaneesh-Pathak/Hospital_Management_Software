import datetime
from django.shortcuts import render
from django.db import models
from .models import Patient, Doctor, Appointment, Billing, Emergency,OPD, IPD

def dashboard(request):
    total_patients = Patient.objects.count()
    total_doctors = Doctor.objects.count()
    total_appointments = Appointment.objects.count()

    total_revenue = Billing.objects.aggregate(total=models.Sum('total_amount'))['total'] or 0

    today = datetime.date.today()
    emergency_cases_today = Emergency.objects.filter(admitted_at__date=today).count()

    upcoming_appointments = Appointment.objects.filter(status='Scheduled').order_by('date')[:5]

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
    patients = Patient.objects.all()
    return render(request, 'hms/patients.html', {'patients': patients})

def doctors(request):
    doctors = Doctor.objects.all()
    return render(request, 'hms/doctors.html', {'doctors': doctors})

def appointments(request):
    appointments = Appointment.objects.all()
    return render(request, 'hms/appointments.html', {'appointments': appointments})

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

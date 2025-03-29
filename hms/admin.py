from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path

from django.shortcuts import render
from django.utils.timezone import now
from datetime import datetime, timedelta
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from .models import (
    Patient, Asset, License, Maintenance, Doctor, Appointment, 
    AccountingRecord, EmergencyCase, IPD, OPD, Billing, CustomUser, 
    Room, Expense, Employee, PatientReport, Daybook, Balance, NICUVitals, 
    NICUMedicationRecord, Medicine, Diluent, Vial
)

class CustomAdminSite(admin.AdminSite):
    site_header = "Hospital Management Dashboard"
    site_title = "Admin Panel"
    index_title = "Welcome to the Hospital Admin"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(self.dashboard_view), name="dashboard"),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        # Basic Statistics
        total_patients = Patient.objects.count()
        total_doctors = Doctor.objects.count()
        total_appointments = Appointment.objects.count()
        total_revenue = Billing.objects.aggregate(total=Sum('total_amount'))['total'] or 0
        today = datetime.today()
        warning_period = today + timedelta(days=30)
        emergency_cases_today = EmergencyCase.objects.filter(admitted_on__date=today).count()
        upcoming_appointments = Appointment.objects.filter(date__gte=now()).order_by('date')

        # Patient Registration Trend (Last 7 Days)
        last_week = today - timedelta(days=6)
        patient_trend = (
            Patient.objects.filter(created_at__date__gte=last_week)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )
        daily_patient_labels = [entry['date'].strftime('%Y-%m-%d') for entry in patient_trend]
        daily_patient_data = [entry['count'] for entry in patient_trend]

        # Room Statistics
        total_rooms = Room.objects.count()
        available_rooms_count = Room.objects.filter(is_available=True).count()
        booked_rooms = total_rooms - available_rooms_count

        # In your dashboard_view function
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

        # Expiring Data
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
            'available_rooms_count': available_rooms_count,
            'booked_rooms': booked_rooms,
            'room_type_data': room_type_data,
            'expiring_licenses': expiring_licenses,
            'expiring_assets': expiring_assets,
            'due_maintenance': due_maintenance,
        }

        return render(request, 'hms/admin/dashboard.html', context)



admin_site = CustomAdminSite(name='custom_admin')
admin_site.register(CustomUser)
admin_site.register(Patient)
admin_site.register(Doctor)
admin_site.register(Appointment)
admin_site.register(EmergencyCase)
admin_site.register(IPD)
admin_site.register(OPD)
admin_site.register(Billing)
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

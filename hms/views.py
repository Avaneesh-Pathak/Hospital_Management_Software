import datetime
import logging
from decimal import Decimal
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from django.utils.timezone import now
from django.contrib import messages
from django.shortcuts import render, redirect,get_object_or_404
from django.db import models
from .models import CustomUser,Patient, Doctor, Appointment, Billing, EmergencyCase,OPD, IPD,Expense,Employee,Room    
from .forms import PatientRegistrationForm,ExpenseForm, BillingForm,OPDForm ,DoctorForm,EmployeeForm,RoomForm,EmergencyCaseForm

logger = logging.getLogger(__name__)


def dashboard(request):
    total_patients = Patient.objects.count()
    total_doctors = Doctor.objects.count()
    total_appointments = Appointment.objects.count()

    total_revenue = Billing.objects.aggregate(total=models.Sum('total_amount'))['total'] or 0

    today = datetime.date.today()
    emergency_cases_today = EmergencyCase.objects.filter(admitted_on__date=today).count()

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


def add_doctor(request):
    if request.method == 'POST':
        form = DoctorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('doctor_list')
    else:
        form = DoctorForm()
    return render(request, 'hms/add_doctor.html', {'form': form})




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

    # Add pending_amount calculation for each bill
    for bill in bills:
        bill.pending_amount = bill.total_amount - bill.paid_amount

    return render(request, 'hms/billing.html', {'bills': bills})


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



def emergency(request):
    emergencies = EmergencyCase.objects.all()
    return render(request, 'hms/emergency.html', {'emergencies': emergencies})

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

def admit_emergency_patient(request, emergency_id):
    emergency_case = get_object_or_404(EmergencyCase, id=emergency_id)

    # Assign the first available room (modify logic as needed)
    available_room = Room.objects.filter(is_available=True).first()
    if available_room:
        ipd = IPD.objects.create(
            patient=emergency_case.patient,
            room=available_room,
            reason_for_admission=emergency_case.case_description
        )
        available_room.is_available = False
        available_room.save()

        # Remove from emergency list
        emergency_case.delete()

        messages.success(request, "Patient admitted to IPD successfully!")
        return redirect("ipd")

    messages.error(request, "No available rooms for admission!")
    return redirect("emergency")


def ipd(request):
    ipds = IPD.objects.all()
    return render(request, 'hms/ipd.html', {'ipds': ipds})

def opd(request):
    opds = OPD.objects.all()
    return render(request, 'hms/opd.html', {'opds': opds})

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

def update_opd(request, opd_id):
    opd = get_object_or_404(OPD, id=opd_id)

    if request.method == "POST":
        doctor_id = request.POST.get("doctor")
        diagnosis = request.POST.get("diagnosis")

        opd.doctor = Doctor.objects.get(id=doctor_id)
        opd.diagnosis = diagnosis
        opd.save()

        messages.success(request, "OPD visit updated successfully!")
        return redirect("opd")

    doctors = Doctor.objects.all()
    return render(request, "hms/update_opd.html", {"opd": opd, "doctors": doctors})

def admit_patient(request, opd_id):
    opd = get_object_or_404(OPD, id=opd_id)
    available_rooms = Room.objects.filter(is_available=True)

    if request.method == "POST":
        room_id = request.POST.get("room")  # Get selected room
        room = get_object_or_404(Room, id=room_id)

        # Create an IPD record for the patient
        ipd = IPD.objects.create(
            patient=opd.patient,
            room=room,
            reason_for_admission=opd.diagnosis  # Use OPD diagnosis as admission reason
        )

        # Mark the room as occupied
        room.is_available = False
        room.save()

        # Delete OPD entry since patient is admitted
        opd.delete()

        messages.success(request, "Patient admitted to IPD successfully!")
        return redirect("ipd")

    return render(request, "hms/admit_patient.html", {"opd": opd, "rooms": available_rooms})

def discharge_patient(request, ipd_id):
    """ Handles patient discharge and makes the room available again """
    ipd = get_object_or_404(IPD, id=ipd_id)
    ipd.discharge()
    return redirect('ipd')

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


def add_room(request):
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('add_room')
    else:
        form = RoomForm()
    return render(request, 'hms/add_room.html', {'form': form})

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
def employee_list(request):
    employees = Employee.objects.all()
    return render(request, 'hms/employee_list.html', {'employees': employees})

# Edit Employee
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
def delete_employee(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == "POST":
        employee.delete()
        return redirect('employee_list')
    return render(request, 'hms/confirm_delete.html', {'object': employee})




















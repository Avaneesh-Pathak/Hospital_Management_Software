from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import CustomUser,NICUVitals, Patient,Billing,Expense,OPD,Room, Doctor, Employee,EmergencyCase,PatientReport,Prescription,License,Asset,Maintenance,Daybook,NICUMedicationRecord,Medicine, Diluent

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ["full_name", "email", "contact_number", "address"]

        
class PatientRegistrationForm(forms.ModelForm):
    full_name = forms.CharField(max_length=255, required=True)
    email = forms.EmailField(required=True)
    contact_number = forms.CharField(max_length=15, required=True)
    address = forms.CharField(widget=forms.Textarea, required=True)
    gender = forms.ChoiceField(choices=CustomUser.GENDER_CHOICES, required=True)
    class Meta:
        model = Patient
        fields = [
            'date_of_birth', 'aadhar_number','weight',
            'blood_group', 'allergies', 'medical_history', 'current_medications', 'emergency_contact_name',
            'emergency_contact_number', 'emergency_contact_relationship', 'accompanying_person_name',
            'accompanying_person_contact', 'accompanying_person_relationship', 'accompanying_person_address',
            'profile_picture'
        ]
        exclude = ['user']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'allergies': forms.Textarea(attrs={'rows': 3}),
            'medical_history': forms.Textarea(attrs={'rows': 3}),
            'current_medications': forms.Textarea(attrs={'rows': 3}),
            'accompanying_person_address': forms.Textarea(attrs={'rows': 3}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'user' in self.fields:  # Only filter if the user field exists
            # Get all Doctor & Employee users
            doctor_users = CustomUser.objects.filter(groups__name='Doctor').values_list('id', flat=True)
            employee_users = CustomUser.objects.filter(groups__name='Employee').values_list('id', flat=True)

            # Exclude Doctor & Employee from user selection
            self.fields['user'].queryset = CustomUser.objects.exclude(id__in=doctor_users).exclude(id__in=employee_users)




class PatientReportForm(forms.ModelForm):
    class Meta:
        model = PatientReport
        fields = ['file_name', 'report_file', 'description']
        widgets = {
            'file_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Enter report name'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Enter description'}),
        }

        
class BillingForm(forms.ModelForm):
    class Meta:
        model = Billing
        fields = ['paid_amount']

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['patient', 'category', 'description', 'cost']


class OPDForm(forms.ModelForm):
    class Meta:
        model = OPD
        fields = [
            'patient', 'doctor', 'diagnosis', 'symptoms', 'prescription', 
            'follow_up_date', 'visit_type', 'payment_status', 'payment_amount'
        ]
        widgets = {
            'patient': forms.Select(attrs={'class': 'w-full p-2 border border-gray-300 rounded-md'}),
            'doctor': forms.Select(attrs={'class': 'w-full p-2 border border-gray-300 rounded-md'}),
            'diagnosis': forms.Textarea(attrs={'class': 'w-full p-2 border border-gray-300 rounded-md', 'rows': 3}),
            'symptoms': forms.Textarea(attrs={'class': 'w-full p-2 border border-gray-300 rounded-md', 'rows': 3}),
            'prescription': forms.Textarea(attrs={'class': 'w-full p-2 border border-gray-300 rounded-md', 'rows': 3}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full p-2 border border-gray-300 rounded-md'}),
            'visit_type': forms.Select(attrs={'class': 'w-full p-2 border border-gray-300 rounded-md'}),
            'payment_status': forms.Select(attrs={'class': 'w-full p-2 border border-gray-300 rounded-md'}),
            'payment_amount': forms.NumberInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded-md'}),
        }

    def clean_follow_up_date(self):
        follow_up_date = self.cleaned_data.get('follow_up_date')

        if follow_up_date in ["", None]:
            return None  # Ensure None instead of an empty string
        
        if isinstance(follow_up_date, str):
            try:
                follow_up_date = timezone.datetime.strptime(follow_up_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError("Invalid date format. Use YYYY-MM-DD.")
        
        return follow_up_date


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['room_number', 'room_type', 'total_beds', 'bed_price_per_day', 'is_available']
        widgets = {
            'room_number': forms.TextInput(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'room_type': forms.Select(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'total_beds': forms.NumberInput(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'bed_price_per_day': forms.NumberInput(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'is_available': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 text-blue-600 rounded focus:ring-blue-500',
            }),
        }

    def save(self, commit=True):
        room = super().save(commit=False)

        # Initialize available beds equal to total beds at the time of creation
        if room.total_beds:
            room.available_beds = room.total_beds

        if commit:
            room.save()
        return room

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['user', 'role', 'contact_number', 'hired_date', 'salary', 'last_payment_date', 'next_due_date']
        widgets = {
            'user': forms.Select(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'role': forms.TextInput(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'contact_number': forms.TextInput(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'hired_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'salary': forms.NumberInput(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'last_payment_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'next_due_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
        }

class DoctorForm(forms.ModelForm):
    user = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(is_staff=False),
        label="Select User",
        widget=forms.Select(attrs={
            'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
        })
    )

    class Meta:
        model = Doctor
        fields = ['user', 'specialization', 'contact_number', 'availability']
        widgets = {
            'specialization': forms.TextInput(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'contact_number': forms.TextInput(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'availability': forms.TextInput(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
        }


class EmergencyCaseForm(forms.ModelForm):
    class Meta:
        model = EmergencyCase
        fields = ['patient', 'referred_by', 'referrer_contact', 'emergency_type', 'case_description', 'severity']


class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['medication', 'dosage', 'timing']
        widgets = {
            'medication': forms.TextInput(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter medication',
            }),
            'dosage': forms.TextInput(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter dosage',
            }),
            'timing': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
        }






class LicenseForm(forms.ModelForm):
    class Meta:
        model = License
        fields = ['name', 'license_type', 'issue_date', 'expiry_date', 'document', 'status', 'renewed_by']
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = ['name', 'asset_type', 'purchase_date', 'warranty_expiry', 'quantity', 'location']
        widgets = {
            'purchase_date': forms.DateInput(attrs={'type': 'date'}),
            'warranty_expiry': forms.DateInput(attrs={'type': 'date'}),
        }

class MaintenanceForm(forms.ModelForm):
    class Meta:
        model = Maintenance
        fields = ['asset', 'maintenance_date', 'next_due_date', 'performed_by', 'notes']
        widgets = {
            'maintenance_date': forms.DateInput(attrs={'type': 'date'}),
            'next_due_date': forms.DateInput(attrs={'type': 'date'}),
        }





class DaybookEntryForm(forms.ModelForm):
    class Meta:
        model = Daybook
        fields = ['date', 'activity', 'custom_activity', 'amount', 'remark']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].initial = timezone.now().date()  # Set current date as the initial value

    def clean_date(self):
        date = self.cleaned_data.get('date')
        today = timezone.now().date()
        if date != today:
            raise forms.ValidationError("Please enter today's date.")
        return date
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        return amount
class BalanceUpdateForm(forms.Form):
    ACTION_CHOICES = [
        ('add', 'Add'),
        ('deduct', 'Deduct'),
    ]

    action = forms.ChoiceField(choices=ACTION_CHOICES, required=True)
    amount = forms.DecimalField(max_digits=10, decimal_places=2, required=True)




class NICUVitalsForm(forms.ModelForm):
    class Meta:
        model = NICUVitals
        fields = [
            'time','temperature', 'respiratory_rate', 'pulse_rate', 'cft', 'skin_color',
            'seizure', 'spo2', 'oxygen', 'retraction', 'iv_fluids', 'by_nasogastric',
            'oral', 'breastfeeding', 'urine', 'stool', 'ift', 'vomiting'
        ]
        widgets = {
            'temperature': forms.NumberInput(attrs={'step': '0.1', 'placeholder': 'Enter Temperature in °F'}),
            'respiratory_rate': forms.NumberInput(attrs={'min': 10, 'max': 100, 'placeholder': 'Breaths per minute'}),
            'pulse_rate': forms.NumberInput(attrs={'min': 50, 'max': 200, 'placeholder': 'Beats per minute'}),
            'cft': forms.NumberInput(attrs={'step': '0.1', 'placeholder': 'Capillary Refill Time (seconds)'}),
            'spo2': forms.NumberInput(attrs={'min': 0, 'max': 100, 'placeholder': 'SpO₂ %'}),
            'oxygen': forms.NumberInput(attrs={'min': 0, 'max': 100, 'placeholder': 'Oxygen Level (1-100%)'}),
            'iv_fluids': forms.NumberInput(attrs={'step': '1', 'placeholder': 'IV Fluid (ml)'}),
            'by_nasogastric': forms.NumberInput(attrs={'step': '1', 'placeholder': 'Nasogastric Intake (ml)'}),
            'oral': forms.NumberInput(attrs={'step': '1', 'placeholder': 'Oral Intake (ml)'}),
            'ift': forms.NumberInput(attrs={'step': '1', 'placeholder': 'IFT Intake (ml)'}),
            'urine': forms.Select(choices=[('nil', 'Nil'), ('ml', 'ML')]),
            'skin_color': forms.Select(choices=[('pink', 'Pink'), ('pallor', 'Pallor')]),
            'seizure': forms.Select(choices=[(True, 'Present'), (False, 'Absent')]),
            'retraction': forms.Select(choices=[(True, 'Yes'), (False, 'No')]),
            'breastfeeding': forms.Select(choices=[(True, 'Yes'), (False, 'No')]),
            'stool': forms.Select(choices=[(True, 'Yes'), (False, 'No')]),
            'vomiting': forms.Select(choices=[(True, 'Yes'), (False, 'No')]),
        }




class NICUMedicationRecordForm(forms.ModelForm):
    class Meta:
        model = NICUMedicationRecord
        fields = [
            "route", "medicine", "diluent", "dose_frequency", 
            "other_frequency", "dilution_volume", "duration", "sign"
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Placeholder for dilution volume
        self.fields["dilution_volume"].widget.attrs["placeholder"] = "Enter custom dilution volume in mL"

        # Hide 'other_frequency' field initially
        self.fields["other_frequency"].widget.attrs.update({
            "placeholder": "Specify custom frequency",
            "style": "display: none;",
        })




class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = ["name", "medicine_type", "standard_dose_per_kg"]
        widgets = {
            "medicine_type": forms.Select(choices=Medicine.MEDICINE_TYPE_CHOICES, attrs={"class": "form-control"}),
            "standard_dose_per_kg": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }
        labels = {
            "name": "Medicine Name",
            "medicine_type": "Type of Medicine",
            "standard_dose_per_kg": "Standard Dose (mg/kg/dose)",
        }

class DiluentForm(forms.ModelForm):
    compatible_medicine_types = forms.ModelMultipleChoiceField(
        queryset=Medicine.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Compatible Medicine Types",
    )

    class Meta:
        model = Diluent
        fields = ["name", "compatible_medicine_types", "standard_volume_per_kg"]
        widgets = {
            "standard_volume_per_kg": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }
        labels = {
            "name": "Diluent Name",
            "standard_volume_per_kg": "Standard Volume (mL/kg/dose)",
        }

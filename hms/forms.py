from django import forms
from django.utils import timezone
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from .models import CustomUser,NICUVitals, Patient,OPDBilling, IPDBilling, BillingItem, Payment, Expense,OPD,Room, Doctor, Employee,EmergencyCase,PatientReport,Prescription,License,Asset,Maintenance,Daybook,NICUMedicationRecord,Medicine, Diluent,Vial,FluidRequirement,IPD,MedicineVial

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ["full_name", "email", "contact_number", "address"]

        
from django import forms
from .models import Patient
from django.core.files.base import ContentFile
import base64

class PatientRegistrationForm(forms.ModelForm):
    full_name = forms.CharField(max_length=255, required=True)
    email = forms.EmailField(required=True)
    contact_number = forms.CharField(max_length=15, required=True)
    address = forms.CharField(widget=forms.Textarea, required=True)
    gender = forms.ChoiceField(choices=CustomUser.GENDER_CHOICES, required=True)
    captured_image = forms.CharField(widget=forms.HiddenInput(), required=False)  # 👈 add this

    class Meta:
        model = Patient
        fields = [
            'date_of_birth', 'aadhar_number', 'weight',
            'blood_group', 'allergies',
            'emergency_contact_name', 'emergency_contact_number',
            'emergency_contact_relationship', 'accompanying_person_address',
            'profile_picture'
        ]
        exclude = ['user']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'allergies': forms.Textarea(attrs={'rows': 3}),
            'accompanying_person_address': forms.Textarea(attrs={'rows': 3}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Handle captured webcam image
        image_data = self.cleaned_data.get('captured_image')
        if image_data:
            try:
                format, imgstr = image_data.split(';base64,')
                ext = format.split('/')[-1]
                file_name = f"profile_{self.cleaned_data['full_name'].replace(' ', '_')}.{ext}"
                instance.profile_picture = ContentFile(base64.b64decode(imgstr), name=file_name)
            except Exception as e:
                print("Image decoding error:", e)

        if commit:
            instance.save()
        return instance





class PatientReportForm(forms.ModelForm):
    class Meta:
        model = PatientReport
        fields = ['file_name', 'report_file', 'description']
        widgets = {
            'file_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Enter report name'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Enter description'}),
        }


class IPDForm(forms.ModelForm):
    class Meta:
        model = IPD
        fields = ['patient', 'room', 'bed_number', 'reason_for_admission']
        widgets = {
            'reason_for_admission': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'patient': forms.Select(attrs={'class': 'form-control'}),
            'room': forms.Select(attrs={'class': 'form-control', 'id': 'id_room'}),
            'bed_number': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(IPDForm, self).__init__(*args, **kwargs)

        if 'room' in self.data:
            try:
                room_id = int(self.data.get('room'))
                room = Room.objects.get(id=room_id)
                occupied = room.occupied_beds
                total = room.total_beds
                available = [(i, f"Bed {i}") for i in range(1, total + 1) if i not in occupied]
                self.fields['bed_number'].choices = available
            except (ValueError, TypeError, Room.DoesNotExist):
                pass
        elif self.instance.pk:
            room = self.instance.room
            total = room.total_beds
            occupied = room.occupied_beds
            available = [(i, f"Bed {i}") for i in range(1, total + 1) if i not in occupied or i == self.instance.bed_number]
            self.fields['bed_number'].choices = available
        else:
            self.fields['bed_number'].choices = []



class OPDQuickForm(forms.ModelForm):
    class Meta:
        model = OPD
        fields = ['patient', 'doctor', 'visit_type']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'form-control',  # Let CSS handle layout
                'style': 'margin-bottom: 10px;'  # Slight spacing between fields
            })


class OPDForm(forms.ModelForm):
    class Meta:
        model = OPD
        fields = [
            'patient', 'doctor', 'diagnosis', 'symptoms', 'prescription', 
            'follow_up_date', 'visit_type',
        ]
        widgets = {
            'patient': forms.Select(attrs={'class': 'w-full p-2 border border-gray-300 rounded-md'}),
            'doctor': forms.Select(attrs={'class': 'w-full p-2 border border-gray-300 rounded-md'}),
            'diagnosis': forms.Textarea(attrs={'class': 'w-full p-2 border border-gray-300 rounded-md', 'rows': 3}),
            'symptoms': forms.Textarea(attrs={'class': 'w-full p-2 border border-gray-300 rounded-md', 'rows': 3}),
            'prescription': forms.Textarea(attrs={'class': 'w-full p-2 border border-gray-300 rounded-md', 'rows': 3}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full p-2 border border-gray-300 rounded-md'}),
            'visit_type': forms.Select(attrs={'class': 'w-full p-2 border border-gray-300 rounded-md'}),
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
        fields = ['medication','concentration_mg_per_ml', 'dosage','dose_frequency','timing']
        widgets = {
            'medication': forms.TextInput(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter medication',
            }),
            'concentration_mg_per_ml': forms.TextInput(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter concentration',
            }),
            'dosage': forms.TextInput(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter dosage',
            }),
            'dose_frequency': forms.Select(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
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
        exclude = ["patient", "ipd_admission", "prescription"]
        fields = [
            "route", "medicine", "medicine_vial", "diluent", "dose_frequency", 
            "other_frequency", "vial", "dilution_volume", "frequency_of_dose", "sign"
        ]

    def __init__(self, *args, **kwargs):
        self.ipd_admission = kwargs.pop("ipd_admission", None)
        if self.ipd_admission is None:
            raise ValueError("IPD admission must be provided.")
        super().__init__(*args, **kwargs)
        # Make medicine_vial optional
        self.fields["medicine_vial"].required = False
        # Hide 'other_frequency' field initially
        self.fields["other_frequency"].widget.attrs.update({
            "placeholder": "Specify custom frequency",
            "style": "display: none;",
        })

        # Optionally filter medicine_vial based on initial medicine (optional)
        if "medicine" in self.data:
            try:
                medicine_id = int(self.data.get("medicine"))
                self.fields["medicine_vial"].queryset = MedicineVial.objects.filter(medicine_id=medicine_id)
            except (ValueError, TypeError):
                self.fields["medicine_vial"].queryset = MedicineVial.objects.none()
        elif self.instance.pk and self.instance.medicine:
            self.fields["medicine_vial"].queryset = MedicineVial.objects.filter(medicine=self.instance.medicine)
        else:
            self.fields["medicine_vial"].queryset = MedicineVial.objects.none()

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.ipd_admission = self.ipd_admission
        instance.patient = self.ipd_admission.patient

        if commit:
            instance.save()
        return instance

    def clean(self):
        cleaned_data = super().clean()
        if not hasattr(self.instance, "patient") or self.instance.patient is None:
            if self.ipd_admission:
                self.instance.patient = self.ipd_admission.patient
            else:
                raise forms.ValidationError("Patient information is required.")
        return cleaned_data


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = [
            "name", "brand", "medicine_type", "route", "duration","tablet_strength",
            "standard_dose_per_kg", "concentration_mg_per_ml", "is_liquid_injection"
        ]
        widgets = {
            "medicine_type": forms.Select(choices=Medicine.MEDICINE_TYPE_CHOICES, attrs={"class": "form-control"}),
            "route": forms.Select(choices=Medicine.ROUTE_CHOICES, attrs={"class": "form-control"}),
            "brand": forms.TextInput(attrs={"class": "form-control"}),
            "duration": forms.Select(choices=Medicine.DURATION_FREQUENCY_CHOICES, attrs={"class": "form-control"}),
            "standard_dose_per_kg": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "concentration_mg_per_ml": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "is_liquid_injection": forms.CheckboxInput(attrs={"class": "form-check-input", "id": "id_is_liquid_injection"}),
        }
        labels = {
            "name": "Medicine Name",
            "brand": "Brand",
            "medicine_type": "Type of Medicine",
            "route": "Route of Administration",
            "duration": "Duration (days)",
            "standard_dose_per_kg": "Standard Dose (mg/kg/dose)",
            "concentration_mg_per_ml": "Concentration (mg/mL)",
            "is_liquid_injection": "Is it a Liquid Injection?",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Only show "is_liquid_injection" if type is "injection"
        if self.data.get("medicine_type") != "injection" and (
            not self.instance or self.instance.medicine_type != "injection"
        ):
            self.fields.pop("is_liquid_injection")

class MedicineVialForm(forms.ModelForm):
    class Meta:
        model = MedicineVial
        fields = ["strength_mg", "volume_ml"]
        widgets = {
            "strength_mg": forms.NumberInput(attrs={"class": "form-control", "step": "0.1"}),
            "volume_ml": forms.NumberInput(attrs={"class": "form-control", "step": "0.1"}),
        }
        labels = {
            "strength_mg": "Strength (mg)",
            "volume_ml": "Volume (mL)",
        }

MedicineVialFormSet = inlineformset_factory(
    Medicine, MedicineVial, form=MedicineVialForm,
    extra=1, can_delete=True
)


class DiluentForm(forms.ModelForm):
    compatible_medicine_types = forms.ModelMultipleChoiceField(
        queryset=Medicine.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Compatible Medicine Types",
    )

    class Meta:
        model = Diluent
        fields = ["name"]
        # widgets = {
        #     "standard_volume_per_kg": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        # }
        labels = {
            "name": "Diluent Name",
            # "standard_volume_per_kg": "Standard Volume (mL/kg/dose)",
        }

class VialForm(forms.ModelForm):
    class Meta:
        model = Vial
        fields = ['size', 'unit']
        widgets = {
            'size': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter size'}),
            'unit': forms.Select(attrs={'class': 'form-control'}),
        }

class NICUFluidForm(forms.ModelForm):
    class Meta:
        model = FluidRequirement
        fields = ["medicine"]  # Only show medicine

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["medicine"].queryset = Medicine.objects.filter(medicine_type="fluid")






class OPDBillingForm(forms.ModelForm):
    class Meta:
        model = OPDBilling
        fields = ['opd_visit', 'consultation_fee', 'procedure_fee', 'medication_fee', 'other_fee']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control fee-input' if 'fee' in name else 'form-control'})


class IPDBillingForm(forms.ModelForm):
    class Meta:
        model = IPDBilling
        fields = ['ipd_admission', 'nursing_charges', 'procedure_charges', 'medication_charges', 'lab_charges', 'other_charges']

    room_charges = forms.DecimalField(required=False, widget=forms.HiddenInput())

class BillingItemForm(forms.ModelForm):
    class Meta:
        model = BillingItem
        fields = [ 'opd_billing', 'ipd_billing', 'description', 'quantity', 'unit_price', 'discount', 'tax_rate']
    

class PaymentForm(forms.ModelForm):
    def __init__(self, *args, max_amount=None, **kwargs):
        super().__init__(*args, **kwargs)
        if max_amount is not None:
            self.fields['amount'].widget.attrs['max'] = str(max_amount)
            self.fields['amount'].widget.attrs['placeholder'] = f'Max: ₹{max_amount}'

    class Meta:
        model = Payment
        # ✅ EXCLUDE 'received_by' since it's set in the view
        fields = ['amount', 'payment_method', 'transaction_id', 'notes']


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['patient', 'category', 'description', 'cost']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control'}),
        }
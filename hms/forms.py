from django import forms
from .models import CustomUser, Patient,Billing,Expense,OPD,Room, Doctor, Employee,EmergencyCase

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ["full_name", "email", "contact_number", "address"]

        
class PatientRegistrationForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['full_name', 'email', 'contact_number', 'address','gender']

    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    aadhar_number = forms.CharField(max_length=12)
    blood_group = forms.ChoiceField(choices=[('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'), 
                                             ('O+', 'O+'), ('O-', 'O-'), ('AB+', 'AB+'), ('AB-', 'AB-')])

    guarantor_name = forms.CharField(max_length=255)
    guarantor_address = forms.CharField(widget=forms.Textarea)
    guarantor_mobile = forms.CharField(max_length=15)
    guarantor_relationship = forms.CharField(max_length=50)
    guarantor_gender = forms.ChoiceField(choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])


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
        fields = ['patient', 'doctor', 'diagnosis']



class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['room_number', 'room_type', 'is_available']

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['user', 'role', 'contact_number', 'hired_date']

class DoctorForm(forms.ModelForm):
    user = forms.ModelChoiceField(queryset=CustomUser.objects.filter(is_staff=False), label="Select User")

    class Meta:
        model = Doctor
        fields = ['user', 'specialization', 'contact_number', 'availability']


class EmergencyCaseForm(forms.ModelForm):
    class Meta:
        model = EmergencyCase
        fields = ['patient', 'referred_by', 'referrer_contact', 'emergency_type', 'case_description']























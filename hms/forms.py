from django import forms
from .models import CustomUser, Patient

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

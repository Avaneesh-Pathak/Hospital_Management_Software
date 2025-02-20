from django.urls import path
from . import views
from .views import patient_detail,doctor_detail

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('patients/', views.patients, name='patients'),
    path('doctors/', views.doctors, name='doctors'),
    path('appointments/', views.appointments, name='appointments'),
    path("appointments/update_status/", views.update_appointment_status, name="update_appointment_status"),
    path('billing/', views.billing, name='billing'),
    path('emergency/', views.emergency, name='emergency'),
    path('ipd/', views.ipd, name='ipd'),
    path('opd/', views.opd, name='opd'),
    path('register/', views.register_patient, name='register_patient'),
    path('patients/<str:patient_code>/', patient_detail, name='patient_detail'),
    path('doctors/<int:doctor_id>/', doctor_detail, name='doctor_detail'),
]

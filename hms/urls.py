from django.urls import path
from . import views
from .views import add_emergency_case,admit_emergency_patient, patient_detail,doctor_detail,generate_bill,add_expense,generate_bill_pdf,add_opd,update_opd,admit_patient,add_doctor,add_employee,add_room,employee_list,edit_employee,delete_employee,discharge_patient

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('patients/', views.patients, name='patients'),
    path('doctors/', views.doctors, name='doctors'),
    path('appointments/', views.appointments, name='appointments'),
    path("appointments/update_status/", views.update_appointment_status, name="update_appointment_status"),
    path('billing/', views.billing, name='billing'),
    path('billing/pay/<int:billing_id>/', views.pay_bill, name='pay_bill'),
    path('billing/generate/<str:patient_code>/', generate_bill, name='generate_bill'),
    path('billing/pdf/<str:patient_code>/', generate_bill_pdf, name='download_bill_pdf'),
    path('billing/add-expense/', add_expense, name='add_expense'),
    path('emergency/', views.emergency, name='emergency'),
    path("emergency/add/", add_emergency_case, name="add_emergency_case"),
    path("emergency/admit/<int:emergency_id>/", admit_emergency_patient, name="admit_emergency_patient"),
    path('ipd/', views.ipd, name='ipd'),
    path('opd/', views.opd, name='opd'),
    path('opd/add/', add_opd, name='add_opd'),
    path('opd/update/<int:opd_id>/', update_opd, name='update_opd'),
    path('opd/admit/<int:opd_id>/', admit_patient, name='admit_patient'),
    path('ipd/discharge/<int:ipd_id>/', discharge_patient, name='discharge_patient'),
    path('register/', views.register_patient, name='register_patient'),
    path('patients/<str:patient_code>/', patient_detail, name='patient_detail'),
    path('doctors/<int:doctor_id>/', doctor_detail, name='doctor_detail'),
    path('add-room/', add_room, name='add_room'),
    path('add-employee/', add_employee, name='add_employee'),
    path('employees/', employee_list, name='employee_list'),
    path('employee/edit/<int:pk>/', edit_employee, name='edit_employee'),
    path('employee/delete/<int:pk>/', delete_employee, name='delete_employee'),
    path('add-doctor/', add_doctor, name='add_doctor'),
]

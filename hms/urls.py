from django.urls import path
from . import views
from .views import (
    signup, upload_patient_report, add_prescription, get_available_beds, fetch_patients, fetch_opd, fetch_appointments,
    user_login, get_ipd_data, book_appointment, update_appointment_status, appointment_success, available_doctors,
    profile_view, patient_profile, user_logout, add_emergency_case, admit_emergency_patient, patient_detail,
    doctor_detail, generate_bill, add_expense, generate_bill_pdf, add_opd, update_opd, admit_patient, add_doctor,
    add_employee, add_room, employee_list, edit_employee, delete_employee, discharge_patient, view_ipd_report,
    update_ipd_room,DaybookListView,DaybookCreateView,BalanceUpdateView
)

urlpatterns = [
    # Dashboard and General Pages
    path('', views.dashboard, name='dashboard'),
    path('search/', views.search, name='search'),
    path('profile/', profile_view, name='profile'),

    # Authentication
    path('signup/', signup, name='signup'),
    path('login/', user_login, name='login'),
    path('logout/', user_logout, name='logout'),

    # Patients
    path('patients/', views.patients, name='patients'),
    path('api/patients/', fetch_patients, name='fetch_patients'),
    path("patient/<str:patient_code>/profile/", views.patient_profile, name="patient_profile"),
    path('patient/<str:patient_code>/upload-report/', upload_patient_report, name='upload_patient_report'),
    path('register/', views.register_patient, name='register_patient'),
    path('patients/<str:patient_code>/', patient_detail, name='patient_detail'),

    # Doctors
    path('doctors/', views.doctors, name='doctors'),
    path('doctor/update/<int:doctor_id>/', views.update_doctor, name='update_doctor'),
    path('doctors/<int:doctor_id>/', doctor_detail, name='doctor_detail'),
    path('add-doctor/', add_doctor, name='add_doctor'),
    path('available-doctors/', available_doctors, name='available_doctors'),

    # Appointments
    path('appointments/', views.appointments, name='appointments'),
    path('api/appointments/', fetch_appointments, name='fetch_appointments'),
    path('appointments_update/', views.appointments_update, name='appointments_update'),
    path('book-appointment/<int:doctor_id>/', book_appointment, name='book_appointment'),
    path('book-appointment/<int:doctor_id>/success/', appointment_success, name='appointment_success'),
    path('update-appointment-status/', update_appointment_status, name='update_appointment_status'),

    # OPD
    path('opd/', views.opd, name='opd'),
    path('opd/report/<int:patient_id>/', views.opd_report_template, name='opd_report_template'),
    path('api/opd/', fetch_opd, name='fetch_opd'),
    path('opd/add/', add_opd, name='add_opd'),
    path('opd/update/<int:opd_id>/', update_opd, name='update_opd'),
    path('opd/admit/<int:opd_id>/', admit_patient, name='admit_patient'),

    # IPD
    path('ipd/', views.ipd, name='ipd'),
    path('get-ipd-data/', get_ipd_data, name='get_ipd_data'),
    path('ipd/<int:ipd_id>/add_prescription/', add_prescription, name='add_prescription'),
    path('ipd/<int:ipd_id>/', view_ipd_report, name='view_ipd_report'),
    path('ipd/<int:ipd_id>/update-room/', update_ipd_room, name='update_ipd_room'),
    path('discharge/<str:patient_code>/', discharge_patient, name='discharge_patient'),
    path('discharge_summary/<str:patient_code>/pdf/',views.discharge_summary_pdf, name='discharge_summary_pdf'),
    path('transfer_patient/<str:patient_code>/', views.transfer_patient, name='transfer_patient'),
    path('transfer_summary/<str:patient_code>/pdf/', views.transfer_summary_pdf, name='transfer_summary_pdf'),


    # Emergency
    path('emergency/', views.emergency, name='emergency'),
    path('emergency/', views.emergency_s, name='emergency_s'),
    path('emergency/add/', add_emergency_case, name='add_emergency_case'),
    path('emergency/edit/<int:emergency_id>/', views.edit_emergency_case, name='edit_emergency_case'),
    path('emergency/delete/<int:emergency_id>/', views.delete_emergency_case, name='delete_emergency_case'),
    path('emergency/admit/<int:emergency_id>/', admit_emergency_patient, name='admit_emergency_patient'),

    # Billing
    path('billing/', views.billing, name='billing'),
    path('billing/pay/<int:billing_id>/', views.pay_bill, name='pay_bill'),
    path('billing/generate/<str:patient_code>/', generate_bill, name='generate_bill'),
    path('billing/pdf/<str:patient_code>/', generate_bill_pdf, name='download_bill_pdf'),
    path('billing/add-expense/', add_expense, name='add_expense'),

    # Rooms and Beds
    path('add-room/', add_room, name='add_room'),
    path('get_available_beds/', get_available_beds, name='get_available_beds'),

    # Employees
    path('add-employee/', add_employee, name='add_employee'),
    path('employees/', employee_list, name='employee_list'),
    path('employee/edit/<int:pk>/', edit_employee, name='edit_employee'),
    path('employee/delete/<int:pk>/', delete_employee, name='delete_employee'),
    path('employees/pay-salary/<int:pk>/', views.pay_salary, name='pay_salary'),

    # Assets
    path('assets/', views.asset_list, name='asset_list'),
    path('assets/add/', views.add_asset, name='add_asset'),
    path('assets/edit/<int:id>/', views.edit_asset, name='edit_asset'),
    path('assets/delete/<int:id>/', views.delete_asset, name='delete_asset'),

    # Maintenance
    path('maintenance/', views.maintenance_list, name='maintenance_list'),
    path('maintenance/add/', views.add_maintenance, name='add_maintenance'),
    path('maintenance/edit/<int:id>/', views.edit_maintenance, name='edit_maintenance'),
    path('maintenance/delete/<int:id>/', views.delete_maintenance, name='delete_maintenance'),

    # Licenses
    path('licenses/', views.license_list, name='license_list'),
    path('licenses/add/', views.add_license, name='add_license'),
    path('licenses/edit/<int:id>/', views.edit_license, name='edit_license'),
    path('licenses/delete/<int:id>/', views.delete_license, name='delete_license'),

    # Accounting
    path('accounting-summary/', views.accounting_summary, name='accounting_summary'),

    #DAYBOOK
    path('daybook/', DaybookListView.as_view(), name='daybook_list'),  # URL for listing expenses
    path('daybook/create/', DaybookCreateView.as_view(), name='daybook_create'),
    path('update-balance/', BalanceUpdateView.as_view(), name='update_balance'),
    path('daybook/export/', views.export_daybook_to_csv, name='export_daybook_to_csv'),

    #Vitals
    path('nicu/add/<int:ipd_id>/', views.add_nicu_vitals, name='add_nicu_vitals'),
    path('nicu/view/<int:ipd_id>/', views.view_nicu_vitals, name='view_nicu_vitals')

]
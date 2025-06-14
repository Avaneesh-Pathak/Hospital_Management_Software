from django.urls import path
# from . import api
from . import views
from .views import (
    signup, upload_patient_report, get_available_beds, fetch_patients, fetch_opd, fetch_appointments,
    user_login, get_ipd_data, book_appointment, update_appointment_status, appointment_success, available_doctors,
    profile_view, patient_profile, user_logout, add_emergency_case, admit_emergency_patient, patient_detail,
    doctor_detail,  add_opd, update_opd, admit_patient, add_doctor,
    add_employee, add_room, employee_list, edit_employee, delete_employee, view_ipd_report,
    update_ipd_room,DaybookListView,DaybookCreateView,BalanceUpdateView,NICUMedicationRecordListView,NICUMedicationRecordCreateView,
    NICUMedicationRecordUpdateView,delete_nicu_medication,NICUFluidAddView,NICUFluidUpdateView,NICUFluidDeleteView,
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
    path('redirect/', views.redirect_after_login, name='redirect_after_login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('nurse/dashboard/', views.nurse_dashboard, name='nurse_dashboard'),
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('api/patient-stats-staff/', views.patient_stats_api_staff, name='patient_stats_api_staff'),

    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # Patients
    path('patients/', views.patients, name='patients'),
    path("api/fetch-patients/", views.fetch_patients, name="fetch_patients"),
    path('api/patient-stats/', views.patient_stats_api, name='patient_stats_api'),
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
    path("opd/quick_add/", views.add_opd_quick, name="add_opd_quick"),
    path("doctor/pending-opds/", views.pending_opds_for_doctor, name="pending_opds_for_doctor"),
    path('opd/add/', add_opd, name='add_opd'),
    path('opd/update/<int:opd_id>/', update_opd, name='update_opd'),
    path('opd/admit/<int:opd_id>/', admit_patient, name='admit_patient'),
    path('ajax/search-medicines/', views.search_medicines, name='search_medicines'),
    
    # notifications
    path("notifications/unread/", views.unread_notifications, name="unread_notifications"),
    path("notifications/mark-read/<int:pk>/", views.mark_notification_read, name="mark_notification_read"),
    # path("notifications/mark-all-read/", views.mark_all_read, name="mark_all_notifications_read"),

    # IPD
    path('ipd/', views.ipd, name='ipd'),
    path('ipd/add/', views.add_ipd, name='add_ipd'),
    path('ipd/<int:ipd_id>/add-summary/', views.add_patient_summary, name='add_patient_summary'),
    path('get-ipd-data/', get_ipd_data, name='get_ipd_data'),
    path('ipd/<int:ipd_id>/add_prescription/', views.add_prescription, name='add_prescription'),
    path('search_medicine_detail/', views.search_medicine_detail, name='search_medicine_detail'),
    path('ipd/<int:ipd_id>/', view_ipd_report, name='view_ipd_report'),
    path('ipd/<int:ipd_id>/update-room/', update_ipd_room, name='update_ipd_room'),
    path('ipd/discharge-summary/<str:patient_code>/', views.discharge_summary_view, name="discharge_summary_view"),
    path('ipd/discharge-summary/pdf/<str:patient_code>/', views.discharge_summary_pdf, name="discharge_summary_pdf"),
    path('ipd/transfer-summary/<str:patient_code>/', views.transfer_summary_view, name="transfer_summary_view"),
    path('ipd/transfer-summary/pdf/<str:patient_code>/', views.transfer_summary_pdf, name="transfer_summary_pdf"),


    # Emergency
    path('emergency/', views.emergency, name='emergency'),
    path('emergency/', views.emergency_s, name='emergency_s'),
    path('emergency/add/', add_emergency_case, name='add_emergency_case'),
    path('emergency/edit/<int:emergency_id>/', views.edit_emergency_case, name='edit_emergency_case'),
    path('emergency/delete/<int:emergency_id>/', views.delete_emergency_case, name='delete_emergency_case'),
    path('emergency/admit/<int:emergency_id>/', admit_emergency_patient, name='admit_emergency_patient'),

    # Billing
    path('bills/', views.bill_list, name='bill_list'),
    path('bills/opd/create/', views.create_opd_bill, name='create_opd_bill'),
    path('bills/ipd/create/', views.create_ipd_bill, name='create_ipd_bill'),
    path('bills/<str:bill_number>/', views.view_bill, name='view_bill'),
    path('bills/<str:bill_number>/pdf/', views.view_bill_pdf, name='view_bill_pdf'),
    path('bills/<str:bill_number>/add-item/', views.add_billing_item, name='add_billing_item'),
    path('bills/<str:bill_number>/pay/', views.record_payment, name='record_payment'),
    
    # Expense URLs
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/', views.add_expense, name='add_expense'),
    path('expenses/<int:pk>/edit/', views.edit_expense, name='edit_expense'),
    path('expenses/<int:pk>/delete/', views.delete_expense, name='delete_expense'),
    
    # Payment URLs
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/<int:pk>/', views.payment_detail, name='payment_detail'),
    path('payments/<int:pk>/receipt/', views.payment_receipt, name='payment_receipt'),
    

    # Rooms and Beds
    path('add-room/', add_room, name='add_room'),
    path("get-available-beds/", views.get_available_beds_ajax, name="get_available_beds_ajax"),
    path('ajax/get-beds/', views.get_available_beds, name='get_available_beds'),
    path('room-overview/', views.room_overview, name='room_overview'),
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
    path('nicu/view/<int:ipd_id>/', views.view_nicu_vitals, name='view_nicu_vitals'),

    #NICUMedicationRecord
    path("nicu/medications/<int:ipd_id>/", NICUMedicationRecordListView.as_view(), name="nicu_medication_list"),
    path("nicu/medication/add/<int:ipd_id>/", NICUMedicationRecordCreateView.as_view(), name="nicu_medication_create"),
    path('nicu/medications/<int:ipd_id>/add/', NICUMedicationRecordCreateView.as_view(), name='nicu_medication_add'),
    path("nicu-medications/edit/<int:pk>/", NICUMedicationRecordUpdateView.as_view(), name="nicu_medication_edit"),
    path("nicu-medications/delete/<int:pk>/", delete_nicu_medication, name="nicu_medication_delete"),

    #Medicne and Diluent
    path('medicine-diluent/', views.manage_medicine_diluent, name='manage_medicine_diluent'),
    path("ajax/get-vials/", views.get_vials_for_medicine, name="get_vials_for_medicine"),
    path('ajax/filter-medicines/', views.filter_medicines, name='filter_medicines'),
    path('delete-medicine/<int:pk>/', views.delete_medicine, name='delete_medicine'),
    path('delete-diluent/<int:pk>/', views.delete_diluent, name='delete_diluent'),
    path('delete_vial/<int:pk>/', views.delete_vial, name='delete_vial'),
    path('api/medicines/', views.medicine_list_api, name='medicine-list-api'),
    path('api/medicines/<int:pk>/', views.medicine_detail_api, name='medicine-detail-api'),

    #Fluid Form
    path("ipd/<int:ipd_id>/fluid/add/", NICUFluidAddView.as_view(), name="add_nicu_fluid"),
    path("fluid/<int:pk>/edit/", NICUFluidUpdateView.as_view(), name="update_nicu_fluid"),
    path('fluid/<int:pk>/delete/', views.NICUFluidDeleteView.as_view(), name='nicu_fluid_delete'),


]
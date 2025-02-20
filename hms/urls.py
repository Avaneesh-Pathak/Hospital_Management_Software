from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('patients/', views.patients, name='patients'),
    path('doctors/', views.doctors, name='doctors'),
    path('appointments/', views.appointments, name='appointments'),
    path('billing/', views.billing, name='billing'),
    path('emergency/', views.emergency, name='emergency'),
    path('ipd/', views.ipd, name='ipd'),
    path('opd/', views.opd, name='opd'),
]

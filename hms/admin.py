from django.contrib import admin
from .models import Patient, Doctor, Appointment, EmergencyCase, IPD, OPD, Billing, CustomUser, Room, Expense, Employee

admin.site.register(CustomUser)
admin.site.register(Patient)
admin.site.register(Doctor)
admin.site.register(Appointment)
admin.site.register(EmergencyCase)
admin.site.register(IPD)
admin.site.register(OPD)
admin.site.register(Billing)
admin.site.register(Room)
admin.site.register(Expense)
admin.site.register(Employee)




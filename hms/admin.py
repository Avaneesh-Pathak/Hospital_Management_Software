from django.contrib import admin
from .models import Patient, Doctor, Appointment, Emergency, IPD, OPD, Billing, CustomUser

admin.site.register(CustomUser)
admin.site.register(Patient)
admin.site.register(Doctor)
admin.site.register(Appointment)
admin.site.register(Emergency)
admin.site.register(IPD)
admin.site.register(OPD)
admin.site.register(Billing)

from django.contrib import admin
from .models import Patient,Asset,License,Maintenance, Doctor, Appointment,AccountingRecord, EmergencyCase, IPD, OPD, Billing, CustomUser, Room, Expense, Employee,PatientReport,Daybook,Balance

admin.site.register(CustomUser)
admin.site.register(Patient)
admin.site.register(Doctor)
admin.site.register(Appointment)
admin.site.register(EmergencyCase)
admin.site.register(IPD)
admin.site.register(OPD)
admin.site.register(Billing)
admin.site.register(Room)
admin.site.register(Asset)
admin.site.register(License)
admin.site.register(Maintenance)
admin.site.register(Expense)
admin.site.register(Employee)
admin.site.register(PatientReport)
admin.site.register(AccountingRecord)
admin.site.register(Daybook)
admin.site.register(Balance)





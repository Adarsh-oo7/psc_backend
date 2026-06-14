from django.contrib import admin
from .models import Message, Institute, FeeItem, Payment, Batch, BatchMembership, Attendance, Note

admin.site.register(Message)
admin.site.register(Institute)
admin.site.register(FeeItem)
admin.site.register(Payment)
admin.site.register(Batch)
admin.site.register(BatchMembership)
admin.site.register(Attendance)
admin.site.register(Note)


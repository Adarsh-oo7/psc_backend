from django.contrib import admin
from .models import Message,Institute,FeeStructure,PaymentTransaction
# Register your models here.
admin.site.register(Message)
admin.site.register(Institute)

admin.site.register(FeeStructure)

admin.site.register(PaymentTransaction)


from django.contrib import admin
from paymentHandler.models import PaymentHistory,PaymentIntentLogs



class PaymentHistoryAdmin(admin.ModelAdmin):
    model = PaymentHistory
    search_fields = ['paymentIntentId']
    readonly_fields = ('paidTimeStamp','timestamp',)
    list_display = ['email', 'paymentIntentId', 'paymentType', 'paymentStatus', 'paymentAmount','paidAmount', 'paidTimeStamp','timestamp',]


class PaymentIntentLogsAdmin(admin.ModelAdmin):
    model = PaymentHistory
    search_fields = ['paymentIntentId']
    readonly_fields = ('eventType','timestamp',)
    list_display = ['paymentIntentId', 'eventType','timestamp',]
    
    


admin.site.register(PaymentHistory, PaymentHistoryAdmin)
admin.site.register(PaymentIntentLogs, PaymentIntentLogsAdmin)
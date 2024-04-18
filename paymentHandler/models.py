from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from authemail.models import send_multi_format_email

PAYMENT_MODE_CHOICE = (
    (0,'Standard'),
    (1,'Pro'),
    (2,'Yearly Deal'),
)
CURRENCY_TYPE = (
    (0,"usd"),
    (1,"inr")
)

PAYMENT_INFO = {
    0: {"name": "Standard","price": {"usd": 1500,"inr": 99900}},
    1: {"name": "Pro","price": {"usd":2900,"inr": 219900}},
    2: {"name": "Yearly Deal","price": {"usd": 4900,"inr": 349900}},
}


PAYMENT_STATUS = (
    (0,'Not Completd'),
    (1, 'Completed')
)

class PaymentHistory(models.Model):

    email = models.EmailField(max_length=255,blank=True,null=True)
    paymentIntentId = models.CharField(max_length=512,blank=True,null=True)
    paymentType = models.IntegerField(default=0, choices=PAYMENT_MODE_CHOICE)
    paymentStatus = models.IntegerField(default=0, choices=PAYMENT_STATUS)
    paymentAmount = models.FloatField(default=0)
    paidAmount = models.FloatField(default=0)
    currencyType = models.IntegerField(default=0, choices=CURRENCY_TYPE)
    paidTimeStamp = models.DateTimeField(blank=True,null=True)
    sessionInfo = models.CharField(blank=True,null=True,max_length=5000)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)

    def __str__(self):
        return f"{self.email} - {self.paymentIntentId}"

    def onSuccess(self):
        if self.paymentStatus!=1:
            self.paymentStatus = 1
            self.paidAmount = self.paymentAmount
            self.paidTimeStamp = timezone.now()
            send_multi_format_email('paymentemail/payment_success',{"email": self.email},self.email)
            self.save()

    def onFailure(self):
        self.paymentStatus = 0
        self.paidTimeStamp = timezone.now()
        self.save()


class PaymentIntentLogs(models.Model):

    paymentIntentId = models.CharField(max_length=512,blank=True,null=True)
    eventType = models.CharField(max_length=256,blank=True,null=True)
    logs = models.TextField()
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)

    def __str__(self):
        return f"{self.paymentIntentId}"
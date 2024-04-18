from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.conf import settings
from math import ceil


CREDIT_USE_TYPE= (
    (0,'VIDEO'),
    (1,'CAMPAIGN'),
)

class VideoCreditUsage(models.Model):
    
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)

    usedCreditType = models.IntegerField(choices=CREDIT_USE_TYPE)
    usedCredit = models.FloatField(default= 0)
    name = models.CharField(max_length=100)
    info = models.CharField(default='',null=True,blank=True,max_length=10000)
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)


@receiver(post_save, sender=VideoCreditUsage)
def addCreditToSubs(sender, instance, *args, **kwargs):
    user = instance.user
    user.usedVideoCredit += instance.usedCredit
    user.save()


    




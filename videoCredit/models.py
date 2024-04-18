from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import json

def getDate(days=0):
    return timezone.now() + timezone.timedelta(days=days)

class CreditType(models.IntegerChoices):
    AVATAR_VIDEO = 0, 'AVATAR_VIDEO'
    NON_AVATAR_VIDEO = 1, 'NON_AVATAR_VIDEO'
    PERSONALIZE_VIDEO = 2, 'PERSONALIZE_VIDEO'
    PERSONALIZE_PAGE = 3, 'PERSONALIZE_PAGE'
    PERSONALIZE_THUMBNAIL = 4, 'PERSONALIZE_THUMBNAIL'
    PERSONALIZE_IMAGE = 5, 'PERSONALIZE_IMAGE'


class UserCredit(models.Model):

    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    usedCredit = models.IntegerField(default=0)
    totalCredit = models.IntegerField(default=0)
    creditType = models.IntegerField(default=CreditType.NON_AVATAR_VIDEO, choices=CreditType.choices)

    meta = models.CharField(max_length=1000,blank=True,null=True)
    
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    class Meta:
        ordering = ['creditType']


    def isCreditEnded(self):
        if self.usedCredit>=self.totalCredit:
            return True
        return False


PLAN_CREDIT_INFO = {
    "Pro": {"AVATAR_VIDEO": 45,"NON_AVATAR_VIDEO": 100000,"PERSONALIZE_VIDEO": 300,"PERSONALIZE_PAGE": 30000,"PERSONALIZE_THUMBNAIL": 30000,"PERSONALIZE_IMAGE": 30000},
    "Standard": {"AVATAR_VIDEO": 15,"NON_AVATAR_VIDEO": 100000,"PERSONALIZE_VIDEO": 100,"PERSONALIZE_PAGE": 5000,"PERSONALIZE_THUMBNAIL": 5000,"PERSONALIZE_IMAGE": 5000},
}

class UserCurrentSubscription(models.Model):

    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE)
    subscription = models.ManyToManyField("UserCredit",blank=True)
    planName = models.CharField(max_length=250,default="Trial Plan")
    subscriptionStart = models.DateTimeField(blank=True,null=True)
    subscriptionEnd = models.DateTimeField(blank=True,null=True)
    _perCycleCreditData = models.CharField(max_length=500,blank=True,null=True)
    _crntSubscriptionCycle = models.IntegerField(default=0) # index of crnt running cycle
    _totalUpdateCycle = models.IntegerField(default=1) # eg. for yearl (12)
    _subTotalDays = models.IntegerField(default=30) # in days

    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)


    def creditCycleUpdate(self):
        if self.subscriptionStart and self._totalUpdateCycle and self._perCycleCreditData:
            _diffDays = timezone.now() - self.subscriptionStart
            _runningCycle = self._subTotalDays/self._totalUpdateCycle
            _crntCycle = int(_diffDays.days/_runningCycle)
            if self._crntSubscriptionCycle != _crntCycle:
                # update credit data
                self._crntSubscriptionCycle = _crntCycle
                self.save()
                self.addCredit(creditData=json.loads(self._perCycleCreditData))
                return True
        return False


    def isSubscriptionEnded(self):
        if self.subscriptionEnd:
            if timezone.now()<=self.subscriptionEnd:
                self.creditCycleUpdate()
                return False
        return True

    # inst.addCredit(creditData={"AVATAR_VIDEO": 1000,"NON_AVATAR_VIDEO": 1000,"PERSONALIZE_VIDEO": 1000,"PERSONALIZE_PAGE": 1000,"PERSONALIZE_THUMBNAIL": 1000,"PERSONALIZE_IMAGE": 1000})
    def addCredit(self,creditData={}):
        _allCreditChoices = CreditType.choices
        self.subscription.all().delete()
        #self.subscription.clear()
        for _crntCredit in _allCreditChoices:
            _cdInst = UserCredit(user=self.user,totalCredit=creditData.get(_crntCredit[1],0),creditType=_crntCredit[0])
            _cdInst.save()
            self.subscription.add(_cdInst)
        
    # meta {id,name,type,quantity=1,}
    def subscriptionValidator(self,type,usedCredit,meta={}):
        # validate credit
        self.creditCycleUpdate()
        _creditType = CreditType[type].value
        if self.subscription:
            try:
                _inst = self.subscription.get(creditType=_creditType)
                _inst.usedCredit = _inst.usedCredit+usedCredit
                _inst.save()
            except:
                pass
        _creditInst = VideoCreditInfo(user=self.user,creditType=_creditType,usedCredit=usedCredit,meta=json.dumps(meta))
        _creditInst.save()
        return True
        



class VideoCreditInfo(models.Model):

    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    meta = models.CharField(max_length=500,blank=True,null=True)
    creditType = models.IntegerField(default=CreditType.NON_AVATAR_VIDEO, choices=CreditType.choices)
    usedCredit = models.IntegerField(default=0)
    
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)

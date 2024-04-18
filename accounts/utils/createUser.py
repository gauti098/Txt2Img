from django.contrib.auth import get_user_model
from videoCredit.models import UserCurrentSubscription,PLAN_CREDIT_INFO,getDate
from django.utils import timezone

def getRandomPassword(length=8):
    return get_user_model().objects.make_random_password(length)

def createUser(email,password,firstName=None):
    user = get_user_model().objects.create_user(email=email)
    user.set_password(password)

    if firstName:
        user.first_name = firstName
    else:
        user.first_name = email.split('@')[0]
    user.is_verified = True
    user.save()
    user.addDefaultOrganization()
    return user

def addSubscriptionPlan(user,plan,expiryDays=30):
    planData = PLAN_CREDIT_INFO.get(plan,None)
    if planData:
        _subInst,ct = UserCurrentSubscription.objects.get_or_create(user=user)
        _subInst.planName = f"{plan} Plan"
        _subInst.subscriptionStart = timezone.now()
        _subInst.subscriptionEnd = getDate(expiryDays)
        _subInst.save()
        _subInst.addCredit(planData)
        return (True,_subInst)
    else:
        return (False,f"{plan} Plan is not Valid.")

def createUserWithSubscriptions(email,password,firstName=None,plan = "Pro",expiryDays=30):
    _planData = PLAN_CREDIT_INFO.get(plan,None)
    if _planData:
        user = createUser(email,password,firstName)
        _subInst = addSubscriptionPlan(user,plan,expiryDays)
        return (True,user,_subInst)
    else:
        return (False,f"{plan} Plan is not Valid.",None)

'''
from accounts.utils import createUser
createUser.createUserWithSubscriptions(email,'JayTomar26',"Jay Tomar")
createUser.createUserWithSubscriptions('india.ashishjain@gmail.com','ashish',"Ashish",expiryDays=365)
createUser.addSubscriptionPlan(user,'Pro',expiryDays=365)
createUser.createUserWithSubscriptions("all@ycombinator.com",'yc',"Y Combinator")
'''
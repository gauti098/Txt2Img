from django.db import models
from authemail.models import EmailUserManager, EmailAbstractUser
from phonenumber_field.modelfields import PhoneNumberField
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import datetime
from datetime import timedelta
import requests
from rest_framework.authtoken.models import Token
from authemail.models import send_multi_format_email
from utils.customValidators import validate_url

def subEnd():
    return datetime.now() + timedelta(days=30*5)


DEFAULT_ORGANIZATION_NAME = '_blank'

class Organization(models.Model):
	# Custom fields
	name = models.CharField(max_length=50)
	subs_start = models.DateTimeField(default=datetime.now)
	subs_end = models.DateTimeField(default=subEnd)
	subdomain = models.CharField(max_length=50)

	logo = models.ImageField(upload_to='organistion/logo/',default="organistion/logo/default.png")
	fav_icon = models.ImageField(upload_to='organistion/fav/',default="organistion/fav/default.ico")
	
	def __str__(self):
		return f"{self.name}"


class MyUser(EmailAbstractUser):
	# Custom fields
	organization = models.ForeignKey(Organization,blank=True,on_delete=models.SET_NULL,null=True)
	org_is_admin = models.BooleanField(default=False)

	profile_image = models.ImageField(upload_to='user_profile/',default="user_profile/default.png",null=True,blank=True)
	auth_provider = models.CharField(default="email",max_length=30)
	isCP = models.BooleanField(default=True) # change password is visible
	phone_number = PhoneNumberField(blank=True)
	calendar_url = models.URLField(max_length = 200,blank=True,validators =[validate_url])
	facebook_url = models.URLField(max_length = 200,blank=True,validators =[validate_url])
	twitter_url = models.URLField(max_length = 200,blank=True,validators =[validate_url])
	linkedin_url = models.URLField(max_length = 200,blank=True,validators =[validate_url])

	subs_start = models.DateTimeField(default=datetime.now)
	subs_end = models.DateTimeField(default=subEnd)    
	last_login = models.DateTimeField(default=datetime.now)    
    
	usedVideoCredit = models.IntegerField(default= 0)
	totalVideoCredit = models.IntegerField(default= 1000)
    
    
    # Required
	objects = EmailUserManager()

	def isActive(self):
		if bool(self.organization) == True and self.is_verified == True and self.is_active == True:
			return True
		else:
			return False

	def addDefaultOrganization(self):
		# Add Default Organization
		_org = Organization.objects.filter(name=DEFAULT_ORGANIZATION_NAME)
		if _org.count():
			self.organization = _org.first()
			self.save()


	def getToken(self):
		token, created = Token.objects.get_or_create(user=self)
		return token.key

	def getWebsocketGroupName(self,appType=1):
		if appType==1:
			return f'newVideoCreator-{self.pk}'
		else:
			return f"{self.pk}"



PROBLEM_CATEGORY = (
    (0,'Video Creation'),
    (1,'Sales Page Creation'),
    (2,'Sharing Campaign'),
    (3,'Dashboard & Analytics'),
    (4,'Subscription'),
    (5,'Other'),
	(6,'Image Personalization'),
	(7,'Video Personalization'),
	(8,'Thumbnail Personalization'),
	(9,'Salespage Personalization'),

)

SOLVE_CATEGORY = (
	(0,'Pending'),
	(1,'Solved'),
	(2,'Working'),
)

class ContactUs(models.Model):
    user = models.ForeignKey(MyUser,on_delete=models.CASCADE)
    message =  models.CharField(max_length=10000,blank=False)
    problemCategory = models.IntegerField(default= 3,choices=PROBLEM_CATEGORY)
    status = models.IntegerField(default= 0,choices=SOLVE_CATEGORY)
	
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    
    def __str__(self):
        return f"{self.id} - {self.message[:20]}..."


FAQ_CATEGORY = (
    (0,'Video Creation'),
    (1,'Sales Page Creation'),
    (2,'Sharing Campaign'),
    (3,'Dashboard & Analytics'),
    (4,'General'),

)

class FAQuestions(models.Model):
    
    faqCategory = models.IntegerField(default= 4,choices=FAQ_CATEGORY)
    description =  models.CharField(max_length=10000,blank=True)
    video = models.FileField(upload_to='faqsVideo/')
    videoThumbnail = models.ImageField(upload_to='faqsVideo/thumbnail/',blank=True)
    orderBy = models.IntegerField(default=0)






class IpLocationInfo(models.Model):

	userIp =  models.CharField(max_length=50,blank=True,null=True)
	country = models.CharField(max_length=50,blank=True,null=True)
	regionName = models.CharField(max_length=50,blank=True,null=True)
	city = models.CharField(max_length=50,blank=True,null=True)
	countryCode = models.CharField(max_length=10,blank=True,null=True)
	region = models.CharField(max_length=10,blank=True,null=True)
	postalCode = models.CharField(max_length=10,blank=True,null=True)
	lattitude = models.FloatField(blank=True,null=True)
	longitude = models.FloatField(blank=True,null=True)
	isp = models.CharField(max_length=50,blank=True,null=True)
	timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)

	def __str__(self):
		return f"{self.userIp} {self.country} {self.regionName} {self.city}"


CLIENT_SOURCE = (
	(0,"common"),
	(1,"autogenerate_requestaccess"),
	(2,"autovid_getearlyaccess"),
	(3,"autovid_corporateplan"),
	(4,"autovid_payment"),
)
CLIENT_SOURCE_DICT_MAP = {_i[0]:_i[1] for _i in CLIENT_SOURCE}
CLIENT_SOURCE_DICT = {_i[1]: _i[0] for _i in CLIENT_SOURCE}
class EmailGrab(models.Model):
	
	email = models.CharField(max_length=100)
	userIp =  models.CharField(max_length=50,blank=True,null=True)
	origin = models.CharField(max_length=50,blank=True,null=True)
	clientSource = models.IntegerField(default=0,choices=CLIENT_SOURCE)
	userInfo = models.CharField(max_length=2500,blank=True,null=True)
	clientDevice = models.CharField(max_length=50,blank=True,null=True)
	userAgent = models.CharField(max_length=500,blank=True,null=True)
	browser = models.CharField(max_length=50,blank=True,null=True)
	location = models.ForeignKey("IpLocationInfo",blank=True,null=True,on_delete=models.SET_NULL)
	timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
	
	def __str__(self):
		return f"{self.email} {self.userIp}"

	def doCommonTask(self):
		# setup if info
		self.setIpToLocation()

		# send mail for particular type
		if self.clientSource in [3]:
			send_multi_format_email('contactusemail/contactus',{"contactType": CLIENT_SOURCE_DICT_MAP[self.clientSource].upper(),"email": self.email,"userIp": self.userIp,"country": self.location.country,"regionName": self.location.regionName,"city": self.location.city,"clientDevice": self.clientDevice,"browser": self.browser},"sehaj@autogenerate.ai")

	def setIpToLocation(self):
		if self.userIp:
			try:
				ipUrl = f'http://ip-api.com/json/{self.userIp}'
				r = requests.get(ipUrl)
				resData = r.json()
				if resData["status"]=="success":
					locationData = {"userIp": self.userIp,"country": resData.get("country",""),"regionName": resData.get("regionName",""),"city": resData.get("city",""),"countryCode":resData.get("countryCode",""),"region":resData.get("region",""),"postalCode":resData.get("zip",""),"lattitude":resData.get("lat",""),"longitude":resData.get("lon",""),"isp":resData.get("isp","")}
					ipLInst,ct = IpLocationInfo.objects.get_or_create(**locationData)

					self.location = ipLInst
					self.save()
					return True
				else:
					return False
			except:
				return False
		else:
			return False

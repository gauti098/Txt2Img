from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from threading import Thread
from authemail.models import ChangeOrgCode

import os


from accounts.serializers import (
    GoogleSocialAuthSerializer,UserSerializer,
    OrganizationSerializer,FAQSerializer,
    OrganizationUserSerializer
)

from accounts.models import (
    CLIENT_SOURCE_DICT,FAQuestions,
    ContactUs,EmailGrab
)

class GoogleSocialAuthView(GenericAPIView):

    serializer_class = GoogleSocialAuthSerializer

    def post(self, request):

        serializer = self.serializer_class(data=request.data,context={'request': request})
        serializer.is_valid(raise_exception=True)
        data = ((serializer.validated_data)['password'])
        return Response(data, status=status.HTTP_200_OK)



class AccountUser(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserSerializer

    def get(self, request, format=None):
        _requestData = request.GET
        _data = self.serializer_class(request.user,context={'request': request}).data
        if _requestData.get('isCP',0):
            _data["isCP"] = request.user.isCP
        return Response(_data)

    def put(self, request, format=None):
        try:
            _data = request.data.copy()
            _profileImage = _data.get("profile_image",None)
            if type(_profileImage)==str:
                _data["profile_image"] = None
        except:
            return Response({"profile_image":["Upload a valid image. The file you uploaded was either not an image or a corrupted image."]}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_class(request.user, data=_data,partial=True,context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class UserOrganization(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = OrganizationSerializer

    def get(self, request, format=None):
        user = request.user
        if bool(user.organization):
            if user.org_is_admin:
                allUser = get_user_model().objects.filter(is_active=True,organization=user.organization)
                return Response(OrganizationUserSerializer(allUser,many=True,context={'request': request}).data,status=status.HTTP_200_OK)
            else:
                return Response({'message': "Don't Have Permission."},status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'message': 'Your Account is Not Linked to any Organization.'},status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, format=None):
        user = request.user
        if bool(user.organization):
            serializer = self.serializer_class(user.organization, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            else:
                return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'Your Account is Not Linked to any Organization.'},status=status.HTTP_400_BAD_REQUEST)


from authemail.models import send_multi_format_email

class ManageOrganization(APIView):
    permission_classes = (IsAuthenticated,)
    #serializer_class = SignupSerializer

    def post(self, request, format=None):
        params = request.data
        user = request.user
        if user.org_is_admin:
            if bool(user.organization):
                if 'email' in params:
                    email = params['email']
                    try:
                        validate_email(email)
                    except ValidationError as e:
                        content = {'message': 'Email is not Valid'}
                        return Response(content,status=status.HTTP_200_OK)
                    is_admin = False
                    try:
                        tuser = get_user_model().objects.get(email=email)
                        content = {'message': 'User Already Connected to Organization.'}
                        return Response(content,status=status.HTTP_200_OK)
                    except Exception as e:
                        try:
                            tuser = get_user_model().objects.create_user(email=email,password=os.environ.get('SOCIAL_SECRET'))
                        except Exception as e:
                            print('Error in Adding new User: ',e)
                            content = {'message': 'Server side Error Occured.'}
                            return Response(content,status=status.HTTP_200_OK)

                        tuser.organization = user.organization
                        tuser.org_is_admin = False
                        tuser.save()
                        try:
                            org_code = ChangeOrgCode.objects.get(user=tuser)
                            org_code.delete()
                        except ChangeOrgCode.DoesNotExist:
                            pass
                        ipaddr = self.request.META.get('REMOTE_ADDR', '0.0.0.0')
                        org_code = ChangeOrgCode.objects.create_change_org_code(tuser, ipaddr,user.organization,is_admin)
                        org_code.send_change_org_email()
                        #send email for signup
                        #send_multi_format_email("accountsemail/org_added",{'login': False,'organization': user.organization.name},tuser.email)
                        content = {'message': f'{email} Added to Organization.'}
                        return Response(content,status=status.HTTP_200_OK)

                else:
                    content = {'message': 'email Field is Required.'}
                    return Response(content,status=status.HTTP_400_BAD_REQUEST)
            else:
                content = {'message': 'Your Account is Not Linked to any Organization.'}
                return Response(content,status=status.HTTP_400_BAD_REQUEST)
        else:
            content = {'message': 'You are not Organization Admin.'}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)


from datetime import date
class OrganizationFetchCode(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, format=None):
        code = request.GET.get('code', '')
        try:
            corg_code = ChangeOrgCode.objects.get(code=code)
            delta = date.today() - corg_code.created_at.date()
            if delta.days > ChangeOrgCode.objects.get_expiry_period():
                corg_code.delete()
                content = {'message': {'code': {'status': 1}},'isError': True}
                return Response(content, status=status.HTTP_200_OK)
            else:
                content = {'message': 'verified','email': corg_code.user.email,'isError': False}
                return Response(content, status=status.HTTP_200_OK)
        except ChangeOrgCode.DoesNotExist:
            content = {'message': {'code': {'status': 0}},'isError': True}
            return Response(content, status=status.HTTP_200_OK)

        


class OrganizationUserRemove(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, format=None):
        params = request.data
        user = request.user
        if user.org_is_admin:
            if bool(user.organization):
                if 'email' in params:
                    email = params['email']
                    try:
                        tuser = get_user_model().objects.get(email=email)
                        try:
                            if tuser.organization.id!=user.organization.id:
                                content = {'message': "Don't Have Permission To Removed."}
                                return Response(content,status=status.HTTP_400_BAD_REQUEST)
                        except:
                            content = {'message': "Don't Have Permission To Removed."}
                            return Response(content,status=status.HTTP_400_BAD_REQUEST)
                        if tuser.id == user.id:
                            content = {'message': 'Self Removing Not Allowed.'}
                            return Response(content,status=status.HTTP_400_BAD_REQUEST) 
                        tuser.is_active = False
                        tokens = Token.objects.filter(user=tuser)
                        for token in tokens:
                            token.delete()
                        tuser.save()
                        content = {'message': 'Successful Removed.'}
                        return Response(content,status=status.HTTP_200_OK) 
                    except Exception as e:
                        print("Error: ",e)
                        content = {'message': 'Email not Exists.'}
                        return Response(content,status=status.HTTP_400_BAD_REQUEST)
                else:
                    content = {'message': 'email Field is required.'}
                    return Response(content,status=status.HTTP_400_BAD_REQUEST)
            else:
                content = {'message': 'Your Account is Not Linked to any Organization.'}
                return Response(content,status=status.HTTP_400_BAD_REQUEST)
        else:
            content = {'message': 'You are not Organization Admin.'}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)
                


class OrganizationUserAdmin(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, format=None):
        params = request.data
        user = request.user
        if user.org_is_admin:
            if bool(user.organization):
                if 'email' in params:
                    email = params['email']
                    try:
                        tuser = get_user_model().objects.get(email=email)
                        try:
                            if tuser.organization.id!=user.organization.id:
                                content = {'message': "Don't Have Permission To Change Admin."}
                                return Response(content,status=status.HTTP_400_BAD_REQUEST)
                        except:
                            content = {'message': "Don't Have Permission To Change Admin."}
                            return Response(content,status=status.HTTP_400_BAD_REQUEST)
                        if tuser.id == user.id:
                            content = {'message': 'Self Change Not Allowed.'}
                            return Response(content,status=status.HTTP_400_BAD_REQUEST) 
                        if params.get('is_admin',None):
                            tuser.org_is_admin = True
                        else:
                            tuser.org_is_admin = False
                        tuser.save()
                        content = {'message': 'Successful Changed.'}
                        return Response(content,status=status.HTTP_200_OK) 
                    except Exception as e:
                        print("Error: ",e)
                        content = {'message': 'Email not Exists.'}
                        return Response(content,status=status.HTTP_400_BAD_REQUEST)
                else:
                    content = {'message': 'email Field is required.'}
                    return Response(content,status=status.HTTP_400_BAD_REQUEST)
            else:
                content = {'message': 'Your Account is Not Linked to any Organization.'}
                return Response(content,status=status.HTTP_400_BAD_REQUEST)
        else:
            content = {'message': 'You are not Organization Admin.'}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)

from utils.common import convertInt
from accounts.models import PROBLEM_CATEGORY
AllProblemCategory = [i[0] for i in PROBLEM_CATEGORY]

class ContactUsView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, format=None):
        user = request.user
        
        message = request.data.get('message','')
        problemCategory = convertInt(request.data.get('problemCategory',None),None)
        if problemCategory == None:
            content = {'problemCategory': ['This Field is Required.']}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)
        if message:
            try:
                if problemCategory not in AllProblemCategory:
                    content = {'problemCategory': ['This Field is Not Valid.']}
                    return Response(content, status=status.HTTP_400_BAD_REQUEST)
                else:
                    inst = ContactUs(user=user,message=message,problemCategory=problemCategory)
                    inst.save()
                    return Response('ok', status=status.HTTP_200_OK)
            except:
                content = {'problemCategory': ['This Field is Not Valid.']}
                return Response(content, status=status.HTTP_400_BAD_REQUEST)
        
        else:
            content = {'message': ['This Field is Required.']}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)


class FAQusetionsView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = FAQSerializer

    def get(self, request, format=None):

        category = request.GET.get('faqCategory',None)
        if category:
            try:
                category = int(category)
            except:
                category = None
        query = FAQuestions.objects.all().order_by('faqCategory','-orderBy')
        if category==0 or category:
            query = query.filter(faqCategory=category)
        
        content = FAQSerializer(query,many=True,context={'request': request}).data
        return Response(content, status=status.HTTP_200_OK)

import httpagentparser
def getUseFulInformation(metaInfo):
    _userIp = metaInfo.get("REMOTE_ADDR","")
    if not _userIp:
        _userIp = metaInfo.get("REMOTE_HOST","")
    
    # parse Origin
    _origin = metaInfo.get("HTTP_ORIGIN","")
    if not _origin:
        _origin = metaInfo.get("HTTP_REFERER","")

    # user Agent
    _userAgent = metaInfo.get("HTTP_USER_AGENT","")
    # device
    try:
        _device,_browser = httpagentparser.simple_detect(_userAgent)
    except:
        _device,_browser = "",""
    return {"userIp": _userIp,"origin": _origin,"clientDevice": _device,"userAgent": _userAgent,"browser": _browser}
        
def addLocationToEmailGrab(emailId):
    try:
        _inst = EmailGrab.objects.get(id=emailId)
        _inst.doCommonTask()
        return True
    except:
        return False

def getEmailGrabInst(email,request,origin=None):
    _fetchInfo = getUseFulInformation(request.META)
    if origin:
        _fetchInfo["origin"] = origin

    clientSource = 0
    if len(origin.split('payment.autovid'))>1:
        clientSource = 4
    elif len(origin.split('autogenerate'))>1:
        clientSource = 1
    _inst = EmailGrab.objects.create(email=email,userIp=_fetchInfo["userIp"],origin=_fetchInfo["origin"],clientSource=clientSource,clientDevice=_fetchInfo["clientDevice"],userAgent=_fetchInfo["userAgent"],browser=_fetchInfo["browser"],userInfo=str(request.META))
    _inst.setIpToLocation()
    return _inst

    

class EmailGrabView(APIView):
    permission_classes = (AllowAny,)
    
    
    def post(self, request, format=None):

        email = request.data.get('email','')
        _type = request.GET.get('type','common')
        clientSource = CLIENT_SOURCE_DICT.get(_type,0)
        if email:
            try:
                _fetchInfo = getUseFulInformation(request.META)
                _inst = EmailGrab.objects.create(email=email,userIp=_fetchInfo["userIp"],clientSource=clientSource,origin=_fetchInfo["origin"],clientDevice=_fetchInfo["clientDevice"],userAgent=_fetchInfo["userAgent"],browser=_fetchInfo["browser"],userInfo=str(request.META))
                _ctThread = Thread(target=addLocationToEmailGrab,args=(_inst.id,))
                _ctThread.start()
            except:
                try:
                    _inst = EmailGrab.objects.create(email=email,userInfo=str(request.META))
                    _ctThread = Thread(target=addLocationToEmailGrab,args=(_inst.id,))
                    _ctThread.start()
                except:
                    pass
        return Response('', status=status.HTTP_200_OK)
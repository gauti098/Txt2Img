from rest_framework import serializers
import os
from rest_framework.exceptions import AuthenticationFailed
from google.oauth2 import id_token
from google.auth.transport import requests as google_req
from django.conf import settings
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
from accounts.models import DEFAULT_ORGANIZATION_NAME, Organization

import requests
from django.core.files.base import ContentFile
from accounts.models import FAQuestions



class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQuestions
        fields = ('id','faqCategory','description','video','videoThumbnail')


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ('name','subs_start','subs_end','subdomain','logo','fav_icon',)
        extra_kwargs = {
            'name': {'read_only': True},
            'subs_start': {'read_only': True},
            'subs_end': {'read_only': True}
        }

from campaignAnalytics.models import CampaignProspect
class OrganizationUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('first_name','email','last_login','org_is_admin')
    
    def to_representation(self, instance):
        data = super(OrganizationUserSerializer, self).to_representation(instance)
        data['totalProspect'] = None
        data['engagementRate'] = None
        if not instance.is_verified:
            data['last_login'] = "Invitation Pending"
            data['first_name'] = None
        else:
            data['last_login'] = instance.last_login.strftime("%I:%M %p, %b %d,%Y")
            totalProspect = CampaignProspect.objects.filter(campaign__user=instance)
            data['totalProspect'] = totalProspect.count()
            if data['totalProspect']>0:
                data['engagementRate'] = round((totalProspect.filter(isLinkedOpend=True).count()/data['totalProspect'])*100,2)
            else:
                data['engagementRate'] = 0
        return data




class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('id','first_name', 'last_name','email','profile_image','phone_number','calendar_url','facebook_url','twitter_url','linkedin_url','organization','org_is_admin','usedVideoCredit','totalVideoCredit','subs_start','subs_end' ,'date_joined')
        extra_kwargs = {
            'email': {'read_only': True},
            'organization': {'read_only': True},
            'org_is_admin': {'read_only': True},
        }

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['organization'] = OrganizationSerializer(instance.organization).data
        return response



def register_social_user(userRequest,provider, first_name, last_name, email, profile_url,name):
    filtered_user_by_email = get_user_model().objects.filter(email=email)

    if filtered_user_by_email.exists():
        user = filtered_user_by_email[0]
        if not user.is_verified:
            if settings.AUTH_SIGNUP_AUTO_VERIFY:
                user.is_verified = True
            user.auth_provider = 'google'
            user.save()
        if bool(user.first_name)==False and bool(user.last_name) == False:
            user.first_name = first_name
            user.last_name = last_name
            user.save()
        if not bool(user.profile_image):
            response = requests.get(profile_url)
            user.profile_image.save(f"{name}_{email}.jpg", ContentFile(response.content), save=True)
        elif user.profile_image.name=='user_profile/default.jpg':
            response = requests.get(profile_url)
            user.profile_image.save(f"{name}_{email}.jpg", ContentFile(response.content), save=True)

        if not user.is_verified:
            return {'message': {'email': {'status': 3}},'redirectTo': settings.AUTH_SIGNUP_AUTO_REDIRECT,'isError': True}
        elif user.is_active:
            if bool(user.organization):
                token, created = Token.objects.get_or_create(user=user)
                return {'token': token.key,'user': UserSerializer(user,context={'request': userRequest}).data}
            else:
                return {'message': {'email': {'status': 2}},'isError': True}
        else:
            return {'message': {'email': {'status': 0}},'isError': True}
            
    else:
        user = {'first_name': first_name,'last_name': last_name, 'email': email,'password': os.environ.get('SOCIAL_SECRET')}
        user = get_user_model().objects.create_user(**user)
        if settings.AUTH_SIGNUP_AUTO_VERIFY:
            user.is_verified = True
        user.isCP = False
        user.auth_provider = provider

        # Add Default Organization
        user.addDefaultOrganization()
        
        #fetch profile url
        response = requests.get(profile_url)
        user.profile_image.save(f"{name}_{email}.jpg", ContentFile(response.content), save=True)
        if not user.is_verified:
            return {'message': {'email': {'status': 3}},'redirectTo': settings.AUTH_SIGNUP_AUTO_REDIRECT,'isError': True}
        elif user.is_active:
            if bool(user.organization):
                token, created = Token.objects.get_or_create(user=user)
                return {'token': token.key,'user': UserSerializer(user,context={'request': userRequest}).data}
            else:
                return {'message': {'email': {'status': 2}},'isError': True}
        else:
            return {'message': {'email': {'status': 0}},'isError': True}
        #token, created = Token.objects.get_or_create(user=user)
        #return {'token': token.key,"user": UserSerializer(user).data}

class GoogleSocialAuthSerializer(serializers.Serializer):
    password = serializers.CharField()

    def validate_password(self, password):

        try:
            user_data = id_token.verify_oauth2_token(password, google_req.Request(),settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY)
        except Exception as e:
            return {'message': {'password': {'status': 0}},'isError': True}

        if user_data['aud'] != settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY and user_data['email_verified']==False:
            raise AuthenticationFailed('oops, who are you?')

        first_name = user_data["given_name"]
        last_name = user_data["family_name"]
        name = user_data["name"]
        email = user_data['email']
        profile_url = user_data['picture']
        provider = 'google'

        return register_social_user(userRequest = self.context['request'],provider=provider, first_name=first_name, last_name=last_name, email=email, profile_url=profile_url,name=name)



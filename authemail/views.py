from datetime import date, datetime

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.utils.translation import gettext as _

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authemail.models import SignupCode, EmailChangeCode, PasswordResetCode
from authemail.models import send_multi_format_email
from authemail.serializers import SignupSerializer, LoginSerializer
from authemail.serializers import PasswordResetSerializer
from authemail.serializers import PasswordResetVerifiedSerializer
from authemail.serializers import EmailChangeSerializer
from authemail.serializers import PasswordChangeSerializer
from accounts.serializers import UserSerializer
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from authemail.models import ChangeOrgCode


class Signup(APIView):
    permission_classes = (AllowAny,)
    serializer_class = SignupSerializer

    def post(self, request, format=None):
        serializer = self.serializer_class(data=request.data)
        orgCode = request.data.get('code',None)
        orgInst = None
        orgVerified = None
        if orgCode:
            orgVerified,orgInst = ChangeOrgCode.objects.set_org_is_verified(orgCode)
            if not orgVerified:
                content = {'message': {'code': {'status': 0}},'isError': True}
                return Response(content, status=status.HTTP_200_OK)
            else:
                delta = date.today() - orgInst.created_at.date()
                if delta.days > ChangeOrgCode.objects.get_expiry_period():
                    orgInst.delete()
                    content = {'message': {'code': {'status': 1}},'isError': True}
                    return Response(content, status=status.HTTP_200_OK)

        email = request.data.get("email","")
        password = request.data.get("password","")
        first_name = request.data.get("first_name","")
        error_message = {'message': {},'isError': True}
        isError = False
        #vaildate Password
        try:
            validate_password(password)
        except:
            isError = True
            error_message["message"]["password"]={"status": 0,"message": "Password is not Valid."}
        ## validate email
        try:
            validate_email(email)
        except Exception as e:
            isError = True
            error_message["message"]["email"]={"status": 0,"message": "Email is not Valid."}
        
        if not first_name:
            isError = True
            error_message["message"]["first_name"]={"status": 0,"message": "First Name is not Valid."}
        if isError:
            return Response(error_message, status=status.HTTP_200_OK)

        if serializer.is_valid():
            if orgVerified and orgInst:
                orgInst.user.first_name = first_name    
                orgInst.user.set_password(password)
                orgInst.user.save()
                orgInst.delete()
                return Response({'message': 'Account Created',"email": orgInst.user.email,'isError': False},status=status.HTTP_200_OK)


            must_validate_email = getattr(settings, "AUTH_EMAIL_VERIFICATION", True)

            try:
                user = get_user_model().objects.get(email=email)
                
                if user.is_verified:
                    isError = True
                    error_message['message']['email'] = {'status': 1}
                if isError:
                    return Response(error_message, status=status.HTTP_200_OK)

                try:
                    # Delete old signup codes
                    signup_code = SignupCode.objects.get(user=user)
                    signup_code.delete()
                except SignupCode.DoesNotExist:
                    pass
                
            except get_user_model().DoesNotExist:
                user = get_user_model().objects.create_user(email=email)

            # Set user fields provided
            user.set_password(password)
            user.first_name = first_name
            if not must_validate_email and settings.AUTH_SIGNUP_AUTO_VERIFY:
                user.is_verified = True
                send_multi_format_email('welcome_email',
                                        {'email': user.email, },
                                        target_email=user.email)
            user.save()
            user.addDefaultOrganization()

            if must_validate_email and settings.AUTH_SIGNUP_AUTO_VERIFY:
                # Create and associate signup code
                ipaddr = self.request.META.get('REMOTE_ADDR', '0.0.0.0')
                signup_code = SignupCode.objects.create_signup_code(user, ipaddr)
                signup_code.send_signup_email()

            if not settings.AUTH_SIGNUP_AUTO_VERIFY:
                return Response({'message': {'email': {'status': 3}},'redirectTo': settings.AUTH_SIGNUP_AUTO_REDIRECT,'isError': True}, status=status.HTTP_200_OK)
            
            return Response({'message': 'Email Sent','isError': False}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SignupVerify(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, format=None):
        code = request.GET.get('code', '')
        verified,user = SignupCode.objects.set_user_is_verified(code)
        if verified:
            try:
                signup_code = SignupCode.objects.get(code=code)
                signup_code.delete()
            except SignupCode.DoesNotExist:
                pass
            content = {'message': 'Email verified.','isError': False,'email': user.email}
            return Response(content, status=status.HTTP_200_OK)
        else:
            content = {'message': 'Unable to verify user.','isError': True}
            return Response(content, status=status.HTTP_200_OK)


class Login(APIView):
    permission_classes = (AllowAny,)
    serializer_class = LoginSerializer
    

    def post(self, request, format=None):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            email = serializer.data['email']
            password = serializer.data['password']
            user = authenticate(email=email, password=password)

            if user:
                if user.is_verified:
                    if user.is_active:
                        if bool(user.organization):
                            user.last_login = datetime.now()
                            user.save()
                            token, created = Token.objects.get_or_create(user=user)
                            return Response({'token': token.key,'user': UserSerializer(user,context={'request': request}).data,'isError': False},status=status.HTTP_200_OK)
                        else:
                            return Response({'message': {'email': {'status': 2}},'isError': True},status=status.HTTP_200_OK)
                    else:
                        return Response({'message': {'email': {'status': 0}},'isError': True},status=status.HTTP_200_OK)
                else:
                    return Response({'message': {'email': {'status': 1}},'isError': True},status=status.HTTP_200_OK)
            else:
                return Response({'message': {'password': {'status': 0}},'isError': True},status=status.HTTP_200_OK)
        else:
            return Response({'message': serializer.errors,'isError': True},status=status.HTTP_200_OK)


class Logout(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, format=None):
        """
        Remove all auth tokens owned by request.user.
        """
        tokens = Token.objects.filter(user=request.user)
        for token in tokens:
            token.delete()
        content = {'success': 'User logged out.'}
        return Response(content, status=status.HTTP_200_OK)


class PasswordReset(APIView):
    permission_classes = (AllowAny,)
    serializer_class = PasswordResetSerializer

    def post(self, request, format=None):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            email = serializer.data['email']

            try:
                user = get_user_model().objects.get(email=email)

                # Delete all unused password reset codes
                PasswordResetCode.objects.filter(user=user).delete()

                if user.is_verified and user.is_active:
                    password_reset_code = \
                        PasswordResetCode.objects.create_password_reset_code(user)
                    password_reset_code.send_password_reset_email()
                    content = {'email': email}
                    return Response({'message': content,'isError': False}, status=status.HTTP_200_OK)

            except get_user_model().DoesNotExist:
                pass

            content = {'email': email}
            return Response({'message': content,'isError': False}, status=status.HTTP_200_OK)


            # content = {'email': {'status': 0}}
            # return Response({'message': content,'isError': True}, status=status.HTTP_200_OK)

        else:
            return Response({'message': serializer.errors,'isError': True},status=status.HTTP_200_OK)


class PasswordResetVerify(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, format=None):
        code = request.GET.get('code', '')

        try:
            password_reset_code = PasswordResetCode.objects.get(code=code)

            # Delete password reset code if older than expiry period
            delta = date.today() - password_reset_code.created_at.date()
            if delta.days > PasswordResetCode.objects.get_expiry_period():
                password_reset_code.delete()
                return Response({'message': {'code': {'status': 1}},'isError': True}, status=status.HTTP_200_OK)
            return Response({'message': 'verified','isError': False,'email': password_reset_code.user.email}, status=status.HTTP_200_OK)
        except PasswordResetCode.DoesNotExist:
            return Response({'message': {'code': {'status': 1}},'isError': True}, status=status.HTTP_200_OK)


class PasswordResetVerified(APIView):
    permission_classes = (AllowAny,)
    serializer_class = PasswordResetVerifiedSerializer

    def post(self, request, format=None):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            code = serializer.data['code']
            password = serializer.data['password']

            try:
                validate_password(password)
            except Exception as e:
                return Response({'message': {'password': {'status': 0}},'isError': True},status=status.HTTP_200_OK)

            try:
                password_reset_code = PasswordResetCode.objects.get(code=code)
                password_reset_code.user.set_password(password)
                if not password_reset_code.user.isCP:
                    password_reset_code.user.isCP = True
                password_reset_code.user.save()

                # Delete password reset code just used
                password_reset_code.delete()

                return Response({'message': 'Password Changed','isError': False},status=status.HTTP_200_OK)
            except PasswordResetCode.DoesNotExist:
                return Response({'message': {'code': {'status': 0}},'isError': True}, status=status.HTTP_200_OK)
        else:
            return Response({'message': serializer.errors,'isError': True}, status=status.HTTP_200_OK)

            


class EmailChange(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = EmailChangeSerializer

    def post(self, request, format=None):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            user = request.user

            # Delete all unused email change codes
            EmailChangeCode.objects.filter(user=user).delete()

            email_new = serializer.data['email']

            try:
                user_with_email = get_user_model().objects.get(email=email_new)
                if user_with_email.is_verified and user_with_email.auth_provider == 'email':
                    content = {'detail': 'Email address already taken.'}
                    return Response(content, status=status.HTTP_400_BAD_REQUEST)
                else:
                    # If the account with this email address is not verified,
                    # give this user a chance to verify and grab this email address
                    raise get_user_model().DoesNotExist

            except get_user_model().DoesNotExist:
                email_change_code = EmailChangeCode.objects.create_email_change_code(user, email_new)

                email_change_code.send_email_change_emails()

                content = {'email': email_new}
                return Response(content, status=status.HTTP_201_CREATED)

        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)


class EmailChangeVerify(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, format=None):
        code = request.GET.get('code', '')

        try:
            # Check if the code exists.
            email_change_code = EmailChangeCode.objects.get(code=code)

            # Check if the code has expired.
            delta = date.today() - email_change_code.created_at.date()
            if delta.days > EmailChangeCode.objects.get_expiry_period():
                email_change_code.delete()
                raise EmailChangeCode.DoesNotExist()

            # Check if the email address is being used by a verified user.
            try:
                user_with_email = get_user_model().objects.get(email=email_change_code.email)
                if user_with_email.is_verified and user_with_email.auth_provider=='email':
                    # Delete email change code since won't be used
                    email_change_code.delete()

                    content = {'detail': 'Email address already taken.'}
                    return Response(content, status=status.HTTP_400_BAD_REQUEST)
                else:
                    # If the account with this email address is not verified,
                    # delete the account (and signup code) because the email
                    # address will be used for the user who just verified.
                    user_with_email.delete()
            except get_user_model().DoesNotExist:
                pass

            # If all is well, change the email address.
            email_change_code.user.email = email_change_code.email
            email_change_code.user.save()

            # Delete email change code just used
            email_change_code.delete()

            content = {'success': 'Email address changed.'}
            return Response(content, status=status.HTTP_200_OK)
        except EmailChangeCode.DoesNotExist:
            content = {'detail': 'Unable to verify user.'}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)


class PasswordChange(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PasswordChangeSerializer

    def post(self, request, format=None):
        user = request.user
        oldPassword = request.data.get('oldpassword','')
        newPassword = request.data.get('newpassword','')
        if not oldPassword:
            return Response({'oldpassword': ["This Field is required."]},status=status.HTTP_400_BAD_REQUEST)
        if not newPassword:
            return Response({'newpassword': ["This Field is required."]},status=status.HTTP_400_BAD_REQUEST)

        success = user.check_password(oldPassword)
        if success:
            try:
                validate_password(newPassword)
                user.set_password(newPassword)
                user.save()
                content = {'success': 'Password changed.'}
                return Response(content, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'newpassword': e},status=status.HTTP_400_BAD_REQUEST)

        else:
            return Response({'oldpassword': ['Password is not Valid']}, status=status.HTTP_200_OK)


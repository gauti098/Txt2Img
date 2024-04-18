import json
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.response import Response

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.validators import validate_email
from utils.common import convertInt


from paymentHandler.models import (
    PAYMENT_INFO,PaymentHistory,
    PaymentIntentLogs,CURRENCY_TYPE
)

from django.conf import settings
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

def getDefaultCustomerId(email,_currencyType='usd'):
    try:
        # _cstmL = stripe.Customer.list(email=email,limit=1)
        # if len(_cstmL.data):
        #     return (True,_cstmL.data[0].id)
        # else:
        _cstm = None
        if _currencyType == 'inr':
            _cstm = stripe.Customer.create(
                name=email.split('@')[0],
                email = email,
                address={ 
                    "line1": 'lajpat nagar',
                    "postal_code": '110001',
                    "city": 'Delhi',
                    "state": 'DL', 
                    "country": 'IN'
                } 
            )
        else:
            _cstm = stripe.Customer.create(
                name=email.split('@')[0],
                email = email,
                address={ 
                    "line1": '510 Townsend St',
                    "postal_code": '98140',
                    "city": 'San Francisco',
                    "state": 'CA', 
                    "country": 'US'
                } 
            )
        return (True,_cstm.id)
    except:
        return (False,None)


from accounts.views import getEmailGrabInst

class StripSessionIdView(APIView):
    permission_classes = (AllowAny,)
    CURRENCY_TYPE_DICT = {kk[1]:kk[0] for kk in CURRENCY_TYPE}

    def post(self, request, format=None):
        isError = False
        isEmailOptional = False
        try:
            _paymentType = convertInt(request.data.get('paymentType',None),None)
            _email = request.data.get('email',None)
        except:
            isError = True
            return Response({'message': 'Data is not Valid.','isError': isError},status=status.HTTP_200_OK)
            
        _paymentInfo = None
        _errorMessage = {"isError": True}

        # yearly deal 
        _paymentType = 1
        if _paymentType == None:
            _errorMessage["paymentType"] = "This Field is required."
            isError = True
        else:
            _paymentInfo = PAYMENT_INFO.get(_paymentType,None)
            if not _paymentInfo:
                _errorMessage["paymentType"] = "This Field is not Valid."
                isError = True
        if not isEmailOptional:
            if not _email:
                _errorMessage["email"] = "This Field is required."
                isError = True
            else:
                try:
                    validate_email(_email)
                except:
                    _errorMessage["email"] = "This Field is not Valid."
                    isError = True
        if isError:
            return Response(_errorMessage,status=status.HTTP_200_OK)

        _grabEmailInst = getEmailGrabInst(_email,request,origin="https://payment.autovid.ai")

        # check if deal ended
        _query = PaymentHistory.objects.filter(paymentStatus=1,paymentType=2).values('email').distinct()
        if _query.count()>40:
            return Response({'sessionUrl': "https://autovid.ai/",'isDealEnded': True},status=status.HTTP_200_OK)

        _crntCurrency = 'usd'
        if _grabEmailInst.location.countryCode == 'IN':
            _crntCurrency = 'inr'
        
        # only for test
        if _email == 'payment_test@autovid.ai':
            _paymentInfo["price"][_crntCurrency] = 100

        _inst = PaymentHistory(email=_email,paymentType=_paymentType,paymentAmount=_paymentInfo["price"][_crntCurrency],currencyType = self.CURRENCY_TYPE_DICT[_crntCurrency])
        _inst.save()



        # create customer for prevent address fill on payment
        #_getCustomer = getDefaultCustomerId(_email,_crntCurrency)
        _getCustomer = []

        
            
        session = None
        _payData = {
            "success_url": 'http://autovid.ai/pricing?paymentSuccess=1',
            "cancel_url": 'http://autovid.ai/pricing?paymentSuccess=0',
            "mode": 'payment', #'payment', 'subscription',
            "payment_method_types": ["card"],
            "line_items": [{
                'name': _paymentInfo["name"],
                'quantity': 1,
                'currency': _crntCurrency,
                'amount': f"{_inst.paymentAmount}",
            }],
            "metadata": {'_orderId': f"{_inst.id}"}
        }

        if 0:
            session = stripe.checkout.Session.create(
                customer=_getCustomer[1],
                success_url=_payData["success_url"],
                cancel_url=_payData["cancel_url"],
                mode=_payData["mode"],
                payment_method_types = _payData["payment_method_types"],
                line_items=_payData["line_items"],
                metadata=_payData["metadata"]
            )
        else:
            session = stripe.checkout.Session.create(
                customer_email=_email,
                success_url=_payData["success_url"],
                cancel_url=_payData["cancel_url"],
                mode=_payData["mode"],
                payment_method_types = _payData["payment_method_types"],
                line_items=_payData["line_items"],
                metadata=_payData["metadata"]
            )
        _sessionDict = session.to_dict()
        _inst.sessionInfo=json.dumps(_sessionDict)
        _inst.paymentIntentId = _sessionDict.get('payment_intent','')
        _inst.save()
        return Response({'sessionUrl': session.url,'isDealEnded': False},status=status.HTTP_200_OK)

from datetime import datetime
ALL_SUCCESS_EVENTS = [
    'checkout.session.completed',
    'payment_intent.succeeded'

]

ALL_FAILURE_EVENTS = [
    'checkout.session.expired',
    'payment_intent.canceled'

]

@csrf_exempt
def stripe_webhook(request):
    
    endpoint_secret = settings.STRIPE_ENDPOINT_SECRET
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    _fileP = open('/home/govind/VideoAutomation/logs/stripe_payment_hook.log','a')
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        _fileP.write(f"{datetime.now()} Invalid payload.\n")
        _fileP.close()
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        _fileP.write(f"{datetime.now()} Invalid signature.\n")
        _fileP.close()
        return HttpResponse(status=400)

    _fileP.write(f"{datetime.now()} Event: {event}.\n")
    _fileP.close()
    _eventType = event['type']
    if _eventType.split('.')[0] == 'payment_intent':
        _paymentIntentID = event.get('data',{}).get('object',{}).get('id',None)
        if _paymentIntentID:
            _payObj,ct = PaymentIntentLogs.objects.get_or_create(paymentIntentId=_paymentIntentID,eventType=_eventType,logs=json.dumps(event))
            _payInst = PaymentHistory.objects.filter(paymentIntentId=_paymentIntentID)
            if _payInst:
                _inst = _payInst.first()
                if _eventType in ALL_SUCCESS_EVENTS:
                    _inst.onSuccess()
                elif _eventType in ALL_FAILURE_EVENTS:
                    _inst.onFailure()

    elif _eventType.split('.')[0] == 'checkout':
        _paymentIntentID = event.get('data',{}).get('object',{}).get('payment_intent',None)
        if _paymentIntentID:
            _payObj,ct = PaymentIntentLogs.objects.get_or_create(paymentIntentId=_paymentIntentID,eventType=_eventType,logs=json.dumps(event))
            _payInst = PaymentHistory.objects.filter(paymentIntentId=_paymentIntentID)
            if _payInst:
                _inst = _payInst.first()
                if _eventType in ALL_SUCCESS_EVENTS:
                    _inst.onSuccess()
                elif _eventType in ALL_FAILURE_EVENTS:
                    _inst.onFailure()
                
    return HttpResponse(status=200)


'''
import stripe
from django.conf import settings
stripe.api_key = settings.STRIPE_SECRET_KEY

a = stripe.Customer.create(
    name= 'test',
    address={ 
        "line1": '510 Townsend St',
        "postal_code": '98140',
        "city": 'San Francisco',
        "state": 'CA', 
        "country": 'US'
    } 
)
session = stripe.checkout.Session.create(
            customer="cus_LHD6gnA2rJbkg7",
            success_url='https://app.autovid.ai',
            cancel_url='https://autovid.ai/',
            mode='payment',
            payment_method_types = ["card"],
            line_items=[{
                'name': "Debug",
                'quantity': 1,
                'currency': 'usd',
                'amount': f"20",
            }],
            metadata={'_orderId': f"{10}"}
        )


b = stripe.PaymentIntent.create(
    { amount: '199', currency: 'usd', // payment_method_types: ['card'], off_session: true, confirm: true, customer: customer.id, description: "yesss", shipping: { name: 'test', address: { line1: '510 Townsend St', postal_code: '98140', city: 'San Francisco', state: 'CA', country: 'US', }, }, }),
'''
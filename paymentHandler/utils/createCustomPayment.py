from paymentHandler.models import PaymentHistory,PAYMENT_INFO,CURRENCY_TYPE
from django.conf import settings
import json
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


CURRENCY_TYPE_DICT = {kk[1]:kk[0] for kk in CURRENCY_TYPE}

def createCustomPayment(email,price,currencyType='usd',isEmail=True):
    _paymentType = 2
    _paymentInfo = PAYMENT_INFO.get(_paymentType,None)
    _inst = PaymentHistory(email=email,paymentType=_paymentType,paymentAmount=price*100,currencyType =CURRENCY_TYPE_DICT[currencyType])
    _inst.save()

    _payData = {
        "success_url": 'http://autovid.ai/pricing?paymentSuccess=1',
        "cancel_url": 'http://autovid.ai/pricing?paymentSuccess=0',
        "mode": 'payment',
        "payment_method_types": ["card"],
        "line_items": [{
            'name': _paymentInfo["name"],
            'quantity': 1,
            'currency': currencyType,
            'amount': f"{_inst.paymentAmount}",
        }],
        "metadata": {'_orderId': f"{_inst.id}","email": email}
    }
    
    if isEmail:
        session = stripe.checkout.Session.create(
            customer_email=email,
            success_url=_payData["success_url"],
            cancel_url=_payData["cancel_url"],
            mode=_payData["mode"],
            payment_method_types = _payData["payment_method_types"],
            line_items=_payData["line_items"],
            metadata=_payData["metadata"]
        )
    else:
        session = stripe.checkout.Session.create(
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
    return {'sessionUrl': session.url,"inst": _inst}


'''
from paymentHandler.utils.createCustomPayment import createCustomPayment
_d = createCustomPayment('custom_user@autovid.ai',14999,'inr',False)
'''
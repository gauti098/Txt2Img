_payData = {
            "success_url": 'http://autovid.ai/pricing?paymentSuccess=1',
            "cancel_url": 'http://autovid.ai/pricing?paymentSuccess=0',
            "mode": 'subscription', #'payment', 'subscription',
            "payment_method_types": ["card"],
            "line_items": [{
                'price': 'price_1LBkNnSEa2s2jtNVTX5tbNAz',
                'quantity': 1,
            }],
            "metadata": {'_orderId': f"1234"}
        }

_email = 'sehaj@autovid.ai'

session = stripe.checkout.Session.create(
    customer_email=_email,
    success_url=_payData["success_url"],
    cancel_url=_payData["cancel_url"],
    mode=_payData["mode"],
    payment_method_types = _payData["payment_method_types"],
    line_items=_payData["line_items"],
    metadata=_payData["metadata"]
)

session.url
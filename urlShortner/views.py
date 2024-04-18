from django.shortcuts import render
from urlShortner.models import CampaignUrlShortner
from django.shortcuts import redirect
from django.conf import settings

def campaignUrlRedirect(request, slugs):
    try:
        inst = CampaignUrlShortner.objects.get(slug=slugs)
        _currentUrl = inst.getMainUrl()
        return redirect(_currentUrl)
    except:
        return redirect("/")
    
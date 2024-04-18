from django.db import models
from urllib.parse import quote
from django.utils.crypto import get_random_string
import string
from uuid import uuid1

_TYPE = (
    (0,'CAMPAIGN_SOLOCAMPAIGN'),
    (1,'CAMPAIGN_GROUPSINGLECAMPAIGN'),
    (2,'NEWVIDEOCREATOR_MAINVIDEOGENERATE'),
    (3,'NEWVIDEOCREATOR_GROUPHANDLER'),
)

APP_TYPE = (
    (0,'salespage'),
    (1,'autovid'),
)

SHORTNER_BASE_URL = {
    0: "https://autovid.ai",#"https://autogenerate.ai",
    1: "https://autovid.ai"
}

FRONTEND_URL = {
    0: "https://autovid.ai",#"https://salespage.autogenerate.ai",
    1: "https://autovid.ai"
}

class CampaignUrlShortner(models.Model):
    slug = models.CharField(max_length=36, unique=True)
    _type = models.IntegerField(default=0,choices=_TYPE)
    _appType = models.IntegerField(default=0,choices=APP_TYPE)
    mainId = models.CharField(default="",max_length=250)
    uniqueId = models.CharField(default="",max_length=250)

    def generateSlug(self):
        RETRY = 180
        complexity = 4
        for ii in range(RETRY):
            _complexity = complexity + int(ii/5)
            _slug = get_random_string(_complexity,allowed_chars=string.ascii_lowercase+string.digits)
            query = CampaignUrlShortner.objects.filter(slug=_slug)
            if not query:
                return _slug
        return str(uuid1())

    def getUrl(self):
        if self._type == 2 or self._type == 3:
            return f"{FRONTEND_URL[self._appType]}/p/{self.slug}"
        return f"{SHORTNER_BASE_URL[self._appType]}/c/{self.slug}"
    
    def getMainUrl(self):
        if self._type == 2:
            return f"{FRONTEND_URL[self._appType]}/p/{self.mainId}?email=video_creator"
        elif self._type == 3:
            return f"{FRONTEND_URL[self._appType]}/p/{self.mainId}?email=campaign_test__batch__"
        elif self._type==1:
            return f"{FRONTEND_URL[self._appType]}/p/{self.mainId}?email={quote(self.uniqueId)}"
        elif self._type==0:
            return f"{FRONTEND_URL[self._appType]}/p/{self.mainId}"
        else:
            return f"{self.mainId}" 
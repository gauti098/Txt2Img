from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
import json,requests
from campaign.models import EmailClient


data = json.load(open('emailClientData/emailM.json','r'))
for ii in data:
    _inst,ct = EmailClient.objects.get_or_create(name=ii['name'])
    if ct:
        img_temp = NamedTemporaryFile(delete=True)
        img_temp.write(requests.get(ii['url']).content)
        img_temp.flush()

        _inst.src.save(f"{ii['url'].split('/')[-1]}", File(img_temp))
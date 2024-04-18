from appAssets.models import AvatarSounds,VoiceLanguage,CountryDetails
import json


soundData = json.load(open('createSamples/microsoftTTS/microsoftVoiceList.json','r'))
GENDER = {"Male": 1, "Female": 2}
# vlang_ids = AvatarSounds.objects.filter(provider = 'microsoft').values_list('voice_language', flat=True)
# query = VoiceLanguage.objects.filter(pk__in=vlang_ids)
# microsoftApi.generateSound(text,'en-US-EricNeural','/home/govind/VideoAutomation/src/t.mp3')
# AvatarSounds.objects.filter(voice_language = q).exclude(provider = 'microsoft')
for _s in soundData:
    data = {
        "name": _s["displayName"],
        "gender": GENDER[_s["genders"]],
        "provider": "microsoft",
        "provider_id": _s["name"]
    }
    langCode = f"{_s['languages'].split('-')[0]}-{_s['languages'].split('-')[1].upper()}"
    # voice language
    _cInst = CountryDetails.objects.get(code=_s["name"].split('-')[1])
    _lInst,ct = VoiceLanguage.objects.get_or_create(name=_s['ln'],code=langCode)
    if _lInst.tags:
        _lInst.tags = f'{_lInst.tags},{_s["style"]}'
    else:
        _lInst.tags = f'{_lInst.tags}'
    _lInst.country.add(_cInst)
    _lInst.image.name = _cInst.image.name
    _lInst.save()
    soundInst,ct = AvatarSounds.objects.get_or_create(name=data['name'],gender=data['gender'],provider=data['provider'],provider_id=data['provider_id'],voice_language=_lInst)

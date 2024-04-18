from appAssets.models import AvatarSounds,AvatarImages
from appAssets.models import AvatarSoundCombination
import json
getFirstAS = AvatarSounds.objects.get(id=1)


GENDER_CHOICES = (
    (1, ("Male")),
    (2, ("Female")),
)
#{     "name": "en-IN-Wavenet-A",     "pitch": 0,     "language_code": "en-US"  }
newSoundConfig = [
    [{"name": "en-IN-Wavenet-C","pitch": 0,"language_code": "en-IN"},GENDER_CHOICES[0][0]],
    [{"name": "en-IN-Wavenet-D","pitch": 0,"language_code": "en-IN"},GENDER_CHOICES[1][0]],
    [{"name": "en-US-Wavenet-C","pitch": 0,"language_code": "en-US"},GENDER_CHOICES[1][0]],
    [{"name": "en-US-Wavenet-B","pitch": 0,"language_code": "en-US"},GENDER_CHOICES[0][0]],
    [{"name": "en-GB-Wavenet-A","pitch": 0,"language_code": "en-GB"},GENDER_CHOICES[1][0]],
    [{"name": "en-GB-Wavenet-B","pitch": 0,"language_code": "en-GB"},GENDER_CHOICES[0][0]],
]


allAvatars = AvatarImages.objects.all().exclude(id__in=[1,2])

for ii in newSoundConfig[1:5]:
    print('Adding New Sound',ii)
    soundInst,ct = AvatarSounds.objects.get_or_create(name=ii[0]['name'],gender=ii[1],provider=getFirstAS.provider,provider_id=json.dumps(ii[0]),samples=getFirstAS.samples)
    for av in allAvatars:
        avatarSoundCombInst = AvatarSoundCombination.objects.get(avatarSound=getFirstAS,avatarImg=av)
        avSc,ct = AvatarSoundCombination.objects.get_or_create(avatarImg=av,avatarSound=soundInst,video=avatarSoundCombInst.video,sound=avatarSoundCombInst.sound,previewVideo=avatarSoundCombInst.previewVideo)
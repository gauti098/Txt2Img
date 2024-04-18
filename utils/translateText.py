import six
from google.cloud import translate_v2 as translate
from google.oauth2 import service_account

def translate_text(target, text="Hi, I am glad to be your virtual agent."):
    _finalText = text
    try:
        translate_client = translate.Client(credentials=service_account.Credentials.from_service_account_file('credentials/GoogleAuthAccount.json'))

        ## reverse language code to target
        fdata = {'cmn-CN': 'zh-CN',"cmn-TW": "zh-TW","yue-HK": "zh","nb-NO": "no","fil-PH": "tl"}
        textTarget = None
        try:
            textTarget = fdata[target]
        except:
            textTarget = target.split('-')[0]

        if isinstance(text, six.binary_type):
            text = text.decode("utf-8")

        result = translate_client.translate(text, target_language=textTarget)
        _finalText = result["translatedText"]
    except:
        pass
    return _finalText

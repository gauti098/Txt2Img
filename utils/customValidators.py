from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

URL_VALIDATE = URLValidator()
def isValidUrl(url):
    try:
        ## check is http or https
        _url = url.lower()
        if not (_url.startswith('https://') or _url.startswith('http://')):
            url = f"https://{url}"
        URL_VALIDATE(url)
        return True,url
    except:
        return False,None

def validate_url(url):
    try:
        ## check is http or https
        _url = url.lower()
        if not (_url.startswith('https://') or _url.startswith('http://')):
            url = f"https://{url}"
        URL_VALIDATE(url)
        return url
    except Exception as e:
        raise ValidationError(f"URL: {url} {e}")
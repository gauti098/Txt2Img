
from django.core.validators import validate_email,URLValidator

URLValidatorInst = URLValidator()
def validateMtag(mtag,tagvalue,isShowTagM=False):
    # text validator
    _dft = "This"
    if isShowTagM:
        _dft = mtag[0]
    message = ""
    if not tagvalue.strip():
        message = f"{_dft} field is Required."
        return (False,message)
    if mtag[1] == 'text':
        return (True,message)
    elif mtag[1] == 'url':
        try:
            URLValidatorInst(tagvalue)
            return (True,message)
        except:
            message = f"{_dft} field is not Valid Url."
            return (False,message)
    elif mtag[1] == 'email':
        try:
            validate_email(tagvalue)
            return (True,message)
        except:
            message = f"{_dft} field is not Valid Email."
            return (False,message)
    return (None,message)



def isEmailCommon(email):
    commonName = [
        'govind',
        'sehaj',
        'jai'
    ]
    for ii in commonName:
        if len(email.split(ii))>1:
            return True
    return False
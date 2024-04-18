from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

import re

def validate_color(value):
    if value[0]!='#':
        value="#"+value
    match = re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', value)
    if match:
        return value
    else:
        raise ValidationError("Hex Color is not Valid (eg #FFFFFF).")

class Colors(models.Model):

    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE,related_name='user_colors')
    colors = models.CharField(max_length=2000,null=True,blank=True,default="")

    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)


    def setColors(self,colors):
        validColors = []
        nonValidC = {}
        for indx,color in enumerate(colors.split(",")):
            try:
                validColors.append(validate_color(color))
            except:
                nonValidC[indx] = color
        self.colors = ','.join(validColors)
        self.save()
        return nonValidC

    def getColors(self):
        return [color for color in self.colors.split(",") if color]

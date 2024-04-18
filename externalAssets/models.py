from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


def updateSvgCurrentColor(path,color):
    _allData = None
    with open(path,'rb') as f:
        _allData = f.read()
        _allData = _allData.replace(b'currentColor',color)
        _allData = _allData.replace(b'currentcolor',color)
    with open(path,'wb') as f:
        f.write(_allData)
    


class Icons(models.Model):

    name = models.CharField(max_length=250)
    src = models.FileField(upload_to='externalAssets/icons/',blank=True,null=True)
    tags = models.CharField(max_length=250,null=True,blank=True)

    def __str__(self):
        return self.name

    def updateCurrentColorColors(self):
        updateSvgCurrentColor(self.src.path,b"#000000")

@receiver(post_save, sender=Icons, dispatch_uid="update_svg")
def update_icons_svg(sender, instance, **kwargs):
    updateSvgCurrentColor(instance.src.path,b"#000000")

class Shapes(models.Model):

    name = models.CharField(max_length=250)
    src = models.FileField(upload_to='externalAssets/shapes/',blank=True,null=True)
    tags = models.CharField(max_length=250,null=True,blank=True)

    def __str__(self):
        return self.name

@receiver(post_save, sender=Icons, dispatch_uid="update_svg")
def update_shapes_svg(sender, instance, **kwargs):
    updateSvgCurrentColor(instance.src.path,b"#ffffff")


class Elements(models.Model):

    name = models.CharField(max_length=250)
    src = models.FileField(upload_to='externalAssets/elements/',blank=True,null=True)
    tags = models.CharField(max_length=250,null=True,blank=True)

    def __str__(self):
        return self.name


class Emoji(models.Model):

    name = models.CharField(max_length=250)
    src = models.FileField(upload_to='externalAssets/emoji/',blank=True,null=True)
    tags = models.CharField(max_length=250,null=True,blank=True)

    def __str__(self):
        return self.name


class Mask(models.Model):

    name = models.CharField(max_length=250)
    src = models.FileField(upload_to='externalAssets/elements/',blank=True,null=True)
    _order = models.IntegerField(default=0)

    class Meta:
        ordering = ['-_order','name']

    def __str__(self):
        return self.name

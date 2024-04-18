
from externalAssets.models import (
    Icons,Elements,Shapes,
    Mask,Emoji
)
from rest_framework import serializers


class IconsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Icons
        fields = ('id','name','src',)


class ShapesSerializer(serializers.ModelSerializer):

    class Meta:
        model = Shapes
        fields = ('id','name','src',)


class ElementsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Elements
        fields = ('id','name','src',)


class EmojiSerializer(serializers.ModelSerializer):

    class Meta:
        model = Emoji
        fields = ('id','name','src',)


class MaskSerializer(serializers.ModelSerializer):

    class Meta:
        model = Mask
        fields = ('id','name','src',)
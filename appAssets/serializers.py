from rest_framework import serializers
import json
from appAssets.models import (
    AvatarImages,AvatarSounds,
    AvatarSoundCombination,VoiceLanguage,
    CountryDetails
)


class CountryDetailsSerializer(serializers.ModelSerializer):

    class Meta:
        model = CountryDetails
        fields = ('name','code',)


class VoiceLanguageSerializer(serializers.ModelSerializer):

    country = CountryDetailsSerializer(many=True)

    class Meta:
        model = VoiceLanguage
        fields = ('id','name','code','country','tags','image')


class AvatarImagesSerializer(serializers.ModelSerializer):

    class Meta:
        model = AvatarImages
        fields = ('id','name','gender','img','largeImg','transparentImage','avatarConfig')
    
    def to_representation(self, instance):
        data = super(AvatarImagesSerializer, self).to_representation(instance)
        data['avatarConfig'] = json.loads(data['avatarConfig'])
        data['avatarConfig']['faceCenterPoint'] = {'x': instance.faceSwapPositionX,'y': instance.faceSwapPositionY,'scale': instance.faceSwapScale}
        return data


class AvatarSoundsSerializer(serializers.ModelSerializer):

    class Meta:
        model = AvatarSounds
        fields = ('id','name','gender','samples')


class AvatarSoundCombinationSerializer(serializers.ModelSerializer):

    class Meta:
        model = AvatarSoundCombination
        fields = '__all__'
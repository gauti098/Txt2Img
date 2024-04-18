from rest_framework import serializers
import json
from aiAudio.models import AiAudio, AiCombineAudio


class AiAudioSerializer(serializers.ModelSerializer):

    class Meta:
        model = AiAudio
        fields = ('id','text','avatarSound','sound','soundDuration','isGenerated')


class AiCombineAudioSerializer(serializers.ModelSerializer):

    class Meta:
        model = AiCombineAudio
        fields = ('id','sound','soundDuration','isGenerated')
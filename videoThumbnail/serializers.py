from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.conf import settings

from videoThumbnail.models import MainThumbnail
from aiQueueManager.models import Colors

class MainThumbnailSerializer(serializers.ModelSerializer):
    class Meta:
        model = MainThumbnail
        fields = ('id','name','category','thumbnailImage','jsonData','isPersonalized','timestamp','updated',)
        extra_kwargs = {
            'category': {'read_only': True},
            'thumbnailImage': {'read_only': True},
            'timestamp': {'read_only': True},
            'updated': {'read_only': True}
        }

    def to_representation(self, instance):
        data = super(MainThumbnailSerializer, self).to_representation(instance)
        try:
            _user = self.context['request'].user
        except:
            _user = instance.user
        colorInst,ct = Colors.objects.get_or_create(user=_user)
        data['color'] = colorInst.getColors()
        return data


class MainThumbnailListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MainThumbnail
        fields = ('id','name','category','thumbnailImage','isPersonalized','timestamp','updated',)
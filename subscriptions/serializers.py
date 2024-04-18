from rest_framework import serializers

from subscriptions.models import VideoCreditUsage



class VideoCreditUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoCreditUsage
        fields = ('id','usedCreditType','name','usedCredit','timestamp',)

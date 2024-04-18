import json
from rest_framework import serializers
from videoCredit.models import UserCurrentSubscription,UserCredit,VideoCreditInfo

class UserCreditSerilizer(serializers.ModelSerializer):

    class Meta:
        model = UserCredit
        fields = ("usedCredit","totalCredit","creditType")


class CreditInfoSerilizer(serializers.ModelSerializer):
    subscription = UserCreditSerilizer(many=True)

    class Meta:
        model = UserCurrentSubscription
        fields = ("planName","subscription","subscriptionStart","subscriptionEnd")


class VideoCreditInfoSerilizer(serializers.ModelSerializer):
    
    class Meta:
        model = VideoCreditInfo
        fields = ("creditType","usedCredit","meta","timestamp")

    def to_representation(self, instance):
        data = super(VideoCreditInfoSerilizer,self).to_representation(instance)
        data["meta"] = json.loads(data["meta"])
        return data
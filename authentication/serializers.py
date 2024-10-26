from rest_framework import serializers

from .models import StationProfile, Journey


class StationProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationProfile
        fields = ('id', 'name', 'type')


class JourneySerializer(serializers.ModelSerializer):

    class Meta:
        model = Journey
        exclude = ('user',)

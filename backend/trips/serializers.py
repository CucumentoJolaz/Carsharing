from rest_framework import serializers
from .models import Trip
from cars.serializers import CarSerializer
from users.serializers import UserSerializer


class TripSerializer(serializers.ModelSerializer):
    car = CarSerializer(read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = Trip
        fields = '__all__'
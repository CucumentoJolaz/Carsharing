from rest_framework import serializers
from .models import Car, Rental

class CarSerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()

    def get_photo(self, obj):
        return obj.photo.url if obj.photo else None

    class Meta:
        model = Car
        fields = '__all__'


class RentalSerializer(serializers.ModelSerializer):

    button_text = serializers.SerializerMethodField()

    def get_button_text(self, obj):
        return obj.get_button_text()

    class Meta:
        model = Rental
        fields = '__all__'
        read_only_fields = ['car', 'user']
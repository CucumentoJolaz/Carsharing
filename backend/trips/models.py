from django.db import models
from django.contrib.auth import get_user_model
from cars.models import Car

User = get_user_model()


class Trip(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trips')
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='trips')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    start_latitude = models.FloatField()
    start_longitude = models.FloatField()
    end_latitude = models.FloatField(null=True, blank=True)
    end_longitude = models.FloatField(null=True, blank=True)
    distance_km = models.FloatField(default=0)
    duration_minutes = models.IntegerField(default=0)
    cost = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Trip #{self.id} - {self.user.username} - {self.car.license_plate}"
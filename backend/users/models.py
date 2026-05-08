from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    phone_number = models.CharField(max_length=15, blank=True)
    driver_license = models.CharField(max_length=20, blank=True)
    rating = models.FloatField(default=5.0)
    total_trips = models.IntegerField(default=0)

    def __str__(self):
        return self.username
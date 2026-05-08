import enum

from django.db import models
from django.utils import timezone

from users.models import User


class Car(models.Model):
    brand = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.IntegerField()
    license_plate = models.CharField(max_length=10, unique=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    fuel_level = models.IntegerField(default=100)
    odometer_reading = models.IntegerField(default=0)
    price_per_minute = models.DecimalField(max_digits=6, decimal_places=2, default=5.0)
    city = models.CharField(max_length=100, default='Москва')
    photo = models.ImageField(upload_to='car_photos/', null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"№{self.id} {self.brand} {self.model} ({self.year}) "

class Statuses(enum.Enum):
    BOOKED = 'booked'
    INSPECTING = 'inspecting'
    ACTIVE = 'active'
    COMPLETED = 'completed'
    CANCELED = 'canceled'


class Rental(models.Model):
    STATUS_CHOICES = [
        (Statuses.BOOKED.value, 'Забронирована'),
        (Statuses.INSPECTING.value, 'На осмотре пользователем'),
        (Statuses.ACTIVE.value, 'Аренда активна'),
        (Statuses.COMPLETED.value, 'Аренда завершена'),
        (Statuses.CANCELED.value, 'Аренда отменена'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=Statuses.BOOKED.value)
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    booked_at = models.DateTimeField(default=timezone.now)
    inspection_started_at = models.DateTimeField(null=True, blank=True)
    total_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)


    def __str__(self):
        return f"{self.id} Статус: {self.status} | авто: {self.car} |  пользователь: {self.user}"

    def get_button_text(self):
        button_texts = {
            Statuses.BOOKED.value:      'Начать осмотр',
            Statuses.INSPECTING.value:  'Начать аренду',
            Statuses.ACTIVE.value:      'Окончить аренду',
            Statuses.COMPLETED.value:   'Вернуться к списку автомобилей',
            Statuses.CANCELED.value:    'Вернуться к списку автомобилей',
        }
        return button_texts.get(self.status, '')
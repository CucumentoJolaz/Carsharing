import enum

from django.db import models
from django.utils import timezone
from django.db.models import Q
from users.models import User
from django.core.exceptions import ValidationError


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
    city = models.CharField(max_length=100, default="Москва")
    photo = models.ImageField(upload_to="car_photos/", null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"№{self.id} {self.brand} {self.model} ({self.year}) "


class Statuses(enum.Enum):
    BOOKED = "booked"
    INSPECTING = "inspecting"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELED = "canceled"


class Rental(models.Model):
    STATUS_CHOICES = [
        (Statuses.BOOKED.value, "Забронирована"),
        (Statuses.INSPECTING.value, "На осмотре пользователем"),
        (Statuses.ACTIVE.value, "Аренда активна"),
        (Statuses.COMPLETED.value, "Аренда завершена"),
        (Statuses.CANCELED.value, "Аренда отменена"),
    ]

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=Statuses.BOOKED.value
    )
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    booked_at = models.DateTimeField(default=timezone.now)
    inspection_started_at = models.DateTimeField(null=True, blank=True)
    total_cost = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )

    def __str__(self):
        return f"{self.id} Статус: {self.status} | авто: {self.car} |  пользователь: {self.user}"

    def get_button_text(self):
        button_texts = {
            Statuses.BOOKED.value: "Начать осмотр",
            Statuses.INSPECTING.value: "Начать аренду",
            Statuses.ACTIVE.value: "Окончить аренду",
            Statuses.COMPLETED.value: "Вернуться к списку автомобилей",
            Statuses.CANCELED.value: "Вернуться к списку автомобилей",
        }
        return button_texts.get(self.status, "")

    def clean(self):
        constraints = {
            Statuses.BOOKED.value: (
                "booked_at",
                "Поле booked_at обязательно при статусе BOOKED",
            ),
            Statuses.INSPECTING.value: (
                "inspection_started_at",
                "Поле inspection_started_at обязательно при статусе INSPECTING",
            ),
            Statuses.ACTIVE.value: (
                "start_time",
                "Поле start_time обязательно при статусе ACTIVE",
            ),
            Statuses.COMPLETED.value: (
                "end_time",
                "Поле end_time обязательно при статусе COMPLETED",
            ),
        }
        if self.status in constraints:
            field, message = constraints[self.status]
            if not getattr(self, field):
                raise ValidationError({field: message})

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="rental_booked_has_booked_at",
                condition=~Q(status=Statuses.BOOKED.value) | Q(booked_at__isnull=False),
            ),
            models.CheckConstraint(
                name="rental_inspecting_has_inspection_started_at",
                condition=~Q(status=Statuses.INSPECTING.value)
                | Q(inspection_started_at__isnull=False),
            ),
            models.CheckConstraint(
                name="rental_active_has_start_time",
                condition=~Q(status=Statuses.ACTIVE.value)
                | Q(start_time__isnull=False),
            ),
            models.CheckConstraint(
                name="rental_completed_has_end_time",
                condition=~Q(status=Statuses.COMPLETED.value)
                | Q(end_time__isnull=False),
            ),
        ]

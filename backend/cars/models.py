import enum

from django.db import models
from django.utils import timezone
from django.db.models import Q
from users.models import User
from django.core.exceptions import ValidationError
from django.db.models import F
from decimal import Decimal

import logging

logger = logging.getLogger(__name__)


class Car(models.Model):
    brand = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.IntegerField()
    license_plate = models.CharField(max_length=10, unique=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    fuel_level = models.IntegerField(default=100)
    odometer_reading = models.IntegerField(default=0)
    price_per_minute = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal(5.0))
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

    def get_button_text(self) -> str:
        button_texts = {
            Statuses.BOOKED.value: "Начать осмотр",
            Statuses.INSPECTING.value: "Начать аренду",
            Statuses.ACTIVE.value: "Окончить аренду",
            Statuses.COMPLETED.value: "Вернуться к списку автомобилей",
            Statuses.CANCELED.value: "Вернуться к списку автомобилей",
        }
        return button_texts.get(self.status, "")

    def clean(self) -> None:
        # Для создаия или изменения состояния Rental автомобиль обязан быть активным.
        if not self.car.active:
            raise ValidationError(
                {"car": "Автомобиль котовый вы хотите арендовать неактивен"}
            )

        # нельзя изменять статус без проставления соответствующей ему временной отметки
        status_constraints = {
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
        if self.status in status_constraints:
            field, message = status_constraints[self.status]
            # Если у выставленного аттрибута статуса нет соответствующему ему timestamp - вызываем ValidationError
            logger.warning(
                "Rental №%s: %s",
                self.pk,
                message,
            )
            if not getattr(self, field):
                raise ValidationError({field: message})

        # timestamps обязаны идти друг за другом по логике аренды.
        # Бронь -> Начало осмотра -> Начало аренды -> Окончание аренды
        timestamps_order = [
            ("booked_at", "inspection_started_at"),
            ("booked_at", "start_time"),
            ("booked_at", "end_time"),
            
            ("inspection_started_at", "start_time"),
            ("inspection_started_at", "end_time"),
            
            ("start_time", "end_time"),
        ]
        for earlier_ts, later_ts in timestamps_order:
            t1, t2 = getattr(self, earlier_ts), getattr(self, later_ts)
            logger.warning(
                "Rental №%s: %s (%s) раньше %s (%s)",
                self.pk,
                later_ts,
                t1,
                earlier_ts,
                t2,
            )
            if t1 and t2 and t2 < t1:
                raise ValidationError(
                    {later_ts: f"{later_ts} должен быть позже чем {earlier_ts}"}
                )

    def validate_unique(self, exclude=None) -> None:
        super().validate_unique(exclude)
        active_statuses = [
            Statuses.BOOKED.value,
            Statuses.INSPECTING.value,
            Statuses.ACTIVE.value,
        ]
        if self.status in active_statuses:
            qs = Rental.objects.filter(car=self.car, status__in=active_statuses)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({"car": "На эту машину уже есть активная аренда"})

    def _calculate_total_cost(self) -> None:
        """
        Внутренний метод который расчитывает и/или выставляет
        в аренде общую стоимость. Его сследует вызывать
        При окончании аренды и выставлении статуса
        Statuses.COMPLETED.value и start_time, end_time
        """
        if self.status not in (Statuses.ACTIVE.value, Statuses.COMPLETED.value):
            return
        if self.total_cost is not None:
            return
        if self.start_time is None:
            return
        last_timestamp = self.end_time if self.end_time else timezone.now()
        duration_minutes = Decimal(
            (last_timestamp - self.start_time).total_seconds() / 60
        )
        self.total_cost = self.car.price_per_minute * duration_minutes
        
        
    def save(self, *args, **kwargs) -> None:
        """
        Стандартный метод сохранения Rental, но здесь может быть
        обращение к БД для получения данных о car в случае если мы не указали
        total_cost в логике своей программы. Если
        вы работаете с множеством машин и аренд для них - следует
        рассмотреть
        Rental.objects.select_relater('car')...
        для избежания множественных запросов и проблемы N + 1
        """
        is_new = self.pk is None
        self.full_clean()

        self._calculate_total_cost()

        super().save(*args, **kwargs)
        if is_new:
            logger.info(
                "Rental #%s создана: car=%s user=%s", self.pk, self.car_id, self.user_id
            )

    class Meta:
        # Нельзя менять статус аренды без выставления соответствующего статусу временного штампа
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
            # Время бронирования должно быть меньше времени начала осмотра, начала и окончания аренд
            models.CheckConstraint(
                name="inspection_started_at_later_than_booked_at",
                condition=Q(booked_at__isnull=True)
                | Q(inspection_started_at__isnull=True)
                | Q(booked_at__lt=F("inspection_started_at")),
            ),
            models.CheckConstraint(
                name="start_time_later_than_booked_at",
                condition=Q(booked_at__isnull=True)
                | Q(start_time__isnull=True)
                | Q(booked_at__lt=F("start_time")),
            ),
            models.CheckConstraint(
                name="end_time_later_than_booked_at",
                condition=Q(booked_at__isnull=True)
                | Q(end_time__isnull=True)
                | Q(booked_at__lt=F("end_time")),
            ),
            
            # Время начала осмотра должно быть меньше времени начала и окончания аренд
            models.CheckConstraint(
                name="start_time_later_than_inspection_started_at",
                condition=Q(inspection_started_at__isnull=True)
                | Q(start_time__isnull=True)
                | Q(inspection_started_at__lt=F("start_time")),
            ),
            models.CheckConstraint(
                name="end_time_later_than_inspection_started_at",
                condition=Q(inspection_started_at__isnull=True)
                | Q(end_time__isnull=True)
                | Q(inspection_started_at__lt=F("end_time")),
            ),
            # Время начала аренды должно быть меньше времени окончания аренды
            models.CheckConstraint(
                name="end_time_later_than_start_time",
                condition=Q(start_time__isnull=True)
                | Q(end_time__isnull=True)
                | Q(start_time__lt=F("end_time")),
            ),
            # Уникальность: одна активная аренда на машину
            models.UniqueConstraint(
                name="one_active_rental_per_car",
                fields=["car"],
                condition=Q(
                    status__in=[
                        Statuses.BOOKED.value,
                        Statuses.INSPECTING.value,
                        Statuses.ACTIVE.value,
                    ]
                ),
            ),
            # total_cost должен быть заполнен только при COMPLETED
            # models.CheckConstraint(
            #     name="total_cost_only_when_completed",
            #     condition=~Q(status=Statuses.COMPLETED.value)
            #     | Q(total_cost__isnull=False),
            # ),
        ]

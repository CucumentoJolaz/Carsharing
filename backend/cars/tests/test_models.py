# rentals/tests.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from cars.models import Car, Rental, Statuses
from users.models import User
import logging

logging.disable(logging.CRITICAL)

class RentalTestBase(TestCase):
    """Общий setUp — создаём пользователя, машину и базовую аренду"""

    def setUp(self):
        self.now = timezone.now()

        self.user = User.objects.create_user(
            username="testuser",
            password="password123",
        )
        self.car = Car.objects.create(
            brand="Toyota",
            model="Camry",
            year=2022,
            license_plate="A123BC",
            latitude=55.756464,
            longitude=37.664646,
        )
        # Минимально валидная аренда, не сохранена в БД
        self.rental = Rental(
            car=self.car,
            user=self.user,
            status=Statuses.BOOKED.value,
            booked_at=self.now,
        )


# ========================================================== #
# Проверки статусных полей                                   #
# ========================================================== #

class TestStatusFieldConstraints(RentalTestBase):

    def test_booked_without_booked_at_fails(self):
        """BOOKED без booked_at — ошибка"""
        self.rental.booked_at = None
        with self.assertRaises(ValidationError) as ctx:
            self.rental.full_clean()
        self.assertIn("booked_at", ctx.exception.message_dict)

    def test_inspecting_without_inspection_started_at_fails(self):
        """INSPECTING без inspection_started_at — ошибка"""
        self.rental.status = Statuses.INSPECTING.value
        self.rental.inspection_started_at = None
        with self.assertRaises(ValidationError) as ctx:
            self.rental.full_clean()
        self.assertIn("inspection_started_at", ctx.exception.message_dict)

    def test_active_without_start_time_fails(self):
        """ACTIVE без start_time — ошибка"""
        self.rental.status = Statuses.ACTIVE.value
        self.rental.inspection_started_at = self.now + timedelta(minutes=1)
        self.rental.start_time = None
        with self.assertRaises(ValidationError) as ctx:
            self.rental.full_clean()
        self.assertIn("start_time", ctx.exception.message_dict)

    def test_completed_without_end_time_fails(self):
        """COMPLETED без end_time — ошибка"""
        self.rental.status = Statuses.COMPLETED.value
        self.rental.inspection_started_at = self.now + timedelta(minutes=1)
        self.rental.start_time = self.now + timedelta(minutes=2)
        self.rental.end_time = None
        with self.assertRaises(ValidationError) as ctx:
            self.rental.full_clean()
        self.assertIn("end_time", ctx.exception.message_dict)

    def test_canceled_passes_without_timestamps(self):
        """CANCELED не требует timestamp кроме booked — ок"""
        self.rental.status = Statuses.CANCELED.value
        self.rental.full_clean()  # не должно кидать исключение


# ========================================================== #
# Проверки порядка времён
# ========================================================== #

class TestTimeOrderConstraints(RentalTestBase):

    def test_inspection_before_booked_fails(self):
        """inspection_started_at раньше booked_at — ошибка"""
        self.rental.inspection_started_at = self.now - timedelta(minutes=1)
        with self.assertRaises(ValidationError) as ctx:
            self.rental.full_clean()
        self.assertIn("inspection_started_at", ctx.exception.message_dict)

    def test_start_before_inspection_fails(self):
        """start_time раньше inspection_started_at — ошибка"""
        self.rental.inspection_started_at = self.now + timedelta(minutes=2)
        self.rental.start_time = self.now + timedelta(minutes=1)
        with self.assertRaises(ValidationError) as ctx:
            self.rental.full_clean()
        self.assertIn("start_time", ctx.exception.message_dict)

    def test_end_before_start_fails(self):
        """end_time раньше start_time — ошибка"""
        self.rental.inspection_started_at = self.now + timedelta(minutes=1)
        self.rental.start_time = self.now + timedelta(minutes=2)
        self.rental.end_time = self.now + timedelta(minutes=1)
        with self.assertRaises(ValidationError) as ctx:
            self.rental.full_clean()
        self.assertIn("end_time", ctx.exception.message_dict)

    def test_correct_time_order_passes(self):
        """Правильный порядок времён — ок"""
        self.rental.status = Statuses.COMPLETED.value
        self.rental.inspection_started_at = self.now + timedelta(minutes=1)
        self.rental.start_time = self.now + timedelta(minutes=2)
        self.rental.end_time = self.now + timedelta(minutes=60)
        self.rental.full_clean()  # не должно кидать исключение


# ========================================================== #
# Проверки уникальности — одна активная аренда на машину
# ========================================================== #

class TestUniqueActiveRental(RentalTestBase):

    def test_second_active_rental_same_car_fails(self):
        """Нельзя создать вторую активную аренду на ту же машину"""
        # Сохраняем первую аренду
        self.rental.save()

        # Пытаемся создать вторую
        second_rental = Rental(
            car=self.car,
            user=self.user,
            status=Statuses.BOOKED.value,
            booked_at=self.now,
        )
        with self.assertRaises(ValidationError) as ctx:
            second_rental.full_clean()
        self.assertIn("car", ctx.exception.message_dict)

    def test_second_rental_after_completed_passes(self):
        """Новая аренда на машину с завершённой арендой — ок"""
        self.rental.status = Statuses.COMPLETED.value
        self.rental.inspection_started_at = self.now + timedelta(minutes=1)
        self.rental.start_time = self.now + timedelta(minutes=2)
        self.rental.end_time = self.now + timedelta(minutes=60)
        self.rental.save()

        second_rental = Rental(
            car=self.car,
            user=self.user,
            status=Statuses.BOOKED.value,
            booked_at=self.now,
        )
        second_rental.full_clean()  # должно пройти

    def test_editing_own_rental_does_not_conflict(self):
        """Редактирование своей же аренды не вызывает конфликт"""
        self.rental.save()
        # Меняем поле и сохраняем тот же объект
        self.rental.booked_at = self.now + timedelta(seconds=10)
        self.rental.full_clean()  # не должно кидать исключение


# ========================================================== #
# Проверки кнопки
# ========================================================== #

class TestGetButtonText(RentalTestBase):

    def test_booked_button(self):
        self.rental.status = Statuses.BOOKED.value
        self.assertEqual(self.rental.get_button_text(), "Начать осмотр")

    def test_inspecting_button(self):
        self.rental.status = Statuses.INSPECTING.value
        self.assertEqual(self.rental.get_button_text(), "Начать аренду")

    def test_active_button(self):
        self.rental.status = Statuses.ACTIVE.value
        self.assertEqual(self.rental.get_button_text(), "Окончить аренду")

    def test_completed_button(self):
        self.rental.status = Statuses.COMPLETED.value
        self.assertEqual(self.rental.get_button_text(), "Вернуться к списку автомобилей")

    def test_canceled_button(self):
        self.rental.status = Statuses.CANCELED.value
        self.assertEqual(self.rental.get_button_text(), "Вернуться к списку автомобилей")
        

# ========================================================== #
# Тесты расчёта общей стоимости поездки
# ========================================================== #

class TestCalculateTotalCost(RentalTestBase):

    def _make_completed_rental(self, minutes: int = 60) -> Rental:
        """Хелпер — возвращает несохранённую аренду в статусе COMPLETED"""
        self.rental.status = Statuses.COMPLETED.value
        self.rental.inspection_started_at = self.now + timedelta(minutes=1)
        self.rental.start_time = self.now + timedelta(minutes=2)
        self.rental.end_time = self.now + timedelta(minutes=2 + minutes)
        return self.rental

    def test_total_cost_calculated_on_complete(self):
        """total_cost считается автоматически при статусе COMPLETED"""
        rental = self._make_completed_rental(minutes=60)
        rental.save()
        # 60 минут * 5 руб/мин = 300
        self.assertEqual(rental.total_cost, Decimal("300.00"))

    def test_total_cost_not_overwritten_if_set(self):
        """Если total_cost уже установлен — не пересчитывается"""
        rental = self._make_completed_rental(minutes=60)
        rental.total_cost = Decimal("999.00")
        rental.save()
        self.assertEqual(rental.total_cost, Decimal("999.00"))

    def test_total_cost_not_calculated_for_active_status(self):
        """Для статуса ACTIVE total_cost считается, но относительно настоящего времени"""
        self.rental.status = Statuses.ACTIVE.value
        self.rental.inspection_started_at = self.now + timedelta(minutes=1)
        self.rental.start_time = self.now + timedelta(minutes=2)
        self.rental._calculate_total_cost()
        self.assertIsNotNone(self.rental.total_cost)

    def test_total_cost_precision(self):
        """Проверка точности при нецелом количестве минут"""
        rental = self._make_completed_rental(minutes=0)
        # 90 секунд = 1.5 минуты
        rental.end_time = rental.start_time + timedelta(seconds=90)
        rental.save()
        # 1.5 * 5 = 7.50
        self.assertEqual(rental.total_cost, Decimal("7.50"))

    def test_total_cost_not_calculated_without_start_time(self):
        """Без start_time total_cost не считается (clean поймает раньше)"""
        self.rental.status = Statuses.COMPLETED.value
        self.rental.start_time = None
        self.rental.end_time = self.now + timedelta(minutes=60)
        self.rental._calculate_total_cost()
        self.assertIsNone(self.rental.total_cost)
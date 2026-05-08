from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
import json

from .models import Car, Rental, Statuses

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(username='testuser', password='testpass123'):
    return User.objects.create_user(username=username, password=password)


def make_car(active=True, **kwargs):
    return Car.objects.create(active=active, **kwargs)


def make_rental(user, car, rental_status=Statuses.BOOKED.value, **kwargs):
    return Rental.objects.create(user=user, car=car, status=rental_status, **kwargs)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class RentalViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.other_user = make_user(username='otheruser')
        self.car = make_car(**{'brand': 'Hyundai',
                               'model': 'Solaris',
                               'year': 2023,
                               'license_plate': 'B023BB',
                               'latitude': 55.7512,
                               'longitude': 37.6185,
                               'odometer_reading': 15000,
                               'city': 'Москва', })

    def _auth(self, user=None):
        self.client.force_authenticate(user=user or self.user)

    def _url_list(self, car_pk):
        return f'/api/v1/cars/{car_pk}/rentals/'

    def _url_detail(self, car_pk, rental_pk):
        return f'/api/v1/cars/{car_pk}/rentals/{rental_pk}/'

    def _url_action(self, car_pk, rental_pk, action):
        return f'/api/v1/cars/{car_pk}/rentals/{rental_pk}/{action}/'


# ---------------------------------------------------------------------------
# Авторизация
# ---------------------------------------------------------------------------

class AuthenticationTests(RentalViewSetTestCase):

    def test_create_rental_requires_auth(self):
        """Неавторизованный запрос на создание аренды возвращает 401."""
        response = self.client.post(self._url_list(self.car.pk), {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_start_inspection_requires_auth(self):
        """Неавторизованный запрос на начало осмотра возвращает 401."""
        rental = make_rental(self.user, self.car)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-inspection'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_start_rental_requires_auth(self):
        rental = make_rental(self.user, self.car, rental_status=Statuses.INSPECTING.value)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-rental'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_end_rental_requires_auth(self):
        rental = make_rental(self.user, self.car, rental_status=Statuses.ACTIVE.value)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'end-rental'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# create — POST /cars/{car_pk}/rentals/
# ---------------------------------------------------------------------------

class CreateRentalTests(RentalViewSetTestCase):

    def test_create_rental_happy_path(self):
        """Создание аренды возвращает 201, нужные поля и статус BOOKED."""
        self._auth()
        response = self.client.post(self._url_list(self.car.pk), {})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()['data']
        self.assertEqual(data['status'], Statuses.BOOKED.value)
        self.assertIn('rental_id', data)
        self.assertIn('car_id', data)
        self.assertIn('new_button_text', data)

    def test_create_rental_creates_db_object(self):
        """После создания аренды объект появляется в базе."""
        self._auth()
        self.client.post(self._url_list(self.car.pk), {})
        self.assertEqual(Rental.objects.filter(user=self.user, car=self.car).count(), 1)

    def test_create_rental_car_not_found(self):
        """Запрос с несуществующим car_pk возвращает 404."""
        self._auth()
        response = self.client.post(self._url_list(99999), {})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_rental_inactive_car(self):
        """Бронирование неактивного автомобиля возвращает 404."""
        self._auth()
        inactive_car = make_car(active=False, **{'brand': 'Hyundai',
                                                 'model': 'Solaris',
                                                 'year': 2023,
                                                 'license_plate': 'B002BB',
                                                 'latitude': 55.7512,
                                                 'longitude': 37.6185,
                                                 'odometer_reading': 15000,
                                                 'city': 'Москва', })
        response = self.client.post(self._url_list(inactive_car.pk), {})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_rental_button_text_is_start_inspection(self):
        """Текст кнопки после бронирования — 'Начать осмотр'."""
        self._auth()
        response = self.client.post(self._url_list(self.car.pk), {})
        self.assertEqual(response.json()['data']['new_button_text'], 'Начать осмотр')


# ---------------------------------------------------------------------------
# start-inspection — POST /cars/{car_pk}/rentals/{pk}/start-inspection/
# ---------------------------------------------------------------------------

class StartInspectionTests(RentalViewSetTestCase):

    def test_start_inspection_happy_path(self):
        """Переход BOOKED → INSPECTING возвращает 200 и новый статус."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.BOOKED.value)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-inspection'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()['data']
        self.assertEqual(data['status'], Statuses.INSPECTING.value)
        self.assertIn('new_button_text', data)

    def test_start_inspection_updates_db(self):
        """После перехода статус в базе обновляется на INSPECTING."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.BOOKED.value)
        self.client.post(self._url_action(self.car.pk, rental.pk, 'start-inspection'))
        rental.refresh_from_db()
        self.assertEqual(rental.status, Statuses.INSPECTING.value)
        self.assertIsNotNone(rental.inspection_started_at)

    def test_start_inspection_button_text(self):
        """Текст кнопки после начала осмотра — 'Начать аренду'."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.BOOKED.value)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-inspection'))
        self.assertEqual(response.json()['data']['new_button_text'], 'Начать аренду')

    def test_start_inspection_wrong_status_returns_409(self):
        """Попытка начать осмотр у не-BOOKED аренды возвращает 409."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.ACTIVE.value)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-inspection'))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_start_inspection_409_content_type(self):
        """409 возвращается с content-type application/problem+json."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.ACTIVE.value)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-inspection'))
        self.assertIn('application/problem+json', response.get('Content-Type', ''))

    def test_start_inspection_409_contains_current_status(self):
        """Тело 409 содержит текущий статус аренды."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.ACTIVE.value)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-inspection'))
        self.assertIn(Statuses.ACTIVE.value, response.json()['detail'])

    def test_start_inspection_rental_not_found(self):
        """Несуществующий rental_pk возвращает 404."""
        self._auth()
        response = self.client.post(self._url_action(self.car.pk, 99999, 'start-inspection'))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_start_inspection_idempotency(self):
        """Повторный вызов start-inspection на INSPECTING возвращает 409, не INSPECTING дважды."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.BOOKED.value)
        self.client.post(self._url_action(self.car.pk, rental.pk, 'start-inspection'))
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-inspection'))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)


# ---------------------------------------------------------------------------
# start-rental — POST /cars/{car_pk}/rentals/{pk}/start-rental/
# ---------------------------------------------------------------------------

class StartRentalTests(RentalViewSetTestCase):

    def test_start_rental_happy_path(self):
        """Переход INSPECTING → ACTIVE возвращает 200 и статус ACTIVE."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.INSPECTING.value)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-rental'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['data']['status'], Statuses.ACTIVE.value)

    def test_start_rental_updates_db(self):
        """После перехода start_time заполнен и статус ACTIVE в базе."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.INSPECTING.value)
        self.client.post(self._url_action(self.car.pk, rental.pk, 'start-rental'))
        rental.refresh_from_db()
        self.assertEqual(rental.status, Statuses.ACTIVE.value)
        self.assertIsNotNone(rental.start_time)

    def test_start_rental_button_text(self):
        """Текст кнопки после начала аренды — 'Окончить аренду'."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.INSPECTING.value)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-rental'))
        self.assertEqual(response.json()['data']['new_button_text'], 'Окончить аренду')

    def test_start_rental_wrong_status_returns_409(self):
        """Попытка начать аренду у BOOKED (не INSPECTING) возвращает 409."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.BOOKED.value)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-rental'))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_start_rental_rental_not_found(self):
        self._auth()
        response = self.client.post(self._url_action(self.car.pk, 99999, 'start-rental'))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# end-rental — POST /cars/{car_pk}/rentals/{pk}/end-rental/
# ---------------------------------------------------------------------------

class EndRentalTests(RentalViewSetTestCase):

    def test_end_rental_happy_path(self):
        """Переход ACTIVE → COMPLETED возвращает 200 и статус COMPLETED."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.ACTIVE.value)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'end-rental'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['data']['status'], Statuses.COMPLETED.value)

    def test_end_rental_updates_db(self):
        """После завершения end_time заполнен и статус COMPLETED в базе."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.ACTIVE.value)
        self.client.post(self._url_action(self.car.pk, rental.pk, 'end-rental'))
        rental.refresh_from_db()
        self.assertEqual(rental.status, Statuses.COMPLETED.value)
        self.assertIsNotNone(rental.end_time)

    def test_end_rental_response_contains_started_and_ended_at(self):
        """Ответ содержит и started_at и ended_at."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.ACTIVE.value)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'end-rental'))
        data = response.json()['data']
        self.assertIn('started_at', data)
        self.assertIn('ended_at', data)

    def test_end_rental_button_text(self):
        """Текст кнопки после завершения — 'Вернуться к списку автомобилей'."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.ACTIVE.value)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'end-rental'))
        self.assertEqual(response.json()['data']['new_button_text'], 'Вернуться к списку автомобилей')

    def test_end_rental_wrong_status_returns_409(self):
        """Попытка завершить BOOKED аренду возвращает 409."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.BOOKED.value)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'end-rental'))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_end_rental_rental_not_found(self):
        self._auth()
        response = self.client.post(self._url_action(self.car.pk, 99999, 'end-rental'))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_end_rental_idempotency(self):
        """Повторный вызов end-rental на COMPLETED возвращает 409."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.ACTIVE.value)
        self.client.post(self._url_action(self.car.pk, rental.pk, 'end-rental'))
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'end-rental'))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)


# ---------------------------------------------------------------------------
# Полный жизненный цикл (интеграционный)
# ---------------------------------------------------------------------------

class FullLifecycleTests(RentalViewSetTestCase):

    def test_full_lifecycle(self):
        """
        Полный happy-path: BOOKED → INSPECTING → ACTIVE → COMPLETED.
        Проверяет статусы на каждом шаге и финальное состояние в базе.
        """
        self._auth()

        # 1. Создать аренду
        r = self.client.post(self._url_list(self.car.pk), {})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        rental_id = r.json()['data']['rental_id']

        # 2. Начать осмотр
        r = self.client.post(self._url_action(self.car.pk, rental_id, 'start-inspection'))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.json()['data']['status'], Statuses.INSPECTING.value)

        # 3. Начать аренду
        r = self.client.post(self._url_action(self.car.pk, rental_id, 'start-rental'))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.json()['data']['status'], Statuses.ACTIVE.value)

        # 4. Завершить аренду
        r = self.client.post(self._url_action(self.car.pk, rental_id, 'end-rental'))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.json()['data']['status'], Statuses.COMPLETED.value)

        # Проверить базу
        rental = Rental.objects.get(pk=rental_id)
        self.assertEqual(rental.status, Statuses.COMPLETED.value)
        self.assertIsNotNone(rental.inspection_started_at)
        self.assertIsNotNone(rental.start_time)
        self.assertIsNotNone(rental.end_time)

    def test_skip_inspection_is_rejected(self):
        """Нельзя перейти из BOOKED сразу в ACTIVE, минуя INSPECTING."""
        self._auth()
        r = self.client.post(self._url_list(self.car.pk), {})
        rental_id = r.json()['data']['rental_id']

        r = self.client.post(self._url_action(self.car.pk, rental_id, 'start-rental'))
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
import logging

from .models import Car, Rental, Statuses

User = get_user_model()
logger = logging.getLogger(__name__)


# ========================================================== #
#  Helpers                                                    #
# ========================================================== #

def make_user(username: str = 'testuser', password: str = 'testpass123') -> User:
    return User.objects.create_user(username=username, password=password)


def make_car(active: bool = True, **kwargs) -> Car:
    defaults = {
        'brand': 'Hyundai',
        'model': 'Solaris',
        'year': 2023,
        'license_plate': 'B023BB',
        'latitude': 55.7512,
        'longitude': 37.6185,
        'odometer_reading': 15000,
        'city': 'Москва',
    }
    defaults.update(kwargs)
    return Car.objects.create(active=active, **defaults)


def make_rental(user: User, car: Car, rental_status: str = Statuses.BOOKED.value, **kwargs) -> Rental:
    return Rental.objects.create(user=user, car=car, status=rental_status, **kwargs)


# ========================================================== #
#  Base                                                       #
# ========================================================== #

class RentalViewSetTestCase(TestCase):
    """
    Базовый класс тестов. Создаёт пользователя и автомобиль,
    предоставляет хелперы для авторизации и построения URL.
    """

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = make_user()
        self.other_user = make_user(username='otheruser')
        self.car = make_car()
        logger.debug(
            "setUp | user=%s other_user=%s car_id=%s",
            self.user, self.other_user, self.car.pk,
        )

    def _auth(self, user: User | None = None) -> None:
        """Авторизует клиент под указанным пользователем (по умолчанию self.user)."""
        target = user or self.user
        self.client.force_authenticate(user=target)
        logger.debug("Клиент авторизован | user=%s", target)

    def _url_list(self, car_pk: int) -> str:
        return f'/api/v1/cars/{car_pk}/rentals/'

    def _url_detail(self, car_pk: int, rental_pk: int) -> str:
        return f'/api/v1/cars/{car_pk}/rentals/{rental_pk}/'

    def _url_action(self, car_pk: int, rental_pk: int, action: str) -> str:
        return f'/api/v1/cars/{car_pk}/rentals/{rental_pk}/{action}/'


# ========================================================== #
#  Авторизация                                               #
# ========================================================== #

class AuthenticationTests(RentalViewSetTestCase):

    def test_create_rental_requires_auth(self) -> None:
        """Неавторизованный POST на создание аренды возвращает 403."""
        logger.debug("test_create_rental_requires_auth | car_pk=%s", self.car.pk)
        response = self.client.post(self._url_list(self.car.pk), {})
        logger.debug("Ответ | status=%s", response.status_code)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_start_inspection_requires_auth(self) -> None:
        """Неавторизованный POST на начало осмотра возвращает 403."""
        rental = make_rental(self.user, self.car)
        logger.debug("test_start_inspection_requires_auth | rental_id=%s", rental.pk)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-inspection'))
        logger.debug("Ответ | status=%s", response.status_code)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_start_rental_requires_auth(self) -> None:
        """Неавторизованный POST на начало аренды возвращает 403."""
        rental = make_rental(self.user, self.car, rental_status=Statuses.INSPECTING.value)
        logger.debug("test_start_rental_requires_auth | rental_id=%s", rental.pk)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-rental'))
        logger.debug("Ответ | status=%s", response.status_code)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_end_rental_requires_auth(self) -> None:
        """Неавторизованный POST на завершение аренды возвращает 403."""
        rental = make_rental(self.user, self.car, rental_status=Statuses.ACTIVE.value)
        logger.debug("test_end_rental_requires_auth | rental_id=%s", rental.pk)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'end-rental'))
        logger.debug("Ответ | status=%s", response.status_code)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ========================================================== #
#  create — POST /cars/{car_pk}/rentals/                     #
# ========================================================== #

class CreateRentalTests(RentalViewSetTestCase):

    def test_create_rental_happy_path(self) -> None:
        """Создание аренды возвращает 201, нужные поля и статус BOOKED."""
        self._auth()
        logger.debug("test_create_rental_happy_path | car_pk=%s user=%s", self.car.pk, self.user)
        response = self.client.post(self._url_list(self.car.pk), {})
        logger.debug("Ответ | status=%s body=%s", response.status_code, response.json())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()['data']
        self.assertEqual(data['status'], Statuses.BOOKED.value)
        self.assertIn('rental_id', data)
        self.assertIn('car_id', data)
        self.assertIn('new_button_text', data)

    def test_create_rental_creates_db_object(self) -> None:
        """После создания аренды объект появляется в базе."""
        self._auth()
        logger.debug("test_create_rental_creates_db_object | car_pk=%s", self.car.pk)
        self.client.post(self._url_list(self.car.pk), {})
        count = Rental.objects.filter(user=self.user, car=self.car).count()
        logger.debug("Аренд в базе | count=%s", count)
        self.assertEqual(count, 1)

    def test_create_rental_car_not_found(self) -> None:
        """Запрос с несуществующим car_pk возвращает 404."""
        self._auth()
        logger.debug("test_create_rental_car_not_found | car_pk=99999")
        response = self.client.post(self._url_list(99999), {})
        logger.debug("Ответ | status=%s", response.status_code)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_rental_inactive_car(self) -> None:
        """Запрос аренды неактивного автомобиля возвращает 404."""
        self._auth()
        # license_plate уникален — передаём отдельный, чтобы не конфликтовать с self.car
        inactive_car = make_car(active=False, license_plate='X999XX')
        logger.debug("test_create_rental_inactive_car | car_pk=%s active=False", inactive_car.pk)
        response = self.client.post(self._url_list(inactive_car.pk), {})
        logger.debug("Ответ | status=%s", response.status_code)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_rental_button_text_is_start_inspection(self) -> None:
        """Текст кнопки после бронирования — 'Начать осмотр'."""
        self._auth()
        response = self.client.post(self._url_list(self.car.pk), {})
        button_text = response.json()['data']['new_button_text']
        logger.debug("test_create_rental_button_text | button_text=%s", button_text)
        self.assertEqual(button_text, 'Начать осмотр')

    def test_create_rental_conflict_if_active_rental_exists(self) -> None:
        """Если у пользователя есть активная аренда, повторный POST возвращает 409."""
        self._auth()
        existing = make_rental(self.user, self.car, rental_status=Statuses.ACTIVE.value, start_time=timezone.now())
        logger.debug(
            "test_create_rental_conflict | existing_rental_id=%s status=%s",
            existing.pk, existing.status,
        )
        # Нужен второй автомобиль, чтобы запрос дошёл до проверки активных аренд
        second_car = make_car(license_plate='C001CC')
        response = self.client.post(self._url_list(second_car.pk), {})
        logger.debug("Ответ | status=%s body=%s", response.status_code, response.json())
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('application/problem+json', response.get('Content-Type', ''))

    def test_create_rental_conflict_body_contains_existing_rental_id(self) -> None:
        """Тело 409 содержит ID существующей активной аренды."""
        self._auth()
        existing = make_rental(self.user, self.car, rental_status=Statuses.BOOKED.value, booked_at=timezone.now())
        second_car = make_car(license_plate='C002CC')
        response = self.client.post(self._url_list(second_car.pk), {})
        logger.debug(
            "test_create_rental_conflict_body | existing_rental_id=%s detail=%s",
            existing.pk, response.json().get('detail'),
        )
        self.assertIn(str(existing.id), response.json()['detail'])


# ========================================================== #
#  start-inspection                                          #
# ========================================================== #

class StartInspectionTests(RentalViewSetTestCase):

    def test_start_inspection_happy_path(self) -> None:
        """Переход BOOKED → INSPECTING возвращает 200 и новый статус."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.BOOKED.value)
        logger.debug("test_start_inspection_happy_path | rental_id=%s", rental.pk)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-inspection'))
        logger.debug("Ответ | status=%s body=%s", response.status_code, response.json())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()['data']
        self.assertEqual(data['status'], Statuses.INSPECTING.value)
        self.assertIn('new_button_text', data)

    def test_start_inspection_updates_db(self) -> None:
        """После перехода статус в базе — INSPECTING, inspection_started_at заполнен."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.BOOKED.value)
        self.client.post(self._url_action(self.car.pk, rental.pk, 'start-inspection'))
        rental.refresh_from_db()
        logger.debug(
            "test_start_inspection_updates_db | rental_id=%s status=%s inspection_started_at=%s",
            rental.pk, rental.status, rental.inspection_started_at,
        )
        self.assertEqual(rental.status, Statuses.INSPECTING.value)
        self.assertIsNotNone(rental.inspection_started_at)

    def test_start_inspection_button_text(self) -> None:
        """Текст кнопки после начала осмотра — 'Начать аренду'."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.BOOKED.value)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-inspection'))
        button_text = response.json()['data']['new_button_text']
        logger.debug("test_start_inspection_button_text | button_text=%s", button_text)
        self.assertEqual(button_text, 'Начать аренду')

    def test_start_inspection_wrong_status_returns_409(self) -> None:
        """Попытка начать осмотр у не-BOOKED аренды возвращает 409."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.ACTIVE.value, start_time=timezone.now())
        logger.debug(
            "test_start_inspection_wrong_status | rental_id=%s current_status=%s",
            rental.pk, rental.status,
        )
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-inspection'))
        logger.debug("Ответ | status=%s", response.status_code)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_start_inspection_409_content_type(self) -> None:
        """409 возвращается с content-type application/problem+json."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.ACTIVE.value)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-inspection'))
        logger.debug(
            "test_start_inspection_409_content_type | Content-Type=%s",
            response.get('Content-Type'),
        )
        self.assertIn('application/problem+json', response.get('Content-Type', ''))

    def test_start_inspection_409_contains_current_status(self) -> None:
        """Тело 409 содержит текущий статус аренды."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.ACTIVE.value)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-inspection'))
        detail = response.json()['detail']
        logger.debug("test_start_inspection_409_detail | detail=%s", detail)
        self.assertIn(Statuses.ACTIVE.value, detail)

    def test_start_inspection_rental_not_found(self) -> None:
        """Несуществующий rental_pk возвращает 404."""
        self._auth()
        logger.debug("test_start_inspection_rental_not_found | rental_pk=99999")
        response = self.client.post(self._url_action(self.car.pk, 99999, 'start-inspection'))
        logger.debug("Ответ | status=%s", response.status_code)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_start_inspection_idempotency(self) -> None:
        """Повторный вызов start-inspection на INSPECTING возвращает 409."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.BOOKED.value)
        self.client.post(self._url_action(self.car.pk, rental.pk, 'start-inspection'))
        logger.debug("test_start_inspection_idempotency | повторный вызов rental_id=%s", rental.pk)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-inspection'))
        logger.debug("Ответ | status=%s", response.status_code)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)


# ========================================================== #
#  start-rental                                              #
# ========================================================== #

class StartRentalTests(RentalViewSetTestCase):

    def test_start_rental_happy_path(self) -> None:
        """Переход INSPECTING → ACTIVE возвращает 200 и статус ACTIVE."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.INSPECTING.value)
        logger.debug("test_start_rental_happy_path | rental_id=%s", rental.pk)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-rental'))
        logger.debug("Ответ | status=%s body=%s", response.status_code, response.json())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['data']['status'], Statuses.ACTIVE.value)

    def test_start_rental_updates_db(self) -> None:
        """После перехода start_time заполнен и статус ACTIVE в базе."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.INSPECTING.value)
        self.client.post(self._url_action(self.car.pk, rental.pk, 'start-rental'))
        rental.refresh_from_db()
        logger.debug(
            "test_start_rental_updates_db | rental_id=%s status=%s start_time=%s",
            rental.pk, rental.status, rental.start_time,
        )
        self.assertEqual(rental.status, Statuses.ACTIVE.value)
        self.assertIsNotNone(rental.start_time)

    def test_start_rental_button_text(self) -> None:
        """Текст кнопки после начала аренды — 'Окончить аренду'."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.INSPECTING.value)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-rental'))
        button_text = response.json()['data']['new_button_text']
        logger.debug("test_start_rental_button_text | button_text=%s", button_text)
        self.assertEqual(button_text, 'Окончить аренду')

    def test_start_rental_wrong_status_returns_409(self) -> None:
        """Попытка начать аренду у BOOKED (не INSPECTING) возвращает 409."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.BOOKED.value)
        logger.debug(
            "test_start_rental_wrong_status | rental_id=%s current_status=%s",
            rental.pk, rental.status,
        )
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-rental'))
        logger.debug("Ответ | status=%s", response.status_code)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_start_rental_rental_not_found(self) -> None:
        """Несуществующий rental_pk возвращает 404."""
        self._auth()
        logger.debug("test_start_rental_rental_not_found | rental_pk=99999")
        response = self.client.post(self._url_action(self.car.pk, 99999, 'start-rental'))
        logger.debug("Ответ | status=%s", response.status_code)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_start_rental_409_content_type(self) -> None:
        """409 при неверном статусе возвращается с content-type application/problem+json."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.BOOKED.value)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-rental'))
        logger.debug(
            "test_start_rental_409_content_type | Content-Type=%s",
            response.get('Content-Type'),
        )
        self.assertIn('application/problem+json', response.get('Content-Type', ''))


# ========================================================== #
#  end-rental                                                #
# ========================================================== #

class EndRentalTests(RentalViewSetTestCase):

    def test_end_rental_happy_path(self) -> None:
        """Переход ACTIVE → COMPLETED возвращает 200 и статус COMPLETED."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.ACTIVE.value, start_time=timezone.now())
        logger.debug("test_end_rental_happy_path | rental_id=%s", rental.pk)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'end-rental'))
        logger.debug("Ответ | status=%s body=%s", response.status_code, response.json())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['data']['status'], Statuses.COMPLETED.value)

    def test_end_rental_updates_db(self) -> None:
        """После завершения end_time заполнен и статус COMPLETED в базе."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.ACTIVE.value, start_time=timezone.now())
        self.client.post(self._url_action(self.car.pk, rental.pk, 'end-rental'))
        rental.refresh_from_db()
        logger.debug(
            "test_end_rental_updates_db | rental_id=%s status=%s end_time=%s",
            rental.pk, rental.status, rental.end_time,
        )
        self.assertEqual(rental.status, Statuses.COMPLETED.value)
        self.assertIsNotNone(rental.end_time)

    def test_end_rental_response_contains_started_and_ended_at(self) -> None:
        """Ответ содержит и started_at и ended_at."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.ACTIVE.value, start_time=timezone.now())
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'end-rental'))
        data = response.json()['data']
        logger.debug("test_end_rental_timestamps | started_at=%s ended_at=%s",
                     data.get('started_at'), data.get('ended_at'))
        self.assertIn('started_at', data)
        self.assertIn('ended_at', data)

    def test_end_rental_button_text(self) -> None:
        """Текст кнопки после завершения — 'Вернуться к списку автомобилей'."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.ACTIVE.value, start_time=timezone.now())
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'end-rental'))
        button_text = response.json()['data']['new_button_text']
        logger.debug("test_end_rental_button_text | button_text=%s", button_text)
        self.assertEqual(button_text, 'Вернуться к списку автомобилей')

    def test_end_rental_wrong_status_returns_409(self) -> None:
        """Попытка завершить BOOKED аренду возвращает 409."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.BOOKED.value, booked_at=timezone.now())
        logger.debug(
            "test_end_rental_wrong_status | rental_id=%s current_status=%s",
            rental.pk, rental.status,
        )
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'end-rental'))
        logger.debug("Ответ | status=%s", response.status_code)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_end_rental_rental_not_found(self) -> None:
        """Несуществующий rental_pk возвращает 404."""
        self._auth()
        logger.debug("test_end_rental_rental_not_found | rental_pk=99999")
        response = self.client.post(self._url_action(self.car.pk, 99999, 'end-rental'))
        logger.debug("Ответ | status=%s", response.status_code)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_end_rental_idempotency(self) -> None:
        """Повторный вызов end-rental на COMPLETED возвращает 409."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.ACTIVE.value, start_time=timezone.now())
        self.client.post(self._url_action(self.car.pk, rental.pk, 'end-rental'))
        logger.debug("test_end_rental_idempotency | повторный вызов rental_id=%s", rental.pk)
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'end-rental'))
        logger.debug("Ответ | status=%s", response.status_code)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_end_rental_409_content_type(self) -> None:
        """409 при неверном статусе возвращается с content-type application/problem+json."""
        self._auth()
        rental = make_rental(self.user, self.car, rental_status=Statuses.BOOKED.value, booked_at=timezone.now())
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'end-rental'))
        logger.debug(
            "test_end_rental_409_content_type | Content-Type=%s",
            response.get('Content-Type'),
        )
        self.assertIn('application/problem+json', response.get('Content-Type', ''))


# ========================================================== #
#  Полный жизненный цикл (интеграционный)                    #
# ========================================================== #

class FullLifecycleTests(RentalViewSetTestCase):

    def test_full_lifecycle(self) -> None:
        """
        Happy-path: BOOKED → INSPECTING → ACTIVE → COMPLETED.
        Проверяет статусы на каждом шаге и финальное состояние в базе.
        """
        self._auth()
        logger.info("test_full_lifecycle start | user=%s car_id=%s", self.user, self.car.pk)

        # 1. Создать аренду
        r = self.client.post(self._url_list(self.car.pk), {})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        rental_id = r.json()['data']['rental_id']
        logger.debug("Шаг 1 BOOKED | rental_id=%s", rental_id)

        # 2. Начать осмотр
        r = self.client.post(self._url_action(self.car.pk, rental_id, 'start-inspection'))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.json()['data']['status'], Statuses.INSPECTING.value)
        logger.debug("Шаг 2 INSPECTING | rental_id=%s", rental_id)

        # 3. Начать аренду
        r = self.client.post(self._url_action(self.car.pk, rental_id, 'start-rental'))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.json()['data']['status'], Statuses.ACTIVE.value)
        logger.debug("Шаг 3 ACTIVE | rental_id=%s", rental_id)

        # 4. Завершить аренду
        r = self.client.post(self._url_action(self.car.pk, rental_id, 'end-rental'))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.json()['data']['status'], Statuses.COMPLETED.value)
        logger.debug("Шаг 4 COMPLETED | rental_id=%s", rental_id)

        rental = Rental.objects.get(pk=rental_id)
        logger.info(
            "test_full_lifecycle end | rental_id=%s status=%s "
            "inspection_started_at=%s start_time=%s end_time=%s",
            rental.pk, rental.status,
            rental.inspection_started_at, rental.start_time, rental.end_time,
        )
        self.assertEqual(rental.status, Statuses.COMPLETED.value)
        self.assertIsNotNone(rental.inspection_started_at)
        self.assertIsNotNone(rental.start_time)
        self.assertIsNotNone(rental.end_time)

    def test_skip_inspection_is_rejected(self) -> None:
        """Нельзя перейти из BOOKED сразу в ACTIVE, минуя INSPECTING."""
        self._auth()
        r = self.client.post(self._url_list(self.car.pk), {})
        rental_id = r.json()['data']['rental_id']
        logger.debug("test_skip_inspection_is_rejected | rental_id=%s", rental_id)
        r = self.client.post(self._url_action(self.car.pk, rental_id, 'start-rental'))
        logger.debug("Ответ | status=%s", r.status_code)
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)

    def test_other_user_cannot_transition_rental(self) -> None:
        """
        Другой пользователь не может управлять чужой арендой.
        Ожидаем 404 (аренда не принадлежит ему) или 403.
        """
        rental = make_rental(self.user, self.car, rental_status=Statuses.BOOKED.value, booked_at=timezone.now())
        self._auth(user=self.other_user)
        logger.debug(
            "test_other_user_cannot_transition | rental_id=%s owner=%s requester=%s",
            rental.pk, self.user, self.other_user,
        )
        response = self.client.post(self._url_action(self.car.pk, rental.pk, 'start-inspection'))
        logger.debug("Ответ | status=%s", response.status_code)
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
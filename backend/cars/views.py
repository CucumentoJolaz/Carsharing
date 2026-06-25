from rest_framework import permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from django.db import transaction
from .models import Car, Rental, Statuses
from .serializers import CarSerializer, RentalSerializer
from django.utils import timezone
from django.http import Http404
import logging

logger = logging.getLogger(__name__)


class CarViewSet(viewsets.ModelViewSet):
    """
    CRUD для модели Car.

    Возвращает только активные автомобили (active=True).
    Все эндпоинты требуют аутентификации.
    """
    queryset = Car.objects.filter(active=True)
    serializer_class = CarSerializer
    permission_classes = (permissions.IsAuthenticated,)


def _conflict_response(
    problem_type: str,
    title: str,
    detail: str,
    instance: str,
    http_status: int = status.HTTP_409_CONFLICT,
) -> Response:
    """
    Формирует ответ в формате application/problem+json (RFC 7807).

    Args:
        problem_type: Относительный URI, идентифицирующий тип ошибки.
        title:        Краткое человекочитаемое описание проблемы.
        detail:       Подробное описание конкретного случая.
        instance:     URI запроса, вызвавшего ошибку.
        http_status:  HTTP-статус ответа (по умолчанию 409).

    Returns:
        Response с content_type='application/problem+json'.
    """
    return Response(
        {
            'type': problem_type,
            'title': title,
            'status': http_status,
            'detail': detail,
            'instance': instance,
        },
        status=http_status,
        content_type='application/problem+json',
    )


class RentalViewSet(viewsets.ModelViewSet):
    """
    Управление арендами автомобилей.

    Реализует жизненный цикл аренды в виде конечного автомата:
        BOOKED → INSPECTING → ACTIVE → COMPLETED

    Переходы инициируются через отдельные эндпоинты:
        POST /api/v1/cars/{car_pk}/rentals/                        — создать бронь (BOOKED)
        POST /api/v1/cars/{car_pk}/rentals/{id}/start-inspection/  — начать осмотр (INSPECTING)
        POST /api/v1/cars/{car_pk}/rentals/{id}/start-rental/      — начать аренду (ACTIVE)
        POST /api/v1/cars/{car_pk}/rentals/{id}/end-rental/        — завершить аренду (COMPLETED)

    Дополнительные эндпоинты:
        GET /api/v1/cars/{car_pk}/rentals/  — список аренд для конкретного автомобиля

    При неверном статусе возвращает 409 Conflict (application/problem+json).
    get_object использует select_for_update() для защиты от гонок при
    одновременном изменении статуса.
    """
    serializer_class = RentalSerializer
    permission_classes = (permissions.IsAuthenticated,)

    # ==================================================================== #
    #  Базовые методы ViewSet                                              #
    # ==================================================================== #

    def get_object(self) -> Rental:
        """
        Возвращает объект Rental с блокировкой строки на уровне БД (SELECT FOR UPDATE).
        Вызывается внутри транзакции, чтобы блокировка была снята после коммита.

        Returns:
            Rental: Объект аренды с пессимистической блокировкой.

        Raises:
            Http404: Если аренда с указанным pk не найдена.
        """
        pk = self.kwargs['pk']
        try:
            rental = Rental.objects.select_for_update().get(pk=pk)
        except Rental.DoesNotExist:
            logger.warning(
                "Rental pk=%s не найден | user=%s",
                pk, self.request.user,
            )
            raise Http404()

        logger.debug(
            "Rental %s получен с блокировкой строки | user=%s",
            rental.id, self.request.user,
        )
        return rental

    def get_queryset(self):
        """
        Возвращает QuerySet аренд для автомобиля, указанного в URL (car_pk).

        Returns:
            QuerySet[Rental]: Аренды, привязанные к данному автомобилю.

        Raises:
            Http404: Если автомобиль не найден или неактивен.
        """
        car_pk = self.kwargs.get('car_pk')

        # car_pk всегда присутствует при вложенном роутинге,
        # но проверка оставлена как защита от прямых вызовов get_queryset()
        if not car_pk:
            logger.error(
                "get_queryset вызван без car_pk | user=%s path=%s",
                self.request.user, self.request.path,
            )
            return Rental.objects.none()

        car = get_object_or_404(Car, pk=car_pk)
        if not car.active:
            logger.warning(
                "Запрос аренд для неактивной машины | car_id=%s user=%s",
                car_pk, self.request.user,
            )
            raise Http404()

        return Rental.objects.filter(car_id=car_pk) 

    # ==================================================================== #
    #  Создание аренды                                                     #
    # ==================================================================== #

    @transaction.atomic
    def create(self, request, *args, **kwargs) -> Response:
        """
        Создать новую аренду (BOOKED) для конкретного автомобиля.

        Endpoint: POST /api/v1/cars/{car_pk}/rentals/

        Args:
            request: HTTP-запрос. Тело может содержать доп. поля аренды.

        Returns:
            Response 201: Аренда создана. Возвращает rental_id, car_id и статус.
            Response 400: Невалидные данные запроса.
            Response 404: Автомобиль не найден или неактивен.
            Response 409: У пользователя уже есть активная аренда.
        """
        active_statuses = [
            Statuses.BOOKED.value,
            Statuses.INSPECTING.value,
            Statuses.ACTIVE.value,
        ]
        existing_rental = Rental.objects.filter(
            user=request.user,
            status__in=active_statuses,
        ).first()

        if existing_rental:
            logger.warning(
                "Попытка создать аренду при наличии активной | user=%s existing_rental_id=%s status=%s",
                request.user, existing_rental.id, existing_rental.status,
            )
            return _conflict_response(
                problem_type='/problems/multiple-rentals',
                title='Существуют активные аренды у пользователя',
                detail=(
                    f'У вас уже есть активная аренда (ID: {existing_rental.id}, '
                    f'статус: {existing_rental.status}). '
                    f'Пожалуйста, обратитесь к администратору для решения проблемы.'
                ),
                instance=request.build_absolute_uri(),
            )

        car = get_object_or_404(Car, pk=self.kwargs.get('car_pk'))
        if not car.active:
            logger.warning(
                "Попытка аренды неактивной машины | car_id=%s user=%s",
                car.id, request.user,
            )
            raise Http404(f"Машина под номером {car.id} не является активной для аренды.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # исправлено: было raise_exception=False
        rental = serializer.save(car=car, user=request.user, status=Statuses.BOOKED.value)

        logger.info(
            "Аренда создана | rental_id=%s car_id=%s user=%s",
            rental.id, car.id, request.user,
        )
        return Response(
            {
                'status': status.HTTP_201_CREATED,
                'data': {
                    'rental_id': rental.id,
                    'car_id': car.id,
                    'started_at': rental.booked_at,
                    'status': Statuses.BOOKED.value,
                    'new_button_text': rental.get_button_text(),
                },
                'message': 'Аренда создана. Автомобиль успешно забронирован.',
            },
            status=status.HTTP_201_CREATED,
        )

    # ==================================================================== #
    #  Переходы состояний                                                  #
    # ==================================================================== #

    @action(detail=True, methods=['post'], url_path='start-inspection')
    @transaction.atomic
    def start_inspection(self, request, *args, **kwargs) -> Response:
        """
        Перевести аренду из статуса BOOKED → INSPECTING.

        Endpoint: POST /api/v1/cars/{car_pk}/rentals/{id}/start-inspection/

        Args:
            request: HTTP-запрос.

        Returns:
            Response 200: Осмотр начат. Возвращает rental_id, car_id, время начала и статус.
            Response 409: Аренда находится в статусе, отличном от BOOKED.
        """
        rental = self.get_object()

        if rental.status != Statuses.BOOKED.value:
            logger.warning(
                "Неверный статус для start_inspection | rental_id=%s status=%s user=%s",
                rental.id, rental.status, request.user,
            )
            return _conflict_response(
                problem_type='/problems/invalid-status',
                title='Неверный статус для начала осмотра',
                detail=(
                    f'Актуальный статус Rental: {rental.status}, '
                    f'для выполнения данного действия требуется {Statuses.BOOKED.value}'
                ),
                instance=request.build_absolute_uri(),
            )

        rental.inspection_started_at = timezone.now()
        rental.status = Statuses.INSPECTING.value
        rental.save(update_fields=['inspection_started_at', 'status'])

        logger.info(
            "Осмотр начат | rental_id=%s car_id=%s user=%s",
            rental.id, rental.car_id, request.user,
        )
        return Response(
            {
                'status': status.HTTP_200_OK,
                'data': {
                    'rental_id': rental.id,
                    'car_id': rental.car_id,  # исправлено: было rental.car.id (лишний запрос к БД)
                    'started_at': rental.inspection_started_at,
                    'status': rental.status,
                    'new_button_text': rental.get_button_text(),
                },
                'message': 'Осмотр автомобиля успешно начат',
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, url_path='start-rental', methods=['post'])
    @transaction.atomic
    def start_rental(self, request, *args, **kwargs) -> Response:
        """
        Перевести аренду из статуса INSPECTING → ACTIVE.

        Endpoint: POST /api/v1/cars/{car_pk}/rentals/{id}/start-rental/

        Args:
            request: HTTP-запрос.

        Returns:
            Response 200: Аренда начата. Возвращает rental_id, car_id, время начала и статус.
            Response 409: Аренда находится в статусе, отличном от INSPECTING.
        """
        rental = self.get_object()

        if rental.status != Statuses.INSPECTING.value:
            logger.warning(
                "Неверный статус для start_rental | rental_id=%s status=%s user=%s",
                rental.id, rental.status, request.user,
            )
            return _conflict_response(
                problem_type='/problems/invalid-status',
                title='Неверный статус для начала аренды',
                detail=(
                    f'Актуальный статус Rental: {rental.status}, '
                    f'для выполнения данного действия требуется {Statuses.INSPECTING.value}'
                ),
                instance=request.build_absolute_uri(),
            )

        rental.start_time = timezone.now()
        rental.status = Statuses.ACTIVE.value
        rental.save(update_fields=['start_time', 'status'])

        logger.info(
            "Аренда начата | rental_id=%s car_id=%s user=%s",
            rental.id, rental.car_id, request.user,
        )
        return Response(
            {
                'status': status.HTTP_200_OK,
                'data': {
                    'rental_id': rental.id,
                    'car_id': rental.car_id,
                    'started_at': rental.start_time,
                    'status': rental.status,
                    'new_button_text': rental.get_button_text(),
                },
                'message': 'Аренда автомобиля успешно началась',
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, url_path='end-rental', methods=['post'])
    @transaction.atomic
    def end_rental(self, request, *args, **kwargs) -> Response:
        """
        Перевести аренду из статуса ACTIVE → COMPLETED.

        Endpoint: POST /api/v1/cars/{car_pk}/rentals/{id}/end-rental/

        Args:
            request: HTTP-запрос.

        Returns:
            Response 200: Аренда завершена. Возвращает rental_id, car_id, время начала/конца и статус.
            Response 409: Аренда находится в статусе, отличном от ACTIVE.
        """
        rental = self.get_object()

        if rental.status != Statuses.ACTIVE.value:
            logger.warning(
                "Неверный статус для end_rental | rental_id=%s status=%s user=%s",
                rental.id, rental.status, request.user,
            )
            return _conflict_response(
                problem_type='/problems/invalid-status',
                title='Неверный статус для окончания аренды',
                detail=(
                    f'Актуальный статус Rental: {rental.status}, '
                    f'для выполнения данного действия требуется {Statuses.ACTIVE.value}'
                ),
                instance=request.build_absolute_uri(),
            )

        rental.end_time = timezone.now()
        rental.status = Statuses.COMPLETED.value
        rental.save(update_fields=['end_time', 'status'])

        logger.info(
            "Аренда завершена | rental_id=%s car_id=%s user=%s duration=%s",
            rental.id, rental.car_id, request.user,
            rental.end_time - rental.start_time,
        )
        return Response(
            {
                'status': status.HTTP_200_OK,
                'data': {
                    'rental_id': rental.id,
                    'car_id': rental.car_id,
                    'started_at': rental.start_time,
                    'ended_at': rental.end_time,
                    'status': rental.status,
                    'new_button_text': rental.get_button_text(),
                },
                'message': 'Аренда автомобиля успешно завершена',
            },
            status=status.HTTP_200_OK,
        )
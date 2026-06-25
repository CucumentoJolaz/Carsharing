from rest_framework import permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from django.db import transaction
from .models import Car, Rental, Statuses
from .serializers import CarSerializer, RentalSerializer
from .utils import conflict_response, forbidden_response, TRANSITION_CONFIG
from django.utils import timezone
from django.http import Http404
import logging

logger = logging.getLogger(__name__)

# ==================================================================== #
#  ViewSets                                                            #
# ==================================================================== #


class CarViewSet(viewsets.ModelViewSet):
    """CRUD для модели Car. Возвращает только активные автомобили."""

    queryset = Car.objects.filter(active=True)
    serializer_class = CarSerializer
    permission_classes = (permissions.IsAuthenticated,)


class RentalViewSet(viewsets.ModelViewSet):
    """
    Управление арендами автомобилей.

    Жизненный цикл: BOOKED → INSPECTING → ACTIVE → COMPLETED

    Эндпоинты:
        POST /api/v1/cars/{car_pk}/rentals/                        — создать бронь
        POST /api/v1/cars/{car_pk}/rentals/{id}/start-inspection/  — начать осмотр
        POST /api/v1/cars/{car_pk}/rentals/{id}/start-rental/      — начать аренду
        POST /api/v1/cars/{car_pk}/rentals/{id}/end-rental/        — завершить аренду
        GET  /api/v1/cars/{car_pk}/rentals/                        — список аренд
    """

    serializer_class = RentalSerializer
    permission_classes = (permissions.IsAuthenticated,)

    # ==================================================================== #
    #  Базовые методы                                                      #
    # ==================================================================== #

    def get_object(self) -> Rental:
        """Возвращает Rental с SELECT FOR UPDATE и проверкой владельца."""
        pk = self.kwargs["pk"]
        try:
            rental = Rental.objects.select_for_update().get(pk=pk)
        except Rental.DoesNotExist:
            logger.warning("Rental pk=%s не найден | user=%s", pk, self.request.user)
            raise Http404()

        logger.debug(
            "Rental %s получен с блокировкой строки | user=%s",
            rental.id,
            self.request.user,
        )
        return rental

    def get_queryset(self):
        car_pk = self.kwargs.get("car_pk")
        if not car_pk:
            logger.error(
                "get_queryset вызван без car_pk | user=%s path=%s",
                self.request.user,
                self.request.path,
            )
            return Rental.objects.none()

        car = get_object_or_404(Car, pk=car_pk, active=True)
        return Rental.objects.filter(car_id=car.pk)

    def _check_rental_owner(self, rental: Rental, request) -> Response | None:
        """
        Проверяет, что текущий пользователь является владельцем аренды.

        Returns:
            403 Response — если не владелец, None — если проверка пройдена.
        """
        if rental.user_id != request.user.pk:
            logger.warning(
                "Попытка чужого доступа к аренде | rental_id=%s owner_id=%s requester=%s",
                rental.id,
                rental.user_id,
                request.user,
            )
            return forbidden_response(
                detail=f"Аренда (ID: {rental.id}) принадлежит другому пользователю.",
                instance=request.build_absolute_uri(),
            )
        return None

    # ==================================================================== #
    #  Общий обработчик переходов                                          #
    # ==================================================================== #

    @transaction.atomic
    def _transition(self, request, transition_name: str, **kwargs) -> Response:
        """
        Универсальный обработчик перехода состояния аренды.

        Выполняет:
            1. Получение аренды с блокировкой строки
            2. Проверку прав доступа (владелец аренды)
            3. Валидацию текущего статуса
            4. Запись временно́й метки и смену статуса
            5. Логирование и формирование ответа
        """
        config = TRANSITION_CONFIG[transition_name]
        rental = self.get_object()

        if (forbidden := self._check_rental_owner(rental, request)) is not None:
            return forbidden

        if rental.status != config["required_status"]:
            logger.warning(
                "Неверный статус для %s | rental_id=%s status=%s user=%s",
                transition_name,
                rental.id,
                rental.status,
                request.user,
            )
            return conflict_response(
                problem_type="/problems/invalid-status",
                title=config["conflict_title"],
                detail=(
                    f"Актуальный статус Rental: {rental.status}, "
                    f'для выполнения данного действия требуется {config["required_status"]}'
                ),
                instance=request.build_absolute_uri(),
            )

        timestamp_now = timezone.now()
        # Устанавливаем поля с информацией о времени начала действия определённого статуса для аренды
        # INSPECTING - inspection_started_at
        # ACTIVE - start_time
        # COMPLETED - end_time
        setattr(rental, config["timestamp_field"], timestamp_now)
        rental.status = config["next_status"]
        rental.save(update_fields=[config["timestamp_field"], "status"])

        logger.info(
            "%s | rental_id=%s car_id=%s user=%s",
            config["log_message"],
            rental.id,
            rental.car_id,
            request.user,
        )
        data = {
            "rental_id": rental.id,
            "car_id": rental.car_id,
            config["response_key"]: timestamp_now,
            "status": rental.status,
            "new_button_text": rental.get_button_text(),
        }
        for response_key, model_field in config.get("extra_fields", {}).items():
            data[response_key] = getattr(rental, model_field)
        return Response(
            {
                "status": status.HTTP_200_OK,
                "data": data,
                "message": config["response_message"],
            },
            status=status.HTTP_200_OK,
        )

    # ==================================================================== #
    #  Создание аренды                                                     #
    # ==================================================================== #

    @transaction.atomic
    def create(self, request, *args, **kwargs) -> Response:
        """
        Создать новую аренду (BOOKED).

        POST /api/v1/cars/{car_pk}/rentals/

        Returns:
            201 — аренда создана
            400 — невалидные данные
            404 — автомобиль не найден или неактивен
            409 — у пользователя уже есть активная аренда
        """
        active_statuses = [
            Statuses.BOOKED.value,
            Statuses.INSPECTING.value,
            Statuses.ACTIVE.value,
        ]
        existing_rental = Rental.objects.filter(
            user=request.user, status__in=active_statuses
        ).first()

        if existing_rental:
            logger.warning(
                "Попытка создать аренду при наличии активной | user=%s existing_rental_id=%s status=%s",
                request.user,
                existing_rental.id,
                existing_rental.status,
            )
            return conflict_response(
                problem_type="/problems/multiple-rentals",
                title="Существуют активные аренды у пользователя",
                detail=(
                    f"У вас уже есть активная аренда (ID: {existing_rental.id}, "
                    f"статус: {existing_rental.status}). "
                    f"Пожалуйста, обратитесь к администратору для решения проблемы."
                ),
                instance=request.build_absolute_uri(),
            )

        car = get_object_or_404(Car, pk=self.kwargs.get("car_pk"), active=True)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rental = serializer.save(
            car=car, user=request.user, status=Statuses.BOOKED.value
        )

        logger.info(
            "Аренда создана | rental_id=%s car_id=%s user=%s",
            rental.id,
            car.id,
            request.user,
        )
        return Response(
            {
                "status": status.HTTP_201_CREATED,
                "data": {
                    "rental_id": rental.id,
                    "car_id": car.id,
                    "started_at": rental.booked_at,
                    "status": Statuses.BOOKED.value,
                    "new_button_text": rental.get_button_text(),
                },
                "message": "Аренда создана. Автомобиль успешно забронирован.",
            },
            status=status.HTTP_201_CREATED,
        )

    # ==================================================================== #
    #  Переходы состояний (делегируют в _transition)                       #
    # ==================================================================== #

    @action(detail=True, methods=["post"], url_path="start-inspection")
    def start_inspection(self, request, *args, **kwargs) -> Response:
        """BOOKED → INSPECTING. POST /api/v1/cars/{car_pk}/rentals/{id}/start-inspection/"""
        return self._transition(request, "start_inspection")

    @action(detail=True, methods=["post"], url_path="start-rental")
    def start_rental(self, request, *args, **kwargs) -> Response:
        """INSPECTING → ACTIVE. POST /api/v1/cars/{car_pk}/rentals/{id}/start-rental/"""
        return self._transition(request, "start_rental")

    @action(detail=True, methods=["post"], url_path="end-rental")
    def end_rental(self, request, *args, **kwargs) -> Response:
        """ACTIVE → COMPLETED. POST /api/v1/cars/{car_pk}/rentals/{id}/end-rental/"""
        return self._transition(request, "end_rental")

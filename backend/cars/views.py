from rest_framework import generics, permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from django.db import transaction
from .models import Car, Rental, Statuses
from .serializers import CarSerializer, RentalSerializer
from django.utils import timezone
from django.http import Http404

class CarViewSet(viewsets.ModelViewSet):
    """
    Стандартный ModelViewSet для Car объекта.
    
    """
    queryset = Car.objects.filter(active=True)
    serializer_class = CarSerializer
    permission_classes = (permissions.IsAuthenticated,)


class RentalViewSet(viewsets.ModelViewSet):
    """
    Управление арендами автомобилей.

    Реализует жизненный цикл аренды в виде конечного автомата:
        BOOKED → INSPECTING → ACTIVE → COMPLETED

    Переходы инициируются через отдельные эндпоинты:
        POST /api/v1/cars/{car_pk}/rentals/          — создать бронь (BOOKED)
        POST /api/v1/cars/{car_pk}/rentals/{id}/start-inspection/  — начать осмотр (INSPECTING)
        POST /api/v1/cars/{car_pk}/rentals/{id}/start-rental/      — начать аренду (ACTIVE)
        POST /api/v1/cars/{car_pk}/rentals/{id}/end-rental/        — завершить аренду (COMPLETED)

    При неверном статусе возвращает 409 Conflict (application/problem+json).
    get_object использует select_for_update() для защиты от гонок при
    одновременном изменении статуса.
    """
    serializer_class = RentalSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):

        try:
            return Rental.objects.select_for_update().get(pk=self.kwargs['pk'])
        except Rental.DoesNotExist:
            raise Http404()

    def get_queryset(self):
        """
        Obtain list of Rentals for the specific Car defined by Car id.
        If Car id is not defined - return 400 error.
        """
        car_pk = self.kwargs.get('car_pk')
        
        if car_pk:
            car = Car.objects.get(id=car_pk)
            if car.active:
                return Rental.objects.filter(id=car_pk)
            else:
                raise Http404()
        else:
            return Response({
            'type': f'/problems/no-car-id',
            'title': f'Нет id для арендуемой машины',
            'status': status.HTTP_400_BAD_REQUEST,
            'detail':
                (f'Вы направили запрос на получение аренд автомобиля, но не указали id автомобиля.'),
            'instance': f'{self.request.build_absolute_uri()}'
        },
            status=status.HTTP_400_BAD_REQUEST,
            content_type='application/problem+json')
        
    @transaction.atomic()
    def create(self, request, *args, **kwargs):
        """
        Create a new rental and book the specified car.

        Endpoint: POST /api/v1/cars/{car_pk}/rentals/

        Args:
            request: HTTP request object containing rental data.
            car_pk (int): Car ID extracted from the URL kwargs.

        Returns:
            Response 201: Rental created successfully with rental_id, car_id and status.
            Response 404: Car with the given ID not found.
            Response 400: Invalid or missing rental data.
            Response 409: The User already have active Rentals
        """
        active_statuses = [Statuses.BOOKED.value, Statuses.INSPECTING.value, Statuses.ACTIVE.value]
        existing_rental = Rental.objects.filter(user=request.user, status__in=active_statuses).first()

        if existing_rental:
            return Response({
            'type': f'/problems/multiple-rentals',
            'title': f'Существуют активные аренды у пользователя',
            'status': status.HTTP_409_CONFLICT,
            'detail':
                (f'У вас уже есть активная аренда (ID: {existing_rental.id}, '
                    f'статус: {existing_rental.status}). '
                    f'Пожалуйста, обратитесь к администратору для решения проблемы.'),
            'instance': f'{request.build_absolute_uri()}'
        },
            status=status.HTTP_409_CONFLICT,
            content_type='application/problem+json')


        car = get_object_or_404(Car, pk=self.kwargs.get('car_pk'))
        if not car.active:
            raise Http404(f"Машина под номером {car.id} не является активной для аренды.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=False)
        rental = serializer.save(car=car, user=request.user, status=Statuses.BOOKED.value)

        return Response({
            'status': status.HTTP_201_CREATED,
            'data': {'rental_id': rental.id,
                     'car_id': car.id,
                     'started_at': rental.booked_at,
                     'status': Statuses.BOOKED.value,
                     'new_button_text': rental.get_button_text()},
            'message': 'Аренда создана. Автомобиль успешно забронирован.',
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='start-inspection')
    @transaction.atomic()
    def start_inspection(self, request, *args, **kwargs):

        rental = self.get_object()
        if rental.status == Statuses.BOOKED.value:
            rental.inspection_started_at = timezone.now()
            rental.status = Statuses.INSPECTING.value
            rental.save(update_fields=['inspection_started_at', 'status'])
            return Response({
                'status': status.HTTP_200_OK,
                'data': {
                    'rental_id': rental.id,
                    'car_id': rental.car.id,
                    'started_at': rental.inspection_started_at,
                    'status': rental.status,
                    'new_button_text': rental.get_button_text()
                },
                'message': 'Осмотр автомобиля успешно начат',
            }, status=status.HTTP_200_OK)

        return Response(
            {
                'type': f'/problems/invalid-status',
                'title': f'Неверный статус для начала осмотра',
                'status': status.HTTP_409_CONFLICT,
                'detail': f'Актуальный статус Rental: {rental.status}, для выполнения данного действия требуется {Statuses.BOOKED.value}',
                'instance': f'{request.build_absolute_uri()}',
            },
            status=status.HTTP_409_CONFLICT,
            content_type='application/problem+json'
        )

    @action(detail=True, url_path='start-rental', methods=['post'])
    @transaction.atomic()
    def start_rental(self, request, *args, **kwargs):
        rental = self.get_object()
        if rental.status == Statuses.INSPECTING.value:
            rental.start_time = timezone.now()
            rental.status = Statuses.ACTIVE.value
            rental.save(update_fields=['start_time', 'status'])
            return Response({
                'status': status.HTTP_200_OK,
                'data': {
                    'rental_id': rental.id,
                    'car_id': rental.car.id,
                    'started_at': rental.start_time,
                    'status': rental.status,
                    'new_button_text': rental.get_button_text()
                },
                'message': 'Аренда автомобиля успешно началась',
            }, status=status.HTTP_200_OK)

        return Response(
            {
                'type': f'/problems/invalid-status',
                'title': f'Неверный статус для начала аренды',
                'status': status.HTTP_409_CONFLICT,
                'detail': f'Актуальный статус Rental: {rental.status}, для выполнения данного действия требуется {Statuses.INSPECTING.value}',
                'instance': f'{request.build_absolute_uri()}',
            },
            status=status.HTTP_409_CONFLICT,
            content_type='application/problem+json'
        )


    @action(detail=True, url_path='end-rental', methods=['post'])
    @transaction.atomic()
    def end_rental(self, request, *args, **kwargs):
        rental = self.get_object()
        if rental.status == Statuses.ACTIVE.value:
            rental.end_time = timezone.now()
            rental.status = Statuses.COMPLETED.value
            rental.save(update_fields=['end_time', 'status'])
            return Response({
                'status': status.HTTP_200_OK,
                'data': {
                    'rental_id': rental.id,
                    'car_id': rental.car.id,
                    'started_at': rental.start_time,
                    'ended_at': rental.end_time,
                    'status': rental.status,
                    'new_button_text': rental.get_button_text()
                },
                'message': 'Аренда автомобиля успешно завершена',
            }, status=status.HTTP_200_OK)

        return Response(
            {
                'type': f'/problems/invalid-status',
                'title': f'Неверный статус для окончания аренды',
                'status': status.HTTP_409_CONFLICT,
                'detail': f'Актуальный статус Rental: {rental.status}, для выполнения данного действия требуется {Statuses.ACTIVE.value}',
                'instance': f'{request.build_absolute_uri()}',
            },
            status=status.HTTP_409_CONFLICT,
            content_type='application/problem+json'
        )

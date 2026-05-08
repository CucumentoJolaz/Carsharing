from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from cars.serializers import RentalSerializer
from .models import User
from .serializers import UserSerializer, RegisterSerializer, LoginSerializer
from cars.models import Rental, Statuses
import logging

logger = logging.getLogger(__name__)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })


class UserProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


@api_view(['GET'])
def mock_user(request):
    user = User.objects.first()
    refresh = RefreshToken.for_user(user)
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_rental_view(request):
    """
    Return the information about active Rental of a User, or None if User does not have active rental.

    Endpoint: GET /api/v1/users/me/rental/
    """

    try:
        rental = Rental.objects.get(user=request.user, end_time=None)
        serializer = RentalSerializer(rental)
        return Response({
            'message': f'Активная аренда найдена успешно. № объекта Rental {rental.id}',
            'status': status.HTTP_200_OK,
            'data': serializer.data
        },
            status=status.HTTP_200_OK)
    except Rental.DoesNotExist:
        return Response({
            'status': status.HTTP_200_OK,
            'message': 'Активных аренд не найдено',
            'data': None
        },
            status=status.HTTP_200_OK)
    except Rental.MultipleObjectsReturned:
        active_statuses = [Statuses.BOOKED.value, Statuses.INSPECTING.value, Statuses.ACTIVE.value]
        existing_rentals = Rental.objects.filter(user=request.user, status__in=active_statuses)
        logger.error(
            f"У пользователя {request.user.id} обнаружено несколько активных аренд. "
            f"Ожидается 0 или 1, получено больше."
        )
        return Response({
            'type': f'/problems/multiple-rentals',
            'title': f'Несколько активных аренд у одного пользователя',
            'status': status.HTTP_409_CONFLICT,
            'detail':
                (f'У вас {existing_rentals.count()} незакрытых аренд. Мы не можем Вас допустить к открытию новой аренды.\n'
                 f'Пожалуйста, обратитесь к администратору для решения проблемы.'),
            'instance': f'{request.build_absolute_uri()}'
        },
            status=status.HTTP_409_CONFLICT,
            content_type='application/problem+json')

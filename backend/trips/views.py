from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Trip
from .serializers import TripSerializer
from cars.models import Car


class StartTripView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        car_id = request.data.get('car_id')
        car = Car.objects.get(id=car_id)

        if car.status != 'available':
            return Response({'error': 'Машина недоступна'}, status=status.HTTP_400_BAD_REQUEST)

        trip = Trip.objects.create(
            user=request.user,
            car=car,
            start_latitude=car.latitude,
            start_longitude=car.longitude
        )

        car.status = 'rented'
        car.save()

        serializer = TripSerializer(trip)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ActiveTripView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        try:
            trip = Trip.objects.get(user=request.user, is_active=True)
            serializer = TripSerializer(trip)
            return Response(serializer.data)
        except Trip.DoesNotExist:
            return Response({'active': False}, status=status.HTTP_404_NOT_FOUND)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Sum, Count, Avg
from cars.models import Car
from trips.models import Trip
from users.models import User


class AnalyticsView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        # Общая статистика
        total_cars = Car.objects.count()
        available_cars = Car.objects.filter(status='available').count()
        rented_cars = Car.objects.filter(status='rented').count()

        total_mileage = Car.objects.aggregate(total=Sum('mileage'))['total'] or 0

        total_rentals = Trip.objects.count()
        active_rentals = Trip.objects.filter(is_active=True).count()

        # Статистика по городам
        cities_data = []
        cities = Car.objects.values('city').distinct()

        for city in cities:
            city_name = city['city']
            cars_in_city = Car.objects.filter(city=city_name).count()
            rentals_in_city = Trip.objects.filter(car__city=city_name).count()

            cities_data.append({
                'city': city_name,
                'cars': cars_in_city,
                'rentals': rentals_in_city
            })

        # Статистика по автомобилям
        top_cars = Trip.objects.values('car__brand', 'car__model').annotate(
            rentals=Count('id'),
            total_distance=Sum('distance_km')
        ).order_by('-rentals')[:5]

        # Финансовая статистика
        total_revenue = Trip.objects.aggregate(total=Sum('cost'))['total'] or 0
        avg_cost_per_trip = Trip.objects.aggregate(avg=Avg('cost'))['avg'] or 0

        response_data = {
            'cars': {
                'total': total_cars,
                'available': available_cars,
                'rented': rented_cars,
            },
            'mileage': {
                'total_km': total_mileage
            },
            'rentals': {
                'total': total_rentals,
                'active': active_rentals
            },
            'cities': cities_data,
            'top_cars': list(top_cars),
            'revenue': {
                'total': float(total_revenue),
                'average_per_trip': float(avg_cost_per_trip)
            }
        }

        return Response(response_data)
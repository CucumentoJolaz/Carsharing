import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Trip
from cars.models import Car
from datetime import datetime
from decimal import Decimal


class TripConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.trip_id = self.scope['url_route']['kwargs']['trip_id']
        self.room_group_name = f'trip_{self.trip_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'update_position':
            await self.update_car_position(data)
        elif action == 'end_trip':
            await self.end_trip(data)

    @database_sync_to_async
    def update_car_position(self, data):
        trip = Trip.objects.get(id=self.trip_id)
        car = trip.car
        car.latitude = data['latitude']
        car.longitude = data['longitude']
        car.save()

        # Обновляем пробег
        if 'distance' in data:
            trip.distance_km = data['distance']
            trip.save()
            car.mileage += int(data['distance'])
            car.save()

    @database_sync_to_async
    def end_trip(self, data):
        trip = Trip.objects.get(id=self.trip_id)
        car = trip.car

        trip.end_time = datetime.now()
        trip.end_latitude = data['latitude']
        trip.end_longitude = data['longitude']

        # Расчет длительности в минутах
        duration = (trip.end_time - trip.start_time).total_seconds() / 60
        trip.duration_minutes = int(duration)

        # Расчет стоимости (5 руб/мин + 10 руб/км)
        cost = (duration * 5) + (trip.distance_km * 10)
        trip.cost = Decimal(str(cost))
        trip.is_active = False
        trip.save()

        # Обновляем статус машины
        car.status = 'available'
        car.save()

        # Обновляем статистику пользователя
        user = trip.user
        user.total_trips += 1
        user.save()

        return trip.id
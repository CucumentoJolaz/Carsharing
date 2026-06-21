import os
import django
import random
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carsharing.settings')
django.setup()

from cars.models import Car
from users.models import User
from trips.models import Trip


def create_cars():
    cars_data = [
        
        
        
        
        
        ('Ford', 'Focus', 2022, 'G007GG', 55.7523, 37.6255, 'Москва'),
        ('Nissan', 'Qashqai', 2023, 'H008HH', 55.7492, 37.6328, 'Москва'),
        ('BMW', 'X5', 2024, 'I009II', 59.9311, 30.3609, 'Санкт-Петербург'),
        ('Mercedes', 'E-Class', 2023, 'J010JJ', 59.9375, 30.3086, 'Санкт-Петербург'),

        ('Toyota', 'Camry', 2022, 'A001AA', 55.7558, 37.6176, 'Москва'),
        ('Toyota', 'Camry', 2024, 'X777XX', 55.7601, 37.6195, 'Москва'),
        ('Toyota', 'Camry', 2025, 'Y888YY', 59.9355, 30.3362, 'Санкт-Петербург'),
        ('Toyota', 'RAV4', 2024, 'Z999ZZ', 55.7530, 37.6220, 'Москва'),
        ('Toyota', 'Corolla', 2023, 'A111AB', 59.9320, 30.3330, 'Санкт-Петербург'),

        # Hyundai
        ('Hyundai', 'Solaris', 2023, 'B002BB', 55.7512, 37.6185, 'Москва'),
        ('Hyundai', 'Solaris', 2024, 'B222BC', 55.7565, 37.6160, 'Москва'),
        ('Hyundai', 'Solaris', 2025, 'C333CD', 59.9380, 30.3120, 'Санкт-Петербург'),
        ('Hyundai', 'Creta', 2024, 'D444DE', 55.7505, 37.6300, 'Москва'),
        ('Hyundai', 'Tucson', 2025, 'E555EF', 59.9360, 30.3400, 'Санкт-Петербург'),

        # Kia
        ('Kia', 'Rio', 2021, 'C003CC', 55.7589, 37.6213, 'Москва'),
        ('Kia', 'Rio', 2023, 'F666FG', 55.7595, 37.6180, 'Москва'),
        ('Kia', 'Rio', 2024, 'G777GH', 59.9330, 30.3380, 'Санкт-Петербург'),
        ('Kia', 'Sportage', 2024, 'H888HI', 55.7528, 37.6245, 'Москва'),
        ('Kia', 'K5', 2025, 'I999IJ', 59.9370, 30.3100, 'Санкт-Петербург'),

        # Volkswagen
        ('Volkswagen', 'Polo', 2022, 'D004DD', 55.7456, 37.6342, 'Санкт-Петербург'),
        ('Volkswagen', 'Polo', 2023, 'J000JK', 55.7545, 37.6320, 'Москва'),
        ('Volkswagen', 'Polo', 2024, 'K111KL', 59.9348, 30.3340, 'Санкт-Петербург'),
        ('Volkswagen', 'Tiguan', 2025, 'L222LM', 55.7570, 37.6205, 'Москва'),

        # Skoda
        ('Skoda', 'Octavia', 2023, 'E005EE', 59.9343, 30.3351, 'Санкт-Петербург'),
        ('Skoda', 'Octavia', 2024, 'M333MN', 59.9350, 30.3370, 'Санкт-Петербург'),
        ('Skoda', 'Rapid', 2023, 'N444NO', 55.7518, 37.6270, 'Москва'),

        # Renault
        ('Renault', 'Logan', 2021, 'F006FF', 59.9398, 30.3146, 'Санкт-Петербург'),
        ('Renault', 'Logan', 2022, 'O555OP', 59.9400, 30.3150, 'Санкт-Петербург'),

        # Ford
        ('Ford', 'Focus', 2023, 'P666PQ', 55.7535, 37.6265, 'Москва'),

        # Nissan
        ('Nissan', 'Qashqai', 2024, 'Q777QR', 55.7485, 37.6340, 'Москва'),

        # BMW
        ('BMW', 'X5', 2025, 'R888RS', 59.9305, 30.3620, 'Санкт-Петербург'),

        # Mercedes
        ('Mercedes', 'E-Class', 2024, 'S999ST', 59.9385, 30.3090, 'Санкт-Петербург'),
    ]

    for brand, model, year, plate, lat, lon, city in cars_data:
        Car.objects.create(
            brand=brand,
            model=model,
            year=year,
            license_plate=plate,
            latitude=lat,
            longitude=lon,
            odometer_reading=random.randint(5000, 50000),
            city=city
        )
    print(f"Создано {len(cars_data)} автомобилей")


def create_users():
    users_data = [
        ('user1', 'password123', 'user1@example.com', '+79123456789'),
        ('user2', 'password123', 'user2@example.com', '+79234567890'),
        ('user3', 'password123', 'user3@example.com', '+79345678901'),
    ]

    for username, password, email, phone in users_data:
        User.objects.create_user(
            username=username,
            password=password,
            email=email,
            phone_number=phone
        )
    print(f"Создано {len(users_data)} пользователей")


def create_trips():
    users = User.objects.all()
    cars = Car.objects.all()

    for i in range(50):
        user = random.choice(users)
        car = random.choice(cars)
        start_date = datetime.now() - timedelta(days=random.randint(1, 30))
        duration_minutes = random.randint(15, 120)
        distance_km = random.randint(5, 50)

        trip = Trip.objects.create(
            user=user,
            car=car,
            start_time=start_date,
            end_time=start_date + timedelta(minutes=duration_minutes),
            start_latitude=car.latitude + random.uniform(-0.01, 0.01),
            start_longitude=car.longitude + random.uniform(-0.01, 0.01),
            end_latitude=car.latitude + random.uniform(-0.02, 0.02),
            end_longitude=car.longitude + random.uniform(-0.02, 0.02),
            distance_km=distance_km,
            duration_minutes=duration_minutes,
            cost=duration_minutes * 5 + distance_km * 10,
            is_active=False
        )

        user.total_trips += 1
        user.save()

        car.odometer_reading += distance_km
        car.save()

    print(f"Создано 50 поездок")


if __name__ == '__main__':
    print("Наполнение базы данных тестовыми данными...")
    create_cars()
    create_users()
    create_trips()
    print("Готово!")

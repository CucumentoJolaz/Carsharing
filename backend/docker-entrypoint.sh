#!/bin/sh
set -eu

python scripts/wait_for_db.py

python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear

if [ "${FILL_DEMO_DATA:-0}" = "1" ]; then
    python manage.py shell -c "from cars.models import Car; raise SystemExit(0 if Car.objects.exists() else 1)" \
        || python manage.py init_data --with-photos
fi

exec "$@"

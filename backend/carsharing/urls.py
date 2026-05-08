from django.contrib import admin
from django.urls import path, include
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/cars/', include('cars.urls')),
    path('api/v1/trips/', include('trips.urls')),
    path('api/v1/users/', include('users.urls')),
    path('api/v1/analytics/', include('analytics.urls')),
]

if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
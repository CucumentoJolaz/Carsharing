from django.contrib import admin
from .models import Car, Rental


class CarAdmin(admin.ModelAdmin):
    pass


admin.site.register(Car, CarAdmin)
admin.site.register(Rental, CarAdmin)
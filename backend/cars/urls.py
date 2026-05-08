from .views import CarViewSet, RentalViewSet
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter


router = DefaultRouter()
router.register(r"", CarViewSet, basename="car")

cars_router = NestedDefaultRouter(router, '', lookup='car')
cars_router.register(r"rentals", RentalViewSet, basename="rental")

urlpatterns = router.urls + cars_router.urls
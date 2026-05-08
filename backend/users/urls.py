from django.urls import path
from .views import RegisterView, LoginView, UserProfileView, user_rental_view, mock_user

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('me/rental/', user_rental_view, name='user-rental'),
    path('mock-user/', mock_user, name='mock-user'),
]
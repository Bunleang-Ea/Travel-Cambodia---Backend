from django.urls import path
from . import views

urlpatterns = [
    path('places/', views.get_all_places, name='get_all_places'),
    
    # New Auth Endpoints
    path('auth/register/', views.register_user, name='register_user'),
    path('auth/verify-otp/', views.verify_otp, name='verify_otp'),
    path('auth/login/', views.login_user, name='login_user'),
]
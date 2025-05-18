from django.urls import path
from . import views
from rest_framework.authtoken.views import obtain_auth_token

app_name = 'authserver'

urlpatterns = [
    # API overview
    path('', views.api_overview, name='api_overview'),
    # User registration and profile
    path('register/', views.RegisterView.as_view(), name='register'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    # Two-step authentication - explicit names
    path('login/step1/', views.LoginStep1View.as_view(), name='login_step1'),
    path('login/step2/', views.LoginStep2View.as_view(), name='login_step2'),
    # 2FA setup endpoints
    path('setup-google-auth/', views.SetupGoogleAuthView.as_view(), name='setup_google_auth'),
    path('setup-sms-auth/', views.SetupSMSAuthView.as_view(), name='setup_sms_auth'),
    # Backward compatibility endpoints
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('verify-2fa/', views.VerifyTwoFactorView.as_view(), name='verify_2fa'),
    # Note: 2FA endpoints will be added later
] 
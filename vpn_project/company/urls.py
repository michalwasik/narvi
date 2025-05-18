from django.urls import path
from . import views

app_name = 'company'

urlpatterns = [
    # Placeholder for company endpoints
    path('', views.api_overview, name='api_overview'),
] 
from django.urls import path
from . import views

app_name = 'company'

urlpatterns = [
    # Placeholder for company endpoints
    path('', views.api_overview, name='api_overview'),
    
    # Company endpoints
    path('v1.0/company/', views.CompanyCreateView.as_view(), name='company_create'),
    path('v1.0/company/<str:pid>/', views.CompanyDetailView.as_view(), name='company_detail'),
    path('v1.0/company/<str:pid>/changelog/', views.CompanyChangeLogView.as_view(), name='company_changelog'),
] 
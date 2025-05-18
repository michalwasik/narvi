from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

# Create your views here.

@api_view(['GET'])
@permission_classes([AllowAny])
def api_overview(request):
    """
    Overview of available company API endpoints
    """
    api_urls = {
        'Company Details': '/v1.0/company/<pid>/',
        'Update Company': '/v1.0/company/<pid>/ (PATCH)',
    }
    return Response(api_urls)

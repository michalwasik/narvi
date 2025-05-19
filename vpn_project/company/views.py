from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView
from django.db import transaction

from .models import Company, ChangeLog
from .serializers import CompanySerializer, ChangeLogSerializer
from .services import CompanyService

# Create your views here.

@api_view(['GET'])
@permission_classes([AllowAny])
def api_overview(request):
    """
    Overview of available company API endpoints
    """
    api_urls = {
        'Create Company': '/v1.0/company/',
        'Company Details': '/v1.0/company/<pid>/',
        'Update Company': '/v1.0/company/<pid>/ (PATCH)',
        'Company Changelog': '/v1.0/company/<pid>/changelog/',
    }
    return Response(api_urls)

class CompanyCreateView(CreateAPIView):
    """
    Create a new company.
    Supports POST method.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CompanySerializer
    
    def create(self, request, *args, **kwargs):
        """Custom create method to handle nested objects including taxinfo"""
        # First validate the data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create company and related entities using the service
        with transaction.atomic():
            # Create the basic company
            company = Company.objects.create(
                name=serializer.validated_data.get('name'),
                date_of_incorporation=serializer.validated_data.get('date_of_incorporation')
            )
            
            # Process the request data using our service
            # We're simulating a PATCH request to an existing company
            updated_company, _ = CompanyService.update_company(company, request.data)
            
            # Create changelog entry for company creation
            CompanyService.log_change(
                change_type='added',
                object_type='Company',
                object_pid=company.pid
            )
            
            # Return the serialized company
            serializer = self.get_serializer(updated_company)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class CompanyDetailView(APIView):
    """
    Retrieve or update a company instance.
    Supports GET and PATCH methods.
    """
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pid):
        """
        Get the company object from the database
        
        Args:
            pid: The public ID of the company
            
        Returns:
            Company instance
        """
        return get_object_or_404(Company, pid=pid)
    
    def get(self, request, pid, format=None):
        """
        Retrieve a company's details
        
        Args:
            request: The HTTP request
            pid: The public ID of the company
            format: The format of the response
            
        Returns:
            Response with company data
        """
        company = self.get_object(pid)
        serializer = CompanySerializer(company)
        return Response(serializer.data)
    
    def patch(self, request, pid, format=None):
        """
        Partially update a company and its nested objects
        All changes are recorded in the ChangeLog
        
        Args:
            request: The HTTP request
            pid: The public ID of the company
            format: The format of the response
            
        Returns:
            Response with updated company data or a message if no changes were detected
        """
        company = self.get_object(pid)
        
        # Validate the pid in the request data
        if 'pid' in request.data and request.data['pid'] != pid:
            return Response(
                {'error': 'The pid in the URL and request data must match'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update the company using the service
        updated_company, changes_made = CompanyService.update_company(company, request.data)
        
        # If no changes were detected, return a message
        if not changes_made:
            return Response(
                {'message': 'No changes detected'},
                status=status.HTTP_200_OK
            )
        
        # Serialize the updated company
        serializer = CompanySerializer(updated_company)
        
        return Response(serializer.data, status=status.HTTP_200_OK)

class CompanyChangeLogView(APIView):
    """
    Retrieve the change log for a company
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pid, format=None):
        """
        Get the changelog for a company
        
        Args:
            request: The HTTP request
            pid: The public ID of the company
            format: The format of the response
            
        Returns:
            Response with changelog data
        """
        # Get the company to verify it exists
        company = get_object_or_404(Company, pid=pid)
        
        # Get all changelogs related to this company
        changelogs = ChangeLog.objects.filter(object_pid=pid)
        
        # Get related objects' pids
        related_pids = set()
        
        # Add directors
        for director in company.directors.all():
            related_pids.add(director.pid)
        
        # Add shareholders
        for shareholder in company.shareholders.all():
            related_pids.add(shareholder.pid)
        
        # Get changelogs for related objects
        for related_pid in related_pids:
            related_changelogs = ChangeLog.objects.filter(object_pid=related_pid)
            changelogs = changelogs | related_changelogs
        
        # Order by timestamp
        changelogs = changelogs.order_by('-timestamp')
        
        serializer = ChangeLogSerializer(changelogs, many=True)
        return Response(serializer.data)

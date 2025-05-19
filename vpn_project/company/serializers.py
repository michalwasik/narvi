from rest_framework import serializers
from .models import Company, Director, Shareholder, TaxInfo, IdentityFile, ChangeLog
from django.contrib.contenttypes.models import ContentType

class IdentityFileSerializer(serializers.ModelSerializer):
    """
    Serializer for IdentityFile model
    """
    class Meta:
        model = IdentityFile
        fields = ['pid', 'file_name', 'file_path', 'file_type', 'uploaded_at']
        read_only_fields = ['pid', 'uploaded_at']
        lookup_field = 'pid'

class TaxInfoSerializer(serializers.ModelSerializer):
    """
    Serializer for TaxInfo model
    """
    class Meta:
        model = TaxInfo
        fields = ['pid', 'tin', 'country']
        read_only_fields = ['pid']
        lookup_field = 'pid'

class DirectorSerializer(serializers.ModelSerializer):
    """
    Serializer for Director model with nested identity files
    """
    identity_files = IdentityFileSerializer(many=True, required=False)
    taxinfo = TaxInfoSerializer(many=True, required=False, read_only=True)
    
    class Meta:
        model = Director
        fields = ['pid', 'full_name', 'taxinfo', 'identity_files']
        read_only_fields = ['pid']
        lookup_field = 'pid'

    def to_representation(self, instance):
        """Custom representation to ensure taxinfo is included correctly"""
        # First get the standard representation
        representation = super().to_representation(instance)
        
        # Manually get the tax info for the director
        director_content_type = ContentType.objects.get_for_model(instance)
        tax_infos = TaxInfo.objects.filter(
            content_type=director_content_type,
            object_id=instance.pid
        )
        
        # Serialize the tax info
        representation['taxinfo'] = TaxInfoSerializer(tax_infos, many=True).data
        
        return representation

class ShareholderSerializer(serializers.ModelSerializer):
    """
    Serializer for Shareholder model with nested identity files
    """
    identity_files = IdentityFileSerializer(many=True, required=False)
    
    class Meta:
        model = Shareholder
        fields = ['pid', 'full_name', 'percentage', 'identity_files']
        read_only_fields = ['pid']
        lookup_field = 'pid'

class CompanySerializer(serializers.ModelSerializer):
    """
    Serializer for Company model with all nested relationships
    """
    taxinfo = TaxInfoSerializer(many=True, required=False, read_only=True)
    directors = DirectorSerializer(many=True, required=False)
    shareholders = ShareholderSerializer(many=True, required=False)
    
    class Meta:
        model = Company
        fields = ['pid', 'name', 'date_of_incorporation', 'taxinfo', 'directors', 'shareholders']
        read_only_fields = ['pid']
        lookup_field = 'pid'

    def validate(self, data):
        """
        Ensure that percentage of all shareholders adds up to maximum 100%
        """
        shareholders_data = data.get('shareholders', [])
        
        if shareholders_data:
            total_percentage = sum(float(s.get('percentage', 0)) for s in shareholders_data)
            if total_percentage > 100:
                raise serializers.ValidationError(
                    {"shareholders": "Total percentage of shareholders cannot exceed 100%."}
                )
        
        return data

    def to_representation(self, instance):
        """Custom representation to ensure taxinfo is included correctly"""
        # First get the standard representation
        representation = super().to_representation(instance)
        
        # Manually get the tax info for the company
        company_content_type = ContentType.objects.get_for_model(instance)
        tax_infos = TaxInfo.objects.filter(
            content_type=company_content_type,
            object_id=instance.pid
        )
        
        # Serialize the tax info
        representation['taxinfo'] = TaxInfoSerializer(tax_infos, many=True).data
        
        return representation
    
    def create(self, validated_data):
        """
        Custom create method to handle nested objects
        """
        from django.db import transaction
        
        directors_data = validated_data.pop('directors', [])
        shareholders_data = validated_data.pop('shareholders', [])
        
        # We need to access taxinfo directly from request data as it's marked as read_only
        taxinfo_data = self.initial_data.get('taxinfo', []) if hasattr(self, 'initial_data') else []
        
        # Create the company
        with transaction.atomic():
            company = Company.objects.create(**validated_data)
            
            # Create tax info
            company_content_type = ContentType.objects.get_for_model(company)
            for tax_info in taxinfo_data:
                TaxInfo.objects.create(
                    tin=tax_info.get('tin', ''),
                    country=tax_info.get('country', ''),
                    content_type=company_content_type,
                    object_id=company.pid
                )
            
            # Create directors
            for director_data in directors_data:
                identity_files_data = director_data.pop('identity_files', [])
                director_tax_info = director_data.pop('taxinfo', [])
                
                # Create director
                director = Director.objects.create(company=company, **director_data)
                
                # Add identity files
                for idf_data in identity_files_data:
                    if 'pid' in idf_data:
                        # Link existing identity file
                        try:
                            identity_file = IdentityFile.objects.get(pid=idf_data['pid'])
                            director.identity_files.add(identity_file)
                        except IdentityFile.DoesNotExist:
                            pass
                    else:
                        # Create new identity file
                        identity_file = IdentityFile.objects.create(
                            file_name=idf_data.get('file_name', ''),
                            file_path=idf_data.get('file_path', ''),
                            file_type=idf_data.get('file_type', '')
                        )
                        director.identity_files.add(identity_file)
                
                # Add tax info
                director_content_type = ContentType.objects.get_for_model(director)
                for ti_data in director_tax_info:
                    TaxInfo.objects.create(
                        tin=ti_data.get('tin', ''),
                        country=ti_data.get('country', ''),
                        content_type=director_content_type,
                        object_id=director.pid
                    )
            
            # Create shareholders
            for shareholder_data in shareholders_data:
                identity_files_data = shareholder_data.pop('identity_files', [])
                
                # Create shareholder
                shareholder = Shareholder.objects.create(company=company, **shareholder_data)
                
                # Add identity files
                for idf_data in identity_files_data:
                    if 'pid' in idf_data:
                        # Link existing identity file
                        try:
                            identity_file = IdentityFile.objects.get(pid=idf_data['pid'])
                            shareholder.identity_files.add(identity_file)
                        except IdentityFile.DoesNotExist:
                            pass
                    else:
                        # Create new identity file
                        identity_file = IdentityFile.objects.create(
                            file_name=idf_data.get('file_name', ''),
                            file_path=idf_data.get('file_path', ''),
                            file_type=idf_data.get('file_type', '')
                        )
                        shareholder.identity_files.add(identity_file)
        
        return company
        
    def update(self, instance, validated_data):
        """
        Custom update method to handle nested objects
        Delegates the actual implementation to CompanyService
        """
        from .services import CompanyService
        
        # The service handles all the create, update, delete operations
        # for the company and its nested objects
        updated_company = CompanyService.update_company(instance, validated_data)
        
        return updated_company

class ChangeLogSerializer(serializers.ModelSerializer):
    """
    Serializer for ChangeLog model
    """
    class Meta:
        model = ChangeLog
        fields = ['id', 'change_type', 'object_type', 'object_pid', 'changes', 'timestamp']
        read_only_fields = ['id', 'timestamp'] 
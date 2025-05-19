from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from .models import Company, Director, Shareholder, TaxInfo, IdentityFile, ChangeLog

class CompanyService:
    """
    Service class for handling company-related operations
    """
    
    @staticmethod
    def create_field_diff(instance, field_name, new_value):
        """
        Create a diff object for a field change
        
        Args:
            instance: Model instance being updated
            field_name: Name of the field being changed
            new_value: New value for the field
            
        Returns:
            Dictionary with old and new values, or None if no change
        """
        old_value = getattr(instance, field_name)
        
        # Skip if values are the same
        if old_value == new_value:
            return None
            
        # Convert values to string if they're complex objects
        if hasattr(old_value, '__str__'):
            old_str = str(old_value)
        else:
            old_str = old_value
            
        if hasattr(new_value, '__str__'):
            new_str = str(new_value)
        else:
            new_str = new_value
            
        return {'old': old_str, 'new': new_str}
    
    @staticmethod
    def log_change(change_type, object_type, object_pid, changes=None):
        """
        Create a changelog entry
        
        Args:
            change_type: Type of change (added, removed, updated)
            object_type: Type of object being changed
            object_pid: Public ID of the object
            changes: Dictionary of field changes (for updates)
            
        Returns:
            Created ChangeLog instance
        """
        return ChangeLog.objects.create(
            change_type=change_type,
            object_type=object_type,
            object_pid=object_pid,
            changes=changes,
            timestamp=timezone.now()  # Explicitly set timestamp for consistency
        )
    
    @staticmethod
    def update_company(company, data):
        """
        Update a company and its related objects based on partial data
        
        Args:
            company: Company instance to update
            data: Dictionary containing update data
            
        Returns:
            Tuple of (Updated company instance, boolean indicating if changes were made)
        """
        with transaction.atomic():
            changes = []
            
            # Update basic company fields
            company_changes = CompanyService._update_company_fields(company, data)
            if company_changes:
                changes.append({
                    'change_type': 'updated',
                    'object_type': 'Company',
                    'object_pid': company.pid,
                    'changes': company_changes
                })
            
            # Handle tax info updates if present
            if 'taxinfo' in data:
                taxinfo_changes = CompanyService._update_company_taxinfo(company, data['taxinfo'])
                changes.extend(taxinfo_changes)
            
            # Handle directors updates if present
            if 'directors' in data:
                director_changes = CompanyService._update_directors(company, data['directors'])
                changes.extend(director_changes)
            
            # Handle shareholders updates if present
            if 'shareholders' in data:
                shareholder_changes = CompanyService._update_shareholders(company, data['shareholders'])
                changes.extend(shareholder_changes)
            
            # Create changelog entries for all changes
            for change in changes:
                CompanyService.log_change(
                    change_type=change['change_type'],
                    object_type=change['object_type'],
                    object_pid=change['object_pid'],
                    changes=change.get('changes')
                )
            
            # Return both the company and whether changes were made
            return company, bool(changes)
    
    @staticmethod
    def _update_company_fields(company, data):
        """
        Update basic company fields
        
        Args:
            company: Company instance
            data: Dictionary with company data
            
        Returns:
            Dictionary of changes or None if no changes
        """
        changes = {}
        
        # Fields that can be updated
        fields = ['name', 'date_of_incorporation']
        
        for field in fields:
            if field in data:
                # Create diff using our helper
                diff = CompanyService.create_field_diff(company, field, data[field])
                if diff:
                    setattr(company, field, data[field])
                    changes[field] = diff
        
        if changes:
            company.save()
            return changes
        
        return None
    
    @staticmethod
    def _update_company_taxinfo(company, taxinfo_data):
        """
        Update company tax info
        
        Args:
            company: Company instance
            taxinfo_data: List of tax info data
            
        Returns:
            List of change dictionaries
        """
        changes = []
        company_content_type = ContentType.objects.get_for_model(company)
        
        # Get existing tax info for this company
        existing_taxinfo = TaxInfo.objects.filter(
            content_type=company_content_type,
            object_id=company.pid
        )
        
        # Map existing tax info by pid for easy lookup
        existing_taxinfo_dict = {ti.pid: ti for ti in existing_taxinfo}
        
        # Track which tax info entries we've processed
        processed_pids = set()
        
        # Process each tax info in the update data
        for ti_data in taxinfo_data:
            pid = ti_data.get('pid')
            
            if pid and pid in existing_taxinfo_dict:
                # Update existing tax info
                ti = existing_taxinfo_dict[pid]
                ti_changes = {}
                
                for field in ['tin', 'country']:
                    if field in ti_data:
                        diff = CompanyService.create_field_diff(ti, field, ti_data[field])
                        if diff:
                            setattr(ti, field, ti_data[field])
                            ti_changes[field] = diff
                
                if ti_changes:
                    ti.save()
                    changes.append({
                        'change_type': 'updated',
                        'object_type': 'TaxInfo',
                        'object_pid': ti.pid,
                        'changes': ti_changes
                    })
                
                processed_pids.add(pid)
            
            elif not pid:
                # Create new tax info
                new_ti = TaxInfo.objects.create(
                    tin=ti_data.get('tin', ''),
                    country=ti_data.get('country', ''),
                    content_type=company_content_type,
                    object_id=company.pid
                )
                
                changes.append({
                    'change_type': 'added',
                    'object_type': 'TaxInfo',
                    'object_pid': new_ti.pid
                })
        
        # Remove tax info not in the update data
        for pid, ti in existing_taxinfo_dict.items():
            if pid not in processed_pids:
                ti.delete()
                changes.append({
                    'change_type': 'removed',
                    'object_type': 'TaxInfo',
                    'object_pid': pid
                })
        
        return changes
    
    @staticmethod
    def _update_directors(company, directors_data):
        """
        Update company directors and their related objects
        
        Args:
            company: Company instance
            directors_data: List of director data
            
        Returns:
            List of change dictionaries
        """
        changes = []
        
        # Get existing directors for this company
        existing_directors = company.directors.all()
        
        # Map existing directors by pid for easy lookup
        existing_directors_dict = {d.pid: d for d in existing_directors}
        
        # Track which directors we've processed
        processed_pids = set()
        
        # Process each director in the update data
        for director_data in directors_data:
            pid = director_data.get('pid')
            
            if pid and pid in existing_directors_dict:
                # Update existing director
                director = existing_directors_dict[pid]
                director_changes = {}
                
                # Update basic fields
                if 'full_name' in director_data:
                    diff = CompanyService.create_field_diff(director, 'full_name', director_data['full_name'])
                    if diff:
                        director.full_name = director_data['full_name']
                        director_changes['full_name'] = diff
                
                if director_changes:
                    director.save()
                    changes.append({
                        'change_type': 'updated',
                        'object_type': 'Director',
                        'object_pid': director.pid,
                        'changes': director_changes
                    })
                
                # Handle tax info if present
                if 'taxinfo' in director_data:
                    director_ct = ContentType.objects.get_for_model(director)
                    taxinfo_changes = CompanyService._update_related_taxinfo(
                        director, director_ct, director_data['taxinfo']
                    )
                    changes.extend(taxinfo_changes)
                
                # Handle identity files if present
                if 'identity_files' in director_data:
                    identity_file_changes = CompanyService._update_identity_files(
                        director, director_data['identity_files'], 'director_files'
                    )
                    changes.extend(identity_file_changes)
                
                processed_pids.add(pid)
            
            elif not pid:
                # Create new director
                new_director = Director.objects.create(
                    full_name=director_data.get('full_name', ''),
                    company=company
                )
                
                changes.append({
                    'change_type': 'added',
                    'object_type': 'Director',
                    'object_pid': new_director.pid
                })
                
                # Handle tax info if present
                if 'taxinfo' in director_data:
                    director_ct = ContentType.objects.get_for_model(new_director)
                    taxinfo_changes = CompanyService._update_related_taxinfo(
                        new_director, director_ct, director_data['taxinfo']
                    )
                    changes.extend(taxinfo_changes)
                
                # Handle identity files if present
                if 'identity_files' in director_data:
                    identity_file_changes = CompanyService._update_identity_files(
                        new_director, director_data['identity_files'], 'director_files'
                    )
                    changes.extend(identity_file_changes)
        
        # Remove directors not in the update data
        for pid, director in existing_directors_dict.items():
            if pid not in processed_pids:
                # Get related objects for logging before deletion
                director_ct = ContentType.objects.get_for_model(director)
                related_taxinfo = TaxInfo.objects.filter(content_type=director_ct, object_id=pid)
                related_identity_files = director.identity_files.all()
                
                # Log removal of related tax info
                for ti in related_taxinfo:
                    changes.append({
                        'change_type': 'removed',
                        'object_type': 'TaxInfo',
                        'object_pid': ti.pid
                    })
                
                # Log removal of related identity files
                for idf in related_identity_files:
                    changes.append({
                        'change_type': 'removed',
                        'object_type': 'IdentityFile',
                        'object_pid': idf.pid
                    })
                
                # Delete the director
                director.delete()
                changes.append({
                    'change_type': 'removed',
                    'object_type': 'Director',
                    'object_pid': pid
                })
        
        return changes
    
    @staticmethod
    def _update_shareholders(company, shareholders_data):
        """
        Update company shareholders and their related objects
        
        Args:
            company: Company instance
            shareholders_data: List of shareholder data
            
        Returns:
            List of change dictionaries
        """
        changes = []
        
        # Get existing shareholders for this company
        existing_shareholders = company.shareholders.all()
        
        # Map existing shareholders by pid for easy lookup
        existing_shareholders_dict = {s.pid: s for s in existing_shareholders}
        
        # Track which shareholders we've processed
        processed_pids = set()
        
        # Process each shareholder in the update data
        for shareholder_data in shareholders_data:
            pid = shareholder_data.get('pid')
            
            if pid and pid in existing_shareholders_dict:
                # Update existing shareholder
                shareholder = existing_shareholders_dict[pid]
                shareholder_changes = {}
                
                # Update basic fields
                for field in ['full_name', 'percentage']:
                    if field in shareholder_data:
                        diff = CompanyService.create_field_diff(shareholder, field, shareholder_data[field])
                        if diff:
                            setattr(shareholder, field, shareholder_data[field])
                            shareholder_changes[field] = diff
                
                if shareholder_changes:
                    shareholder.save()
                    changes.append({
                        'change_type': 'updated',
                        'object_type': 'Shareholder',
                        'object_pid': shareholder.pid,
                        'changes': shareholder_changes
                    })
                
                # Handle identity files if present
                if 'identity_files' in shareholder_data:
                    identity_file_changes = CompanyService._update_identity_files(
                        shareholder, shareholder_data['identity_files'], 'shareholder_files'
                    )
                    changes.extend(identity_file_changes)
                
                processed_pids.add(pid)
            
            elif not pid:
                # Create new shareholder
                new_shareholder = Shareholder.objects.create(
                    full_name=shareholder_data.get('full_name', ''),
                    percentage=shareholder_data.get('percentage', 0),
                    company=company
                )
                
                changes.append({
                    'change_type': 'added',
                    'object_type': 'Shareholder',
                    'object_pid': new_shareholder.pid
                })
                
                # Handle identity files if present
                if 'identity_files' in shareholder_data:
                    identity_file_changes = CompanyService._update_identity_files(
                        new_shareholder, shareholder_data['identity_files'], 'shareholder_files'
                    )
                    changes.extend(identity_file_changes)
        
        # Remove shareholders not in the update data
        for pid, shareholder in existing_shareholders_dict.items():
            if pid not in processed_pids:
                # Get related identity files for logging before deletion
                related_identity_files = shareholder.identity_files.all()
                
                # Log removal of related identity files
                for idf in related_identity_files:
                    changes.append({
                        'change_type': 'removed',
                        'object_type': 'IdentityFile',
                        'object_pid': idf.pid
                    })
                
                # Delete the shareholder
                shareholder.delete()
                changes.append({
                    'change_type': 'removed',
                    'object_type': 'Shareholder',
                    'object_pid': pid
                })
        
        return changes
    
    @staticmethod
    def _update_related_taxinfo(object_instance, content_type, taxinfo_data):
        """
        Update tax info related to an object
        
        Args:
            object_instance: The object that tax info is related to
            content_type: ContentType of the object
            taxinfo_data: List of tax info data
            
        Returns:
            List of change dictionaries
        """
        changes = []
        
        # Get existing tax info for this object
        existing_taxinfo = TaxInfo.objects.filter(
            content_type=content_type,
            object_id=object_instance.pid
        )
        
        # Map existing tax info by pid for easy lookup
        existing_taxinfo_dict = {ti.pid: ti for ti in existing_taxinfo}
        
        # Track which tax info entries we've processed
        processed_pids = set()
        
        # Process each tax info in the update data
        for ti_data in taxinfo_data:
            pid = ti_data.get('pid')
            
            if pid and pid in existing_taxinfo_dict:
                # Update existing tax info
                ti = existing_taxinfo_dict[pid]
                ti_changes = {}
                
                for field in ['tin', 'country']:
                    if field in ti_data:
                        diff = CompanyService.create_field_diff(ti, field, ti_data[field])
                        if diff:
                            setattr(ti, field, ti_data[field])
                            ti_changes[field] = diff
                
                if ti_changes:
                    ti.save()
                    changes.append({
                        'change_type': 'updated',
                        'object_type': 'TaxInfo',
                        'object_pid': ti.pid,
                        'changes': ti_changes
                    })
                
                processed_pids.add(pid)
            
            elif not pid:
                # Create new tax info
                new_ti = TaxInfo.objects.create(
                    tin=ti_data.get('tin', ''),
                    country=ti_data.get('country', ''),
                    content_type=content_type,
                    object_id=object_instance.pid
                )
                
                changes.append({
                    'change_type': 'added',
                    'object_type': 'TaxInfo',
                    'object_pid': new_ti.pid
                })
        
        # Remove tax info not in the update data
        for pid, ti in existing_taxinfo_dict.items():
            if pid not in processed_pids:
                ti.delete()
                changes.append({
                    'change_type': 'removed',
                    'object_type': 'TaxInfo',
                    'object_pid': pid
                })
        
        return changes
    
    @staticmethod
    def _update_identity_files(object_instance, identity_files_data, relation_name):
        """
        Update identity files related to an object
        
        Args:
            object_instance: The object that identity files are related to
            identity_files_data: List of identity file data
            relation_name: Name of the related_name for the relationship
            
        Returns:
            List of change dictionaries
        """
        changes = []
        
        # Get existing identity files for this object
        existing_identity_files = object_instance.identity_files.all()
        
        # Map existing identity files by pid for easy lookup
        existing_identity_files_dict = {idf.pid: idf for idf in existing_identity_files}
        
        # Track which identity files we've processed
        processed_pids = set()
        
        # Process each identity file in the update data
        for idf_data in identity_files_data:
            pid = idf_data.get('pid')
            
            if pid and pid in existing_identity_files_dict:
                # Identity file already exists, just mark as processed
                # No updates needed since we're just referencing by pid
                processed_pids.add(pid)
            
            elif pid and pid not in existing_identity_files_dict:
                # Identity file exists but not linked to this object
                try:
                    identity_file = IdentityFile.objects.get(pid=pid)
                    # Add the relationship
                    getattr(identity_file, relation_name).add(object_instance)
                    
                    changes.append({
                        'change_type': 'added',
                        'object_type': 'IdentityFile',
                        'object_pid': pid
                    })
                    
                    processed_pids.add(pid)
                except IdentityFile.DoesNotExist:
                    # File doesn't exist, create it if we have enough data
                    if 'file_name' in idf_data and 'file_path' in idf_data and 'file_type' in idf_data:
                        new_identity_file = IdentityFile.objects.create(
                            pid=pid,  # Use provided pid
                            file_name=idf_data['file_name'],
                            file_path=idf_data['file_path'],
                            file_type=idf_data['file_type']
                        )
                        # Add the relationship
                        getattr(new_identity_file, relation_name).add(object_instance)
                        
                        changes.append({
                            'change_type': 'added',
                            'object_type': 'IdentityFile',
                            'object_pid': new_identity_file.pid
                        })
                        
                        processed_pids.add(pid)
            
            elif not pid and all(k in idf_data for k in ['file_name', 'file_path', 'file_type']):
                # Create new identity file
                new_identity_file = IdentityFile.objects.create(
                    file_name=idf_data['file_name'],
                    file_path=idf_data['file_path'],
                    file_type=idf_data['file_type']
                )
                # Add the relationship
                getattr(new_identity_file, relation_name).add(object_instance)
                
                changes.append({
                    'change_type': 'added',
                    'object_type': 'IdentityFile',
                    'object_pid': new_identity_file.pid
                })
        
        # Remove identity files not in the update data
        for pid, identity_file in existing_identity_files_dict.items():
            if pid not in processed_pids:
                # Remove the relationship
                getattr(identity_file, relation_name).remove(object_instance)
                
                changes.append({
                    'change_type': 'removed',
                    'object_type': 'IdentityFile',
                    'object_pid': pid
                })
        
        return changes 
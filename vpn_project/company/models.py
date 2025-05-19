from django.db import models
import random
import json
from datetime import date
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder

def generate_pid():
    """Generate a unique 16-digit random number as pid"""
    return ''.join(str(random.randint(0, 9)) for _ in range(16))

# Custom JSON encoder to handle date objects
class DateJSONEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)

class IdentityFile(models.Model):
    """
    Model for identity files that can be linked to either Directors or Shareholders
    """
    pid = models.CharField(max_length=16, unique=True, editable=False, default=generate_pid)
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.file_name} ({self.pid})"

class TaxInfo(models.Model):
    """
    Model for tax information that can be linked to either Companies or Directors
    """
    pid = models.CharField(max_length=16, unique=True, editable=False, default=generate_pid)
    tin = models.CharField(max_length=50, verbose_name="Tax Identification Number")
    country = models.CharField(max_length=2)  # ISO Country Code (2 characters)
    
    # Generic relation to allow linking to either Company or Director
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=16)  # using pid as foreign key
    content_object = GenericForeignKey('content_type', 'object_id')
    
    def __str__(self):
        return f"TaxInfo: {self.tin} ({self.country})"

class Director(models.Model):
    """
    Model for company directors
    """
    pid = models.CharField(max_length=16, unique=True, editable=False, default=generate_pid)
    full_name = models.CharField(max_length=255)
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='directors')
    identity_files = models.ManyToManyField(IdentityFile, blank=True, related_name='director_files')
    taxinfo = GenericRelation(TaxInfo, content_type_field='content_type', object_id_field='object_id')
    
    def __str__(self):
        return f"Director: {self.full_name} ({self.pid})"

class Shareholder(models.Model):
    """
    Model for company shareholders
    """
    pid = models.CharField(max_length=16, unique=True, editable=False, default=generate_pid)
    full_name = models.CharField(max_length=255)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='shareholders')
    identity_files = models.ManyToManyField(IdentityFile, blank=True, related_name='shareholder_files')
    
    def __str__(self):
        return f"Shareholder: {self.full_name} ({self.percentage}%) ({self.pid})"

class Company(models.Model):
    """
    Model for company information
    """
    pid = models.CharField(max_length=16, unique=True, editable=False, default=generate_pid)
    name = models.CharField(max_length=255)
    date_of_incorporation = models.DateField()
    # Using 'taxinfo_set' for backward compatibility, but making it available as 'taxinfo' as well
    taxinfo = GenericRelation(TaxInfo, content_type_field='content_type', object_id_field='object_id')
    
    def __str__(self):
        return f"Company: {self.name} ({self.pid})"

class ChangeLog(models.Model):
    """
    Model for tracking changes to any of the other models
    """
    CHANGE_TYPES = (
        ('added', 'Added'),
        ('removed', 'Removed'),
        ('updated', 'Updated'),
    )
    
    OBJECT_TYPES = (
        ('Company', 'Company'),
        ('Director', 'Director'),
        ('Shareholder', 'Shareholder'),
        ('TaxInfo', 'TaxInfo'),
        ('IdentityFile', 'IdentityFile'),
    )
    
    change_type = models.CharField(max_length=10, choices=CHANGE_TYPES)
    object_type = models.CharField(max_length=20, choices=OBJECT_TYPES)
    object_pid = models.CharField(max_length=16)
    changes = models.JSONField(null=True, blank=True, encoder=DateJSONEncoder)
    timestamp = models.DateTimeField(default=timezone.now)
    
    def set_changes(self, changes_dict):
        """
        Set the changes field with a dictionary of changes
        """
        self.changes = changes_dict
    
    def get_changes(self):
        """
        Get the changes as a dictionary
        """
        return self.changes
    
    def __str__(self):
        return f"{self.change_type.capitalize()} {self.object_type} ({self.object_pid}) at {self.timestamp}"
    
    class Meta:
        ordering = ['-timestamp']

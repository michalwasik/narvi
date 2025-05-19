from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
import json
from datetime import date

from .models import Company, Director, Shareholder, TaxInfo, IdentityFile, ChangeLog

User = get_user_model()

class ModelTestCase(TestCase):
    """
    Test case for models
    """
    
    def setUp(self):
        """
        Set up test data
        """
        # Create a company
        self.company = Company.objects.create(
            name="Test Company",
            date_of_incorporation=date(2020, 1, 1)
        )
        
        # Create tax info for the company
        company_content_type = ContentType.objects.get_for_model(self.company)
        self.tax_info = TaxInfo.objects.create(
            tin="COMPANYTIN123",
            country="US",
            content_type=company_content_type,
            object_id=self.company.pid
        )
        
        # Create a director
        self.director = Director.objects.create(
            full_name="Jane Smith",
            company=self.company
        )
        
        # Create tax info for the director
        director_content_type = ContentType.objects.get_for_model(self.director)
        self.director_tax_info = TaxInfo.objects.create(
            tin="123456789",
            country="US",
            content_type=director_content_type,
            object_id=self.director.pid
        )
        
        # Create identity files for the director
        self.director_identity_file = IdentityFile.objects.create(
            file_name="passport.jpg",
            file_path="/uploads/passport.jpg",
            file_type="image/jpeg"
        )
        self.director.identity_files.add(self.director_identity_file)
        
        # Create a shareholder
        self.shareholder = Shareholder.objects.create(
            full_name="Alex Johnson",
            percentage=25.5,
            company=self.company
        )
        
        # Create identity files for the shareholder
        self.shareholder_identity_file = IdentityFile.objects.create(
            file_name="id_card.jpg",
            file_path="/uploads/id_card.jpg",
            file_type="image/jpeg"
        )
        self.shareholder.identity_files.add(self.shareholder_identity_file)
    
    def test_company_creation(self):
        """
        Test company creation with a 16-digit pid
        """
        self.assertEqual(self.company.name, "Test Company")
        self.assertEqual(len(self.company.pid), 16)
        self.assertTrue(self.company.pid.isdigit())
    
    def test_tax_info_creation(self):
        """
        Test tax info creation and linking to company
        """
        self.assertEqual(self.tax_info.tin, "COMPANYTIN123")
        self.assertEqual(self.tax_info.country, "US")
        self.assertEqual(len(self.tax_info.pid), 16)
        
        # Check generic relation
        company_content_type = ContentType.objects.get_for_model(self.company)
        tax_info = TaxInfo.objects.filter(
            content_type=company_content_type,
            object_id=self.company.pid
        ).first()
        self.assertEqual(tax_info, self.tax_info)
    
    def test_director_creation(self):
        """
        Test director creation and linking to company
        """
        self.assertEqual(self.director.full_name, "Jane Smith")
        self.assertEqual(len(self.director.pid), 16)
        self.assertEqual(self.director.company, self.company)
        
        # Check tax info
        director_content_type = ContentType.objects.get_for_model(self.director)
        tax_info = TaxInfo.objects.filter(
            content_type=director_content_type,
            object_id=self.director.pid
        ).first()
        self.assertEqual(tax_info, self.director_tax_info)
        
        # Check identity files
        self.assertEqual(self.director.identity_files.count(), 1)
        self.assertIn(self.director_identity_file, self.director.identity_files.all())
    
    def test_shareholder_creation(self):
        """
        Test shareholder creation and linking to company
        """
        self.assertEqual(self.shareholder.full_name, "Alex Johnson")
        self.assertEqual(self.shareholder.percentage, 25.5)
        self.assertEqual(len(self.shareholder.pid), 16)
        self.assertEqual(self.shareholder.company, self.company)
        
        # Check identity files
        self.assertEqual(self.shareholder.identity_files.count(), 1)
        self.assertIn(self.shareholder_identity_file, self.shareholder.identity_files.all())

class CompanyAPITestCase(APITestCase):
    """
    Test case for company API
    """
    
    def setUp(self):
        """
        Set up test data
        """
        # Create a user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        
        # Create a client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create a company
        self.company = Company.objects.create(
            name="Acme Inc.",
            date_of_incorporation=date(2020, 1, 15)
        )
        
        # Create tax info for the company
        company_content_type = ContentType.objects.get_for_model(self.company)
        self.tax_info = TaxInfo.objects.create(
            tin="COMPANYTIN123",
            country="US",
            content_type=company_content_type,
            object_id=self.company.pid
        )
        
        # Create a director
        self.director = Director.objects.create(
            full_name="Jane Smith",
            company=self.company
        )
        
        # Create tax info for the director
        director_content_type = ContentType.objects.get_for_model(self.director)
        self.director_tax_info = TaxInfo.objects.create(
            tin="123456789",
            country="US",
            content_type=director_content_type,
            object_id=self.director.pid
        )
        
        # Create identity files for the director
        self.director_identity_file1 = IdentityFile.objects.create(
            file_name="passport.jpg",
            file_path="/uploads/passport.jpg",
            file_type="image/jpeg"
        )
        self.director_identity_file2 = IdentityFile.objects.create(
            file_name="drivers_license.jpg",
            file_path="/uploads/drivers_license.jpg",
            file_type="image/jpeg"
        )
        self.director.identity_files.add(self.director_identity_file1)
        self.director.identity_files.add(self.director_identity_file2)
        
        # Create a shareholder
        self.shareholder = Shareholder.objects.create(
            full_name="Alex Johnson",
            percentage=25.5,
            company=self.company
        )
        
        # Create identity files for the shareholder
        self.shareholder_identity_file = IdentityFile.objects.create(
            file_name="id_card.jpg",
            file_path="/uploads/id_card.jpg",
            file_type="image/jpeg"
        )
        self.shareholder.identity_files.add(self.shareholder_identity_file)
        
        # URL for company detail
        self.url = reverse('company:company_detail', kwargs={'pid': self.company.pid})
        
        # URL for company changelog
        self.changelog_url = reverse('company:company_changelog', kwargs={'pid': self.company.pid})
    
    def test_get_company(self):
        """
        Test retrieving a company
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check company data
        data = response.data
        self.assertEqual(data['name'], self.company.name)
        self.assertEqual(data['pid'], self.company.pid)
        
        # Verify taxinfo is included
        self.assertIn('taxinfo', data)
        self.assertEqual(len(data['taxinfo']), 1)
        self.assertEqual(data['taxinfo'][0]['tin'], self.tax_info.tin)
        
        # Check if it includes directors
        self.assertEqual(len(data['directors']), 1)
        self.assertEqual(data['directors'][0]['full_name'], self.director.full_name)
        
        # Check if it includes shareholders
        self.assertEqual(len(data['shareholders']), 1)
        self.assertEqual(data['shareholders'][0]['full_name'], self.shareholder.full_name)
    
    def test_patch_company_name(self):
        """
        Test updating the company name
        """
        data = {'name': 'Updated Company Name'}
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if company name was updated
        self.company.refresh_from_db()
        self.assertEqual(self.company.name, 'Updated Company Name')
        
        # Check if changelog was created
        changelog = ChangeLog.objects.filter(
            change_type='updated',
            object_type='Company',
            object_pid=self.company.pid
        ).first()
        self.assertIsNotNone(changelog)
        self.assertEqual(changelog.changes['name']['old'], 'Acme Inc.')
        self.assertEqual(changelog.changes['name']['new'], 'Updated Company Name')
    
    def test_patch_company_complex_update(self):
        """
        Test updating multiple aspects of a company
        """
        data = {
            'name': 'New Company Name',
            'taxinfo': [
                {
                    'pid': self.tax_info.pid,
                    'tin': 'NEWTAXID',
                    'country': 'CA'
                }
            ],
            'directors': [
                {
                    'pid': self.director.pid,
                    'full_name': 'New Director Name'
                }
            ],
            'shareholders': [
                {
                    'pid': self.shareholder.pid,
                    'percentage': 30
                }
            ]
        }
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if company was updated
        self.company.refresh_from_db()
        self.assertEqual(self.company.name, 'New Company Name')
        
        # Check if tax info was updated
        self.tax_info.refresh_from_db()
        self.assertEqual(self.tax_info.tin, 'NEWTAXID')
        self.assertEqual(self.tax_info.country, 'CA')
        
        # Check if director was updated
        self.director.refresh_from_db()
        self.assertEqual(self.director.full_name, 'New Director Name')
        
        # Check if shareholder was updated
        self.shareholder.refresh_from_db()
        self.assertEqual(self.shareholder.percentage, 30)
        
        # Check if changelogs were created
        company_changelog = ChangeLog.objects.filter(
            change_type='updated',
            object_type='Company',
            object_pid=self.company.pid
        ).first()
        self.assertIsNotNone(company_changelog)
        
        tax_info_changelog = ChangeLog.objects.filter(
            change_type='updated',
            object_type='TaxInfo',
            object_pid=self.tax_info.pid
        ).first()
        self.assertIsNotNone(tax_info_changelog)
        
        director_changelog = ChangeLog.objects.filter(
            change_type='updated',
            object_type='Director',
            object_pid=self.director.pid
        ).first()
        self.assertIsNotNone(director_changelog)
        
        shareholder_changelog = ChangeLog.objects.filter(
            change_type='updated',
            object_type='Shareholder',
            object_pid=self.shareholder.pid
        ).first()
        self.assertIsNotNone(shareholder_changelog)
    
    def test_add_new_director(self):
        """
        Test adding a new director
        """
        data = {
            'directors': [
                {
                    'pid': self.director.pid,  # Keep existing director
                    'full_name': self.director.full_name
                },
                {
                    'full_name': 'New Director'  # Add new director
                }
            ]
        }
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if new director was added
        self.assertEqual(self.company.directors.count(), 2)
        
        # Check if new director has the correct name
        new_director = Director.objects.filter(company=self.company).exclude(pid=self.director.pid).first()
        self.assertEqual(new_director.full_name, 'New Director')
        
        # Check if changelog was created
        director_changelog = ChangeLog.objects.filter(
            change_type='added',
            object_type='Director',
            object_pid=new_director.pid
        ).first()
        self.assertIsNotNone(director_changelog)
    
    def test_remove_director(self):
        """
        Test removing a director
        """
        data = {
            'directors': []  # Empty list to remove all directors
        }
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if director was removed
        self.assertEqual(self.company.directors.count(), 0)
        
        # Check if changelog was created
        director_changelog = ChangeLog.objects.filter(
            change_type='removed',
            object_type='Director',
            object_pid=self.director.pid
        ).first()
        self.assertIsNotNone(director_changelog)
    
    def test_get_changelog(self):
        """
        Test retrieving the changelog for a company
        """
        # First make a change to create a changelog entry
        data = {'name': 'Updated Company Name'}
        self.client.patch(self.url, data, format='json')
        
        # Get changelog
        response = self.client.get(self.changelog_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if changelog entries are returned
        self.assertGreater(len(response.data), 0)
        
        # Check the first entry
        changelog = response.data[0]
        self.assertEqual(changelog['change_type'], 'updated')
        self.assertEqual(changelog['object_type'], 'Company')
        self.assertEqual(changelog['object_pid'], self.company.pid)
        self.assertIn('name', changelog['changes'])
    
    def test_create_company(self):
        """
        Test creating a new company with nested objects
        """
        url = reverse('company:company_create')
        data = {
            'name': 'New Test Company',
            'date_of_incorporation': '2021-01-01',
            'directors': [
                {
                    'full_name': 'New Director'
                }
            ],
            'shareholders': [
                {
                    'full_name': 'New Shareholder',
                    'percentage': 75.5
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check if company was created
        company_pid = response.data['pid']
        company = Company.objects.get(pid=company_pid)
        self.assertEqual(company.name, 'New Test Company')
        
        # Check if director was created
        director = company.directors.first()
        self.assertIsNotNone(director)
        self.assertEqual(director.full_name, 'New Director')
        
        # Check if shareholder was created
        shareholder = company.shareholders.first()
        self.assertIsNotNone(shareholder)
        self.assertEqual(shareholder.full_name, 'New Shareholder')
        self.assertEqual(shareholder.percentage, 75.5)
        
        # Check if changelog was created
        changelog = ChangeLog.objects.filter(
            change_type='added',
            object_type='Company',
            object_pid=company.pid
        ).first()
        self.assertIsNotNone(changelog)

    def test_patch_company_no_changes(self):
        """
        Test updating a company with no actual changes
        Should return a message indicating no changes were detected
        """
        # Get current company data
        current_name = self.company.name
        
        # Send a PATCH request with the same data
        data = {'name': current_name}
        response = self.client.patch(self.url, data, format='json')
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'No changes detected')
        
        # Verify no changelog was created
        changelog_count = ChangeLog.objects.filter(
            change_type='updated',
            object_type='Company',
            object_pid=self.company.pid
        ).count()
        self.assertEqual(changelog_count, 0)

    def test_detailed_changelog(self):
        """
        Test that changes are properly logged with field-level diffs
        """
        # Update various parts of the company to generate detailed changelogs
        data = {
            'name': 'Enhanced Company Name',
            'directors': [
                {
                    'pid': self.director.pid,
                    'full_name': 'Jane Updated Smith'
                }
            ],
            'shareholders': [
                {
                    'pid': self.shareholder.pid,
                    'percentage': 30.25
                }
            ]
        }
        
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Get changelog
        response = self.client.get(self.changelog_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should have at least 3 changelog entries (company, director, shareholder updates)
        self.assertGreaterEqual(len(response.data), 3)
        
        # Find each type of changelog entry
        company_log = None
        director_log = None
        shareholder_log = None
        
        for entry in response.data:
            if entry['object_type'] == 'Company' and entry['object_pid'] == self.company.pid:
                company_log = entry
            elif entry['object_type'] == 'Director' and entry['object_pid'] == self.director.pid:
                director_log = entry
            elif entry['object_type'] == 'Shareholder' and entry['object_pid'] == self.shareholder.pid:
                shareholder_log = entry
        
        # Verify company change details
        self.assertIsNotNone(company_log)
        self.assertEqual(company_log['change_type'], 'updated')
        self.assertIn('name', company_log['changes'])
        self.assertEqual(company_log['changes']['name']['old'], 'Acme Inc.')
        self.assertEqual(company_log['changes']['name']['new'], 'Enhanced Company Name')
        
        # Verify director change details
        self.assertIsNotNone(director_log)
        self.assertEqual(director_log['change_type'], 'updated')
        self.assertIn('full_name', director_log['changes'])
        self.assertEqual(director_log['changes']['full_name']['old'], 'Jane Smith')
        self.assertEqual(director_log['changes']['full_name']['new'], 'Jane Updated Smith')
        
        # Verify shareholder change details
        self.assertIsNotNone(shareholder_log)
        self.assertEqual(shareholder_log['change_type'], 'updated')
        self.assertIn('percentage', shareholder_log['changes'])
        self.assertEqual(float(shareholder_log['changes']['percentage']['old']), 25.5)
        self.assertEqual(float(shareholder_log['changes']['percentage']['new']), 30.25)
        
        # Verify timestamp format and existence
        for entry in [company_log, director_log, shareholder_log]:
            self.assertIn('timestamp', entry)
            self.assertIsNotNone(entry['timestamp'])

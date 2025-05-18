from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock, call

from authserver.management_interface import OpenVPNManagementInterface

User = get_user_model()

class OpenVPNManagementInterfaceTest(TestCase):
    """
    Tests for the OpenVPN Management Interface
    """
    
    def setUp(self):
        """
        Set up for the tests
        """
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        
        # Create a mock socket
        self.mock_socket = MagicMock()
        self.mock_socket.recv.return_value = b"Welcome to OpenVPN Management Interface\r\n"
        
    @patch('socket.socket')
    def test_connect(self, mock_socket_class):
        """
        Test connecting to the OpenVPN Management Interface
        """
        # Set up the mock
        mock_socket_instance = MagicMock()
        mock_socket_class.return_value = mock_socket_instance
        mock_socket_instance.recv.return_value = b"Welcome to OpenVPN Management Interface\r\n"
        
        # Create the interface
        interface = OpenVPNManagementInterface(host='127.0.0.1', port=7505)
        
        # Connect
        result = interface.connect()
        
        # Assertions
        self.assertTrue(result)
        mock_socket_instance.connect.assert_called_once_with(('127.0.0.1', 7505))
        # We're not testing the exact number of recv calls since it may depend on implementation details
        self.assertTrue(mock_socket_instance.recv.called)
        
    @patch('socket.socket')
    def test_send_command(self, mock_socket_class):
        """
        Test sending a command to the OpenVPN Management Interface
        """
        # Set up the mock
        mock_socket_instance = MagicMock()
        mock_socket_class.return_value = mock_socket_instance
        mock_socket_instance.recv.return_value = b"SUCCESS: command executed\r\n"
        
        # Create the interface
        interface = OpenVPNManagementInterface(host='127.0.0.1', port=7505)
        interface.socket = mock_socket_instance
        
        # Send a command
        response = interface.send_command("test-command")
        
        # Assertions
        self.assertEqual(response, "SUCCESS: command executed\r\n")
        mock_socket_instance.sendall.assert_called_once_with(b"test-command\n")
        
    def test_process_auth_request_success(self):
        """
        Test processing an authentication request with valid credentials
        """
        # Create the interface
        interface = OpenVPNManagementInterface()
        
        # Mock the necessary methods
        interface._allow_auth = MagicMock()
        interface._deny_auth = MagicMock()
        
        # Mock the authenticate function directly in the method
        with patch('authserver.management_interface.authenticate') as mock_authenticate:
            # Set up the mock
            mock_authenticate.return_value = self.user
            
            # Process an auth request
            interface._process_auth_request('testuser', 'testpassword123', '1', '1')
            
            # Assertions
            mock_authenticate.assert_called_once_with(username='testuser', password='testpassword123')
            interface._allow_auth.assert_called_once_with('1', '1')
            interface._deny_auth.assert_not_called()
        
    def test_process_auth_request_failure(self):
        """
        Test processing an authentication request with invalid credentials
        """
        # Create the interface
        interface = OpenVPNManagementInterface()
        
        # Mock the necessary methods
        interface._allow_auth = MagicMock()
        interface._deny_auth = MagicMock()
        
        # Mock the authenticate function directly in the method
        with patch('authserver.management_interface.authenticate') as mock_authenticate:
            # Set up the mock
            mock_authenticate.return_value = None
            
            # Process an auth request
            interface._process_auth_request('testuser', 'wrongpassword', '1', '1')
            
            # Assertions
            mock_authenticate.assert_called_once_with(username='testuser', password='wrongpassword')
            interface._deny_auth.assert_called_once_with('1', '1')
            interface._allow_auth.assert_not_called() 
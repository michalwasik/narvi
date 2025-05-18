import socket
import threading
import logging
import re
import time
from django.conf import settings
from django.contrib.auth import authenticate
from .models import CustomUser, TwoFactorCode
from .services import TwoFactorService

logger = logging.getLogger(__name__)

class OpenVPNManagementInterface:
    """
    Service class that connects to the OpenVPN Management Interface,
    listens for authentication requests, and validates them against
    the Django user database with 2FA support.
    """
    
    def __init__(self, host='127.0.0.1', port=7505):
        """
        Initialize the OpenVPN Management Interface connection
        
        Args:
            host (str): The OpenVPN Management Interface host
            port (int): The OpenVPN Management Interface port
        """
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.thread = None
        self.connect_retries = 5
        self.retry_interval = 5  # seconds
        
        # Patterns for parsing OpenVPN Management Interface output
        self.auth_request_pattern = re.compile(r'>CLIENT:CONNECT,(\d+),(\d+)')
        self.username_pattern = re.compile(r'>CLIENT:ENV,username=(.+)')
        self.password_pattern = re.compile(r'>CLIENT:ENV,password=(.+)')
        self.end_pattern = re.compile(r'>CLIENT:ENV,END')
        
    def connect(self):
        """
        Connect to the OpenVPN Management Interface
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        retry_count = 0
        
        while retry_count < self.connect_retries:
            try:
                logger.info(f"Connecting to OpenVPN Management Interface at {self.host}:{self.port}")
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.host, self.port))
                
                # Read welcome message
                data = self.socket.recv(4096).decode('utf-8')
                logger.info(f"Connected to OpenVPN Management Interface: {data.strip()}")
                
                # Enable client authentication handling
                self.send_command("auth-retry none")
                
                return True
            except socket.error as e:
                logger.error(f"Failed to connect to OpenVPN Management Interface: {e}")
                retry_count += 1
                
                if retry_count < self.connect_retries:
                    logger.info(f"Retrying in {self.retry_interval} seconds...")
                    time.sleep(self.retry_interval)
                else:
                    logger.error("Maximum retries reached. Could not connect to OpenVPN Management Interface.")
                    return False
    
    def send_command(self, command):
        """
        Send a command to the OpenVPN Management Interface
        
        Args:
            command (str): The command to send
            
        Returns:
            str: The response from the OpenVPN Management Interface
        """
        if not self.socket:
            logger.error("Cannot send command: Not connected to OpenVPN Management Interface")
            return None
            
        try:
            self.socket.sendall(f"{command}\n".encode('utf-8'))
            response = self.socket.recv(4096).decode('utf-8')
            return response
        except socket.error as e:
            logger.error(f"Error sending command to OpenVPN Management Interface: {e}")
            return None
    
    def start(self):
        """
        Start the OpenVPN Management Interface service in a separate thread
        """
        if self.running:
            logger.warning("OpenVPN Management Interface service is already running")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        logger.info("OpenVPN Management Interface service started")
    
    def stop(self):
        """
        Stop the OpenVPN Management Interface service
        """
        if not self.running:
            logger.warning("OpenVPN Management Interface service is not running")
            return
            
        self.running = False
        
        if self.socket:
            try:
                self.socket.close()
            except socket.error as e:
                logger.error(f"Error closing socket: {e}")
                
        if self.thread:
            self.thread.join(timeout=5.0)
            if self.thread.is_alive():
                logger.warning("OpenVPN Management Interface service thread did not terminate properly")
            else:
                logger.info("OpenVPN Management Interface service stopped")
    
    def _run(self):
        """
        Main service loop that listens for auth requests
        """
        if not self.connect():
            self.running = False
            return
            
        current_cid = None
        current_kid = None
        username = None
        password = None
        collecting_env = False
        
        while self.running:
            try:
                # Read data from socket
                data = self.socket.recv(4096).decode('utf-8')
                
                if not data:
                    logger.error("Connection to OpenVPN Management Interface closed")
                    if not self.connect():
                        break
                    continue
                
                # Process each line in the data
                for line in data.splitlines():
                    logger.debug(f"Received: {line}")
                    
                    # Check for auth request
                    auth_match = self.auth_request_pattern.match(line)
                    if auth_match:
                        # New auth request
                        current_cid = auth_match.group(1)
                        current_kid = auth_match.group(2)
                        username = None
                        password = None
                        collecting_env = True
                        logger.info(f"New auth request: cid={current_cid}, kid={current_kid}")
                        continue
                    
                    # If we're collecting environment variables for an auth request
                    if collecting_env:
                        # Check for username
                        username_match = self.username_pattern.match(line)
                        if username_match:
                            username = username_match.group(1)
                            logger.info(f"Username: {username}")
                            continue
                        
                        # Check for password
                        password_match = self.password_pattern.match(line)
                        if password_match:
                            password = password_match.group(1)
                            logger.info("Password received")
                            continue
                        
                        # Check for end of environment variables
                        end_match = self.end_pattern.match(line)
                        if end_match:
                            collecting_env = False
                            
                            # Process auth request
                            if username and password and current_cid and current_kid:
                                self._process_auth_request(username, password, current_cid, current_kid)
                            else:
                                logger.warning("Incomplete auth request")
                                self._deny_auth(current_cid, current_kid)
                            
                            # Reset state
                            current_cid = None
                            current_kid = None
                            username = None
                            password = None
                            continue
                
            except socket.error as e:
                logger.error(f"Socket error: {e}")
                if not self.connect():
                    break
    
    def _process_auth_request(self, username, password, cid, kid):
        """
        Process an authentication request
        
        Format of password field from OpenVPN:
        - For no 2FA: regular password
        - For 2FA: password;verification_code
        
        Args:
            username (str): The username
            password (str): The password or password;verification_code
            cid (str): The client ID
            kid (str): The key ID
        """
        logger.info(f"Processing auth request for user {username}")
        
        # Check if password contains 2FA code
        if ';' in password:
            # Extract password and 2FA code
            password_part, code_part = password.split(';', 1)
            
            # First, authenticate with username and password
            user = authenticate(username=username, password=password_part)
            
            if not user:
                logger.warning(f"Username/password authentication failed for {username}")
                self._deny_auth(cid, kid)
                return
            
            # Check if 2FA is enabled for this user
            if user.two_fa_method == 'NONE':
                logger.info(f"User {username} does not have 2FA enabled but provided a 2FA code")
                self._allow_auth(cid, kid)
                return
                
            # Verify 2FA code
            if user.two_fa_method == 'SMS':
                # Verify SMS code
                verified = False
                try:
                    latest_code = TwoFactorCode.objects.filter(
                        user=user,
                        is_used=False
                    ).latest('created_at')
                    
                    if latest_code.is_valid and latest_code.code == code_part:
                        latest_code.is_used = True
                        latest_code.save()
                        verified = True
                except TwoFactorCode.DoesNotExist:
                    pass
            
            elif user.two_fa_method == 'GOOGLE_AUTH':
                # Verify Google Authenticator code
                verified = TwoFactorService.verify_totp(user.two_fa_secret, code_part)
            
            else:
                logger.warning(f"Unknown 2FA method for user {username}: {user.two_fa_method}")
                verified = False
            
            if verified:
                logger.info(f"2FA successful for user {username}")
                self._allow_auth(cid, kid)
            else:
                logger.warning(f"2FA failed for user {username}")
                self._deny_auth(cid, kid)
        
        else:
            # No 2FA code provided, just check username and password
            user = authenticate(username=username, password=password)
            
            if not user:
                logger.warning(f"Username/password authentication failed for {username}")
                self._deny_auth(cid, kid)
                return
            
            # Check if 2FA is required for this user
            if user.two_fa_method != 'NONE':
                logger.warning(f"2FA required for user {username} but no code provided")
                self._deny_auth(cid, kid)
            else:
                logger.info(f"Authentication successful for user {username}")
                self._allow_auth(cid, kid)
    
    def _allow_auth(self, cid, kid):
        """
        Allow authentication for a client
        
        Args:
            cid (str): The client ID
            kid (str): The key ID
        """
        command = f"client-auth-nt {cid} {kid}"
        response = self.send_command(command)
        logger.info(f"Allowed auth for client {cid}, response: {response}")
    
    def _deny_auth(self, cid, kid):
        """
        Deny authentication for a client
        
        Args:
            cid (str): The client ID
            kid (str): The key ID
        """
        command = f"client-deny {cid} {kid} \"Authentication failed\""
        response = self.send_command(command)
        logger.info(f"Denied auth for client {cid}, response: {response}")


# Singleton instance of the OpenVPN Management Interface
management_interface = None

def get_management_interface():
    """
    Get or create the OpenVPN Management Interface singleton
    
    Returns:
        OpenVPNManagementInterface: The management interface instance
    """
    global management_interface
    
    if management_interface is None:
        # Get the configuration from settings
        host = getattr(settings, 'OPENVPN_MANAGEMENT_HOST', '127.0.0.1')
        port = getattr(settings, 'OPENVPN_MANAGEMENT_PORT', 7505)
        
        management_interface = OpenVPNManagementInterface(host=host, port=port)
    
    return management_interface

def start_management_interface():
    """
    Start the OpenVPN Management Interface service
    """
    interface = get_management_interface()
    interface.start()

def stop_management_interface():
    """
    Stop the OpenVPN Management Interface service
    """
    global management_interface
    
    if management_interface:
        management_interface.stop()
        management_interface = None 
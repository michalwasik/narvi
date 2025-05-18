#!/usr/bin/env python3
"""
Mock OpenVPN Management Interface server for testing the authentication service.
This mimics the behavior of an actual OpenVPN server's management interface.

Usage:
  python mock_openvpn_server.py [port]
"""

import socket
import sys
import threading
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("MockOpenVPNServer")

class MockOpenVPNServer:
    """
    A mock OpenVPN Management Interface server for testing.
    """
    def __init__(self, host='127.0.0.1', port=7505):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.clients = []
        
    def start(self):
        """
        Start the mock server
        """
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            logger.info(f"Mock OpenVPN Management Interface server listening on {self.host}:{self.port}")
            
            self.running = True
            
            # Start accepting clients
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    logger.info(f"Accepted connection from {client_address}")
                    
                    # Welcome message
                    client_socket.sendall(b"OpenVPN Management Interface Mock [version 1.0]\r\n")
                    
                    # Start a thread to handle this client
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                    self.clients.append({
                        'socket': client_socket,
                        'address': client_address,
                        'thread': client_thread
                    })
                    
                except socket.error as e:
                    if self.running:
                        logger.error(f"Socket error: {e}")
                    break
                    
        except socket.error as e:
            logger.error(f"Failed to start server: {e}")
            return False
            
        return True
    
    def stop(self):
        """
        Stop the mock server
        """
        self.running = False
        
        # Close all client connections
        for client in self.clients:
            try:
                client['socket'].close()
            except socket.error:
                pass
        
        # Close the server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except socket.error:
                pass
            
        logger.info("Mock OpenVPN Management Interface server stopped")
    
    def handle_client(self, client_socket, client_address):
        """
        Handle a client connection
        """
        try:
            while self.running:
                data = client_socket.recv(4096)
                
                if not data:
                    logger.info(f"Client {client_address} disconnected")
                    break
                
                command = data.decode('utf-8').strip()
                logger.info(f"Received command from {client_address}: {command}")
                
                if command == "auth-retry none":
                    client_socket.sendall(b"SUCCESS: auth-retry set to none\r\n")
                
                # Simulate a client connection request every 10 seconds
                # This is just for demo purposes - in a real server, this would be triggered by OpenVPN events
                threading.Thread(
                    target=self.simulate_client_auth_request,
                    args=(client_socket,)
                ).start()
                
        except socket.error as e:
            logger.error(f"Error handling client {client_address}: {e}")
        finally:
            try:
                client_socket.close()
            except socket.error:
                pass
    
    def simulate_client_auth_request(self, client_socket):
        """
        Simulate a client authentication request
        """
        try:
            # Wait a bit before sending the simulated request
            time.sleep(10)
            
            # Send client connect notification
            client_socket.sendall(b">CLIENT:CONNECT,1,1\r\n")
            
            # Send client environment
            client_socket.sendall(b">CLIENT:ENV,username=testuser\r\n")
            client_socket.sendall(b">CLIENT:ENV,password=testpassword123;123456\r\n")
            client_socket.sendall(b">CLIENT:ENV,END\r\n")
            
            # Wait for response (client-auth or client-deny)
            data = client_socket.recv(4096)
            response = data.decode('utf-8').strip()
            
            if "client-auth-nt 1 1" in response:
                logger.info("Authentication successful")
            elif "client-deny 1 1" in response:
                logger.info("Authentication failed")
            else:
                logger.warning(f"Unknown response: {response}")
                
        except socket.error as e:
            logger.error(f"Error simulating client auth request: {e}")

def main():
    """
    Main function
    """
    port = 7505
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            logger.error(f"Invalid port: {sys.argv[1]}")
            return
    
    server = MockOpenVPNServer(port=port)
    
    try:
        if server.start():
            # Keep the program running
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        server.stop()

if __name__ == "__main__":
    main() 
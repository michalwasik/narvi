from django.apps import AppConfig


class AuthserverConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authserver'
    
    def ready(self):
        """
        Start the OpenVPN Management Interface when Django starts.
        This method is called once when Django starts.
        """
        # Import is inside method to avoid AppRegistryNotReady exception
        from .management_interface import start_management_interface
        import threading
        import os
        
        # Only start in the main process, not in management commands or other subprocesses
        if os.environ.get('RUN_MAIN', None) != 'true':
            # Start the management interface in a separate thread
            threading.Thread(target=start_management_interface).start()
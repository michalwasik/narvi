from django.core.management.base import BaseCommand, CommandError
from authserver.management_interface import get_management_interface, start_management_interface, stop_management_interface
import time
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Start or stop the OpenVPN Management Interface service'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            type=str,
            choices=['start', 'stop', 'status'],
            help='Action to perform: start, stop, or status'
        )
        
        parser.add_argument(
            '--daemonize',
            action='store_true',
            help='Run in daemon mode (start only)'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'start':
            try:
                self.stdout.write(self.style.SUCCESS('Starting OpenVPN Management Interface service...'))
                
                if options['daemonize']:
                    # Start in daemon mode
                    import threading
                    thread = threading.Thread(target=start_management_interface)
                    thread.daemon = True
                    thread.start()
                    self.stdout.write(self.style.SUCCESS('Service started in daemon mode'))
                else:
                    # Start in foreground
                    try:
                        self.stdout.write(self.style.SUCCESS('Service started. Press Ctrl+C to stop.'))
                        interface = get_management_interface()
                        interface.start()
                        
                        # Keep the command running
                        while True:
                            time.sleep(1)
                    except KeyboardInterrupt:
                        self.stdout.write(self.style.WARNING('Stopping service...'))
                        stop_management_interface()
                        self.stdout.write(self.style.SUCCESS('Service stopped'))
            except Exception as e:
                raise CommandError(f'Error starting service: {e}')
                
        elif action == 'stop':
            try:
                self.stdout.write(self.style.SUCCESS('Stopping OpenVPN Management Interface service...'))
                stop_management_interface()
                self.stdout.write(self.style.SUCCESS('Service stopped'))
            except Exception as e:
                raise CommandError(f'Error stopping service: {e}')
                
        elif action == 'status':
            interface = get_management_interface()
            if interface.running:
                self.stdout.write(self.style.SUCCESS(f'Service is running on {interface.host}:{interface.port}'))
            else:
                self.stdout.write(self.style.WARNING('Service is not running')) 
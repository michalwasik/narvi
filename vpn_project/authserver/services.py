import pyotp
from django.conf import settings
import qrcode
import base64
import io
from .models import TwoFactorCode, CustomUser
import logging

logger = logging.getLogger(__name__)

class TwoFactorService:
    """
    Service class for handling two-factor authentication operations
    """
    
    @staticmethod
    def generate_totp_secret():
        """
        Generate a new TOTP secret key for Google Authenticator
        """
        return pyotp.random_base32()
    
    @staticmethod
    def verify_totp(secret, code):
        """
        Verify a TOTP code against a secret
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(code)
    
    @staticmethod
    def get_totp_uri(user, secret=None):
        """
        Get the TOTP URI for QR code generation
        """
        if not secret:
            secret = user.two_fa_secret
            
        if not secret:
            return None
            
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=user.username,
            issuer_name=settings.APP_NAME if hasattr(settings, 'APP_NAME') else 'VPN Auth Server'
        )
    
    @staticmethod
    def generate_qr_code(uri):
        """
        Generate a QR code for a TOTP URI
        """
        if not uri:
            return None
            
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert image to base64 string
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    @staticmethod
    def setup_google_auth(user):
        """
        Setup Google Authenticator for a user
        Returns the secret and QR code image
        """
        # Generate a new secret
        secret = TwoFactorService.generate_totp_secret()
        
        # Save the secret to user
        user.two_fa_secret = secret
        user.two_fa_method = CustomUser.TwoFactorMethod.GOOGLE_AUTH
        user.save()
        
        # Generate QR code
        uri = TwoFactorService.get_totp_uri(user, secret)
        qr_code = TwoFactorService.generate_qr_code(uri)
        
        return {
            'secret': secret,
            'qr_code': qr_code
        }
    
    @staticmethod
    def send_sms_code(user, code=None):
        """
        Send an SMS with a verification code to a user
        Returns the code for testing purposes
        """
        if not user.phone_number:
            raise ValueError("User has no phone number")
            
        if code is None:
            # Generate a new code
            verification_code_obj = TwoFactorCode.generate_code(user)
            code = verification_code_obj.code
        
        # In a real application, you would send an SMS here
        # For example, using Twilio:
        # 
        # from twilio.rest import Client
        # 
        # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        # message = client.messages.create(
        #     body=f"Your verification code is: {code}",
        #     from_=settings.TWILIO_PHONE_NUMBER,
        #     to=user.phone_number
        # )
        
        # For now, we just log the code
        logger.info(f"SMS verification code for {user.username}: {code}")
        
        # Print to console for testing purposes
        print(f"SMS verification code for {user.username}: {code}")
        
        return code 
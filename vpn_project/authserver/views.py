from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django.contrib.auth import authenticate

from .models import CustomUser, TwoFactorCode, TemporaryToken
from .serializers import UserSerializer, UserCreateSerializer
from .services import TwoFactorService

import pyotp  # For Google Authenticator

# Create your views here.

@api_view(['GET'])
@permission_classes([AllowAny])
def api_overview(request):
    """
    Overview of available auth API endpoints
    """
    api_urls = {
        'Register': '/register/',
        'Login - Step 1': '/login/step1/',
        'Login - Step 2 (2FA)': '/login/step2/',
        'User Profile': '/profile/',
        'Setup Google Auth': '/setup-google-auth/',
        'Setup SMS Auth': '/setup-sms-auth/',
    }
    return Response(api_urls)

class RegisterView(generics.CreateAPIView):
    """
    Register a new user
    """
    queryset = CustomUser.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Get or update user profile
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

class LoginStep1View(APIView):
    """
    Step 1 of the two-step login process.
    Validates username and password, then:
    - If 2FA is disabled, returns a permanent token
    - If 2FA is enabled, returns a temporary token and prepares for 2FA verification
    """
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        # Get username and password
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({
                'error': 'Please provide both username and password'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Authenticate user with username and password
        user = authenticate(username=username, password=password)
        
        if not user:
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Check if 2FA is enabled for this user
        if user.two_fa_method == 'NONE':
            # No 2FA, create and return permanent token directly
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'access_token': token.key,
                'user_id': user.pk,
                'username': user.username,
                'two_fa_required': False
            })
        else:
            # 2FA is enabled, generate temporary token
            temp_token = TemporaryToken.generate_token(user)
            
            # Generate verification code based on 2FA method
            if user.two_fa_method == 'SMS':
                # Generate and send SMS code
                TwoFactorService.send_sms_code(user)
                
            elif user.two_fa_method == 'GOOGLE_AUTH':
                # For Google Authenticator, we don't need to generate anything
                # The user already has the app configured with the secret
                pass
                
            return Response({
                'temporary_token': temp_token.token,
                'user_id': user.pk,
                'username': user.username,
                'two_fa_required': True,
                'two_fa_method': user.two_fa_method
            })

class LoginStep2View(APIView):
    """
    Step 2 of the two-step login process.
    Verifies the 2FA code and temporary token.
    If valid, returns a permanent access token.
    """
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        temporary_token = request.data.get('temporary_token')
        verification_code = request.data.get('code')
        
        if not temporary_token or not verification_code:
            return Response({
                'error': 'Please provide both temporary_token and verification code'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate temporary token
        try:
            temp_token_obj = TemporaryToken.objects.get(token=temporary_token, is_used=False)
            if not temp_token_obj.is_valid:
                return Response({
                    'error': 'Temporary token has expired. Please login again.'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            user = temp_token_obj.user
        except TemporaryToken.DoesNotExist:
            return Response({
                'error': 'Invalid or expired temporary token'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Verify 2FA code
        verified = False
        
        if user.two_fa_method == 'SMS':
            # Verify SMS code
            try:
                code_obj = TwoFactorCode.objects.filter(
                    user=user,
                    code=verification_code,
                    is_used=False
                ).latest('created_at')
                
                if code_obj.is_valid:
                    code_obj.is_used = True
                    code_obj.save()
                    verified = True
            except TwoFactorCode.DoesNotExist:
                pass
                
        elif user.two_fa_method == 'GOOGLE_AUTH':
            # Verify Google Authenticator code using the service
            verified = TwoFactorService.verify_totp(user.two_fa_secret, verification_code)
        
        if verified:
            # Mark temporary token as used
            temp_token_obj.is_used = True
            temp_token_obj.save()
            
            # Create and return permanent token
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'access_token': token.key,
                'user_id': user.pk,
                'username': user.username,
                'email': user.email
            })
        else:
            return Response({
                'error': 'Invalid verification code'
            }, status=status.HTTP_401_UNAUTHORIZED)

class SetupGoogleAuthView(APIView):
    """
    Setup Google Authenticator for a user
    Returns a QR code and secret for the user to scan
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        user = request.user
        
        # Setup Google Authenticator
        result = TwoFactorService.setup_google_auth(user)
        
        return Response({
            'secret': result['secret'],
            'qr_code': result['qr_code'],
            'message': 'Scan the QR code with Google Authenticator app'
        })

class SetupSMSAuthView(APIView):
    """
    Setup SMS authentication for a user
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        user = request.user
        phone_number = request.data.get('phone_number')
        
        if not phone_number:
            return Response({
                'error': 'Please provide a phone number'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Update user's phone number and 2FA method
        user.phone_number = phone_number
        user.two_fa_method = CustomUser.TwoFactorMethod.SMS
        user.save()
        
        # Send a test SMS
        code = TwoFactorService.send_sms_code(user)
        
        return Response({
            'message': f'SMS authentication setup successfully. A test code has been sent to {phone_number}',
            'test_code': code  # In production, you would not return this
        })

# Keep the old views for backward compatibility
CustomLoginView = LoginStep1View
VerifyTwoFactorView = LoginStep2View

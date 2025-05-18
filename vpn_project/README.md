# VPN Project

This project contains two Django applications:
1. **authserver** - Custom authorization server for OpenVPN with 2FA support
2. **company** - Company management API with nested object updates

## Setup Instructions

### 1. Environment Setup

Create a virtual environment and install the dependencies:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Database Setup

Create a PostgreSQL database and update the `.env` file with your database credentials.

### 3. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Start the Development Server

```bash
python manage.py runserver
```

The API will be available at:
- Auth server endpoints: http://localhost:8000/api/auth/
- Company endpoints: http://localhost:8000/api/company/

## API Documentation

### Auth Server API
- `GET /api/auth/` - API overview
- `POST /api/auth/register/` - Register a new user
- `POST /api/auth/login/step1/` - Step 1: Username/password authentication
- `POST /api/auth/login/step2/` - Step 2: 2FA verification (SMS or Google Authenticator)
- `GET /api/auth/profile/` - Get user profile
- `POST /api/auth/setup-google-auth/` - Setup Google Authenticator
- `POST /api/auth/setup-sms-auth/` - Setup SMS authentication

### Company API
- `GET /api/company/` - API overview
- `GET /api/company/v1.0/company/<pid>/` - Get company details
- `PATCH /api/company/v1.0/company/<pid>/` - Update company and its nested objects 

## Two-Factor Authentication

This project supports two methods of two-factor authentication:

### SMS Authentication
1. Setup: `POST /api/auth/setup-sms-auth/` with a phone number
2. Login Step 1: `POST /api/auth/login/step1/` with username and password
3. A verification code will be sent to the user's phone (mocked in development)
4. Login Step 2: `POST /api/auth/login/step2/` with the verification code and temporary token

### Google Authenticator
1. Setup: `POST /api/auth/setup-google-auth/`
2. Scan the QR code with Google Authenticator app
3. Login Step 1: `POST /api/auth/login/step1/` with username and password
4. Login Step 2: `POST /api/auth/login/step2/` with the code from Google Authenticator app and temporary token

## Sample API Requests

### Setup Google Authenticator
```bash
curl -X POST http://localhost:8000/api/auth/setup-google-auth/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

### Setup SMS Authentication
```bash
curl -X POST http://localhost:8000/api/auth/setup-sms-auth/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890"}'
```

### Login Step 1
```bash
curl -X POST http://localhost:8000/api/auth/login/step1/ \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

### Login Step 2
```bash
curl -X POST http://localhost:8000/api/auth/login/step2/ \
  -H "Content-Type: application/json" \
  -d '{"temporary_token": "your_temporary_token", "code": "your_verification_code"}' 
```

## OpenVPN Integration

This project includes an OpenVPN Management Interface service that authenticates OpenVPN users against the Django user database with 2FA support.

### Configuration

1. In your OpenVPN server configuration, add the management interface:

```
# Enable management interface on localhost port 7505
management 127.0.0.1 7505
```

2. Configure OpenVPN to use an external authentication script:

```
# Use external auth script
auth-user-pass-verify /path/to/openvpn-auth-script.sh via-env
script-security 3
```

3. Create a client configuration that prompts for username and password:

```
auth-user-pass
```

### OpenVPN Authentication Service

To start the authentication service:

```bash
python manage.py openvpn_auth_service start
```

Run it in daemon mode:

```bash
python manage.py openvpn_auth_service start --daemonize
```

Check the status:

```bash
python manage.py openvpn_auth_service status
```

Stop the service:

```bash
python manage.py openvpn_auth_service stop
```

### Authentication Protocol

For users with 2FA enabled, the password field should contain:
- `password;verification_code`

The verification code can be from SMS or Google Authenticator, depending on the user's 2FA method. 

## Project Structure Summary

### Task 1: OpenVPN Authentication Server with 2FA

We've implemented a complete OpenVPN authentication server with 2FA support:

1. **Custom User Model**
   - Extended Django's built-in User model with 2FA fields
   - Added support for different 2FA methods (SMS, Google Authenticator)

2. **Two-Factor Authentication (2FA)**
   - SMS-based 2FA (with mock SMS sending for demonstration)
   - Google Authenticator with QR code generation
   - Temporary verification codes with expiration

3. **Two-Step Login Process**
   - Step 1: Username/password verification
   - Step 2: 2FA verification

4. **OpenVPN Management Interface**
   - TCP-based connection to OpenVPN's management interface
   - Authentication of OpenVPN users against the Django user database
   - Support for 2FA verification during VPN authentication
   - Management command to start/stop the service

5. **Mock OpenVPN Server**
   - For testing and demonstration purposes
   - Simulates the OpenVPN management interface behavior

### Key Components

1. **`authserver/models.py`**: Custom user model and 2FA-related models
2. **`authserver/services.py`**: Service to handle 2FA operations
3. **`authserver/management_interface.py`**: OpenVPN Management Interface service
4. **`authserver/management/commands/openvpn_auth_service.py`**: Command to control the service
5. **`authserver/tests/mock_openvpn_server.py`**: Mock OpenVPN server for testing

### Running the Project

1. Install dependencies: `pip install -r requirements.txt`
2. Apply migrations: `python manage.py migrate`
3. Start the server: `python manage.py runserver`
4. Start the OpenVPN auth service: `python manage.py openvpn_auth_service start`

For testing without a real OpenVPN server, run the mock server:
```bash
python authserver/tests/mock_openvpn_server.py
``` 
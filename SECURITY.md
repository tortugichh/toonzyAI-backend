# ToonzyAI Security Documentation

## 🔐 JWT Authentication System

This project implements a robust JWT (JSON Web Token) based authentication system to secure all API endpoints and user data.

## 🚀 Features

### Authentication & Authorization
- **JWT Bearer Token Authentication**: Secure token-based authentication
- **Password Hashing**: Bcrypt hashing with salt for password security
- **Access & Refresh Tokens**: Dual token system for enhanced security
- **User Registration & Login**: Secure user account management
- **Protected Endpoints**: All avatar operations require authentication
- **User Isolation**: Users can only access their own avatars

### Security Features
- **Input Validation**: Comprehensive validation using Pydantic models
- **CORS Configuration**: Secure cross-origin resource sharing
- **Error Handling**: Secure error responses without sensitive information
- **Rate Limiting Ready**: Architecture supports rate limiting middleware
- **SQL Injection Protection**: SQLAlchemy ORM prevents SQL injection

## 🔑 Authentication Flow

### 1. User Registration
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Security Features:**
- Username: 3-50 characters, alphanumeric + underscore only
- Email: Valid email format validation
- Password: Minimum 8 characters
- Bcrypt hashing with automatic salt generation
- Unique username and email constraints

### 2. User Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "johndoe",
  "password": "securepassword123"
}
```

**Returns:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 3. Using Protected Endpoints
```http
GET /api/v1/auth/me
Authorization: Bearer {access_token}
```

### 4. Token Refresh
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

## 🛡️ Security Configuration

### Environment Variables
```bash
# JWT Configuration
SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
```

### CORS Configuration
```python
allow_origins=[
    "http://localhost:3000",  # React dev server
    "https://your-frontend-domain.com",  # Production frontend
]
allow_credentials=True
allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
allow_headers=[
    "Accept", "Content-Type", "Authorization", "X-Requested-With"
]
```

## 🔒 Protected Endpoints

### Avatar Operations
All avatar endpoints require valid JWT authentication:

- `POST /api/v1/avatars/` - Create avatar
- `GET /api/v1/avatars/` - List user's avatars
- `GET /api/v1/avatars/{avatar_id}` - Get specific avatar
- `GET /api/v1/avatars/{avatar_id}/image` - Get avatar image
- `DELETE /api/v1/avatars/{avatar_id}` - Delete avatar

### User Management
- `GET /api/v1/auth/me` - Get user profile
- `PUT /api/v1/auth/me` - Update user profile
- `POST /api/v1/auth/change-password` - Change password
- `POST /api/v1/auth/logout` - Logout (client-side token deletion)

## 🎯 Security Best Practices Implemented

### 1. Password Security
- **Bcrypt Hashing**: Industry-standard password hashing
- **Salt Generation**: Automatic salt generation for each password
- **Password Policies**: Minimum length requirements
- **No Plain Text**: Passwords never stored in plain text

### 2. Token Security
- **Short-lived Access Tokens**: 30-minute expiration by default
- **Refresh Token Rotation**: New refresh tokens issued on refresh
- **Secure Claims**: Minimal user information in tokens
- **Token Type Validation**: Separate access and refresh token types

### 3. Input Validation
- **Pydantic Models**: Type-safe input validation
- **Email Validation**: RFC-compliant email validation
- **Username Constraints**: Alphanumeric characters only
- **SQL Injection Prevention**: SQLAlchemy ORM protection

### 4. Authorization
- **User Isolation**: Users can only access their own resources
- **Resource Ownership**: Strict ownership checks on all operations
- **403 Forbidden**: Proper error codes for access violations

### 5. Error Handling
- **Generic Error Messages**: No sensitive information in errors
- **Proper Status Codes**: RESTful HTTP status codes
- **Logging**: Comprehensive security event logging

## ⚡ Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Run Database Migrations
```bash
alembic upgrade head
```

### 4. Start the Server
```bash
uvicorn main:app --reload
```

### 5. Test Authentication
```bash
python test_auth.py
```

## 🔧 Testing the System

Use the included test script to verify authentication:

```bash
python test_auth.py
```

This will test:
- User registration
- User login
- Protected endpoint access
- Token refresh
- Avatar creation
- Unauthorized access blocking

## 📚 API Documentation

Visit `/docs` when the server is running for interactive API documentation with authentication support.

## 🚨 Production Security Considerations

### 1. Environment Variables
- Change `SECRET_KEY` to a long, random string
- Use strong database credentials
- Set appropriate token expiration times

### 2. HTTPS
- Always use HTTPS in production
- Configure proper SSL certificates
- Use secure cookie settings

### 3. Rate Limiting
- Implement rate limiting on auth endpoints
- Add brute force protection
- Monitor for suspicious activity

### 4. Monitoring
- Log authentication events
- Monitor failed login attempts
- Set up alerts for security events

### 5. Database Security
- Use database connection pooling
- Regular security updates
- Backup encryption

## 🤝 Contributing

When contributing to this project:
1. Follow security best practices
2. Add tests for new security features
3. Update documentation for security changes
4. Review authentication flows carefully

## 📞 Security Contact

For security issues, please email: security@yourcompany.com

---

**Remember**: Security is an ongoing process. Regularly review and update security measures as the project evolves. 
# Email Verification Setup

This document explains how to set up email verification for the ToonzyAI application.

## Email Configuration

Add the following environment variables to your `.env` file:

```bash
# Email Configuration
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_FROM=noreply@toonzyai.me
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_TLS=True
MAIL_SSL=False

# Frontend URL (for email links)
FRONTEND_URL=https://toonzyai.me
```

## Gmail Setup

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate an App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate a new app password for "Mail"
   - Use this password as `MAIL_PASSWORD`

## Alternative Email Providers

### Outlook/Hotmail
```bash
MAIL_SERVER=smtp-mail.outlook.com
MAIL_PORT=587
MAIL_TLS=True
MAIL_SSL=False
```

### Yahoo
```bash
MAIL_SERVER=smtp.mail.yahoo.com
MAIL_PORT=587
MAIL_TLS=True
MAIL_SSL=False
```

### Custom SMTP Server
```bash
MAIL_SERVER=your-smtp-server.com
MAIL_PORT=587
MAIL_TLS=True
MAIL_SSL=False
```

## Testing Email Configuration

1. Start the backend server
2. Register a new user
3. Check the email inbox for verification email
4. Click the verification link

## Troubleshooting

### Common Issues

1. **Authentication failed**: Check your email and app password
2. **Connection timeout**: Verify SMTP server and port settings
3. **Email not received**: Check spam folder and email settings

### Development Mode

For development, you can use services like:
- **Mailtrap**: For testing without sending real emails
- **Ethereal Email**: For catching emails in development

Example Mailtrap configuration:
```bash
MAIL_SERVER=smtp.mailtrap.io
MAIL_PORT=2525
MAIL_USERNAME=your-mailtrap-username
MAIL_PASSWORD=your-mailtrap-password
```

## Security Notes

- Never commit real email credentials to version control
- Use environment variables for all sensitive data
- Consider using a dedicated email service for production
- Regularly rotate app passwords 
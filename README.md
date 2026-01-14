# OBS Overlay Manager - Flask SaaS Application

A professional Flask-based SaaS application for creating and managing dynamic OBS streaming overlays for events like weddings, funerals, ceremonies, and corporate events.

## Features

- **Real-time Overlay Control**: Update overlays instantly without refreshing OBS
- **Multiple Event Types**: Pre-built templates for weddings, funerals, ceremonies, and corporate events
- **Mobile-Optimized Control Panel**: Manage overlays from your phone during live streams
- **Customizable Styling**: Control colors, fonts, animations, and layouts
- **Subscription Management**: Built-in M-Pesa payment integration with trial periods
- **Admin Panel**: User management and access control
- **WebSocket Support**: Real-time updates using Socket.IO
- **Secure Authentication**: Flask-Login with local and Google OAuth options

## Project Structure

```
obs-overlay-saas/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
├── overlays.db                     # SQLite database (auto-created)
├── static/
│   └── uploads/
│       ├── logos/                  # User company logos
│       └── photos/                 # Event photos
└── templates/
    ├── base.html                   # Base template with navigation
    ├── login.html                  # Login page
    ├── dashboard.html              # User dashboard
    ├── create_overlay.html         # Overlay creation form
    ├── control.html                # Mobile control interface
    ├── subscription.html           # Subscription management
    ├── admin_users.html            # Admin user management
    └── overlays/
        ├── funerals/
        │   ├── version1.html       # Modern funeral overlay
        │   ├── version2.html       # Classic funeral overlay
        │   └── version3.html       # Minimal funeral overlay
        ├── weddings/
        │   ├── version1.html       # Modern wedding overlay
        │   ├── version2.html       # Classic wedding overlay
        │   └── version3.html       # Minimal wedding overlay
        ├── ceremonies/
        │   ├── version1.html       # Modern ceremony overlay
        │   ├── version2.html       # Classic ceremony overlay
        │   └── version3.html       # Minimal ceremony overlay
        └── corporate/
            ├── version1.html       # Modern corporate overlay
            ├── version2.html       # Classic corporate overlay
            └── version3.html       # Minimal corporate overlay
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Clone or Download

Download all the project files to a directory on your computer.

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Edit `.env` and add your configuration:
```bash
# Generate a secret key (use Python to generate a random string)
SECRET_KEY=your-generated-secret-key-here

# M-Pesa Configuration (get from Safaricom Daraja Portal)
MPESA_CONSUMER_KEY=your-mpesa-consumer-key
MPESA_CONSUMER_SECRET=your-mpesa-consumer-secret
MPESA_SHORTCODE=your-business-shortcode
MPESA_PASSKEY=your-mpesa-passkey
MPESA_ENVIRONMENT=sandbox  # or 'production'

# Google OAuth (Optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### Step 4: Create Template Directories

Create all the required template directories:

```bash
mkdir -p templates/overlays/funerals
mkdir -p templates/overlays/weddings
mkdir -p templates/overlays/ceremonies
mkdir -p templates/overlays/corporate
```

Then create the additional version files (version2.html, version3.html) by copying and modifying version1.html files for each event type.

### Step 5: Run the Application

```bash
python app.py
```

The application will:
- Initialize the database automatically
- Create an admin user (see default credentials below)
- Start the server on `http://localhost:5000`

## Default Admin Credentials

```
Email: admin@overlays.com
Password: admin123
```

**IMPORTANT**: Change these credentials immediately after first login!

## Usage Guide

### For Admin Users

1. **Login** with admin credentials
2. **Add Users**:
   - Go to "Manage Users"
   - Click "Add New User"
   - Fill in user details
   - Users get 14-day free trial automatically

3. **Manage Subscriptions**:
   - View user subscription status
   - Enable/disable user accounts

### For Regular Users

1. **Login** to your account
2. **Create an Overlay**:
   - Click "Create New Overlay"
   - Select event type (Weddings, Funerals, Ceremonies, Corporate)
   - Choose template version
   - Name your overlay

3. **Control Your Overlay**:
   - Click "Control" on any overlay
   - Upload photos and logos
   - Add speaker information
   - Customize colors and styles
   - Toggle visibility of elements
   - Add scrolling ticker text

4. **Add to OBS**:
   - Copy the Display URL from the control panel
   - In OBS, add a "Browser Source"
   - Paste the URL
   - Set dimensions (1920x1080 recommended)
   - The overlay updates in real-time!

5. **Live Control** (Mobile-friendly):
   - Open the control page on your phone
   - Toggle elements on/off during the stream
   - Update text and speaker info live
   - Preview changes in real-time

## M-Pesa Integration Setup

### Get M-Pesa API Credentials

1. Register at [Safaricom Daraja Portal](https://developer.safaricom.co.ke/)
2. Create an app to get:
   - Consumer Key
   - Consumer Secret
3. Register for STK Push (Lipa Na M-Pesa Online):
   - Get Business Shortcode
   - Get Passkey
4. Set up callback URL in Daraja portal

### Testing with Sandbox

Use sandbox mode for testing:
```bash
MPESA_ENVIRONMENT=sandbox
```

Test phone numbers: Use 254708374149 (any other number won't work in sandbox)

### Production Deployment

1. Switch to production mode:
```bash
MPESA_ENVIRONMENT=production
```

2. Use real business credentials
3. Ensure callback URL is publicly accessible

## Database Schema

### Users Table
- Authentication and profile information
- Subscription status and dates
- Admin privileges
- Logo storage path

### Overlays Table
- Overlay identification
- Event type and template version
- User ownership
- Active status

### Overlay Data Table
- Dynamic key-value storage for overlay content
- Supports real-time updates
- Stores all customization settings

### Payments Table
- M-Pesa transaction records
- Payment status tracking
- Plan type information

## Real-Time Updates

The application uses Socket.IO for real-time communication:
- Changes made in the control panel appear instantly in OBS
- No need to refresh the browser source
- Efficient WebSocket connections

## Customization

### Adding New Event Types

1. Create new template directory:
```bash
mkdir -p templates/overlays/your-event-type
```

2. Create version files (version1.html, version2.html, version3.html)

3. Update `create_overlay.html` to include the new event type

### Creating Custom Templates

Each template file should:
- Use Socket.IO for real-time updates
- Support visibility toggles for all elements
- Handle color and style customization
- Include animations
- Be responsive and OBS-safe

### Styling Templates

Templates use:
- Tailwind CSS for styling
- Custom CSS for animations
- JavaScript for dynamic updates
- Transparent background for OBS

## Production Deployment

### Using Gunicorn (Recommended)

1. Install Gunicorn:
```bash
pip install gunicorn eventlet
```

2. Run with Gunicorn:
```bash
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 app:app
```

### Using Nginx (Recommended)

Set up Nginx as a reverse proxy:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    location /socket.io {
        proxy_pass http://127.0.0.1:5000/socket.io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Environment Setup

- Use a proper secret key (not the default)
- Set up SSL/TLS certificates
- Configure firewall rules
- Set up database backups
- Monitor application logs

## Security Considerations

1. **Change Default Credentials**: Immediately change admin password
2. **Use Strong Secret Key**: Generate a cryptographically secure key
3. **Enable HTTPS**: Use SSL/TLS in production
4. **Secure Database**: Regular backups and proper permissions
5. **Input Validation**: The app includes basic validation, enhance as needed
6. **Rate Limiting**: Consider adding rate limiting for API endpoints

## Troubleshooting

### Database Issues
- Delete `overlays.db` and restart to recreate
- Check file permissions

### WebSocket Not Working
- Ensure Socket.IO is properly installed
- Check firewall rules
- Verify CORS settings

### M-Pesa Not Working
- Verify credentials in .env file
- Check Daraja portal for API status
- Ensure callback URL is accessible
- Review Daraja documentation

### Uploads Failing
- Check `static/uploads` directory exists
- Verify write permissions
- Check file size limits

## API Endpoints

### Public Endpoints
- `GET /display/<overlay_id>` - Display overlay (for OBS)

### Protected Endpoints (Login Required)
- `GET /dashboard` - User dashboard
- `POST /create-overlay` - Create new overlay
- `GET /control/<overlay_id>` - Control interface
- `GET/POST /api/overlay/<overlay_id>` - Get/update overlay data
- `POST /upload/<file_type>` - Upload files

### Admin Endpoints
- `GET /admin/users` - User management
- `POST /admin/add-user` - Add new user
- `POST /admin/toggle-user/<user_id>` - Enable/disable user

## Support & Contributing

For issues, questions, or contributions:
1. Check existing documentation
2. Review error logs in console
3. Test in sandbox mode first
4. Ensure all dependencies are installed

## License

This project is provided as-is for educational and commercial use.

## Credits

Built with:
- Flask (Web Framework)
- Socket.IO (Real-time Communication)
- Tailwind CSS (Styling)
- SQLite (Database)
- M-Pesa API (Payments)# LMN-Overlay

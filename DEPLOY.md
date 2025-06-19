# Render.com Deployment Configuration

## Environment Variables to Set in Render Dashboard:

### Required Environment Variables:

```
FLASK_ENV=production
SECRET_KEY=[Generate a secure random key in Render dashboard]
DEBUG=False
LOG_LEVEL=INFO
MAX_CONTENT_LENGTH=16777216
```

### Optional Environment Variables:

```
MAIN_APP_PORT=5000
JSON_SERVER_PORT=8000
ROUTE_TEMP_PORT=5001
NGROK_DOMAIN=your-custom-domain.ngrok-free.app
```

## Deployment Steps:

1. **Create New Web Service in Render**

   - Connect your GitHub repository
   - Choose "Docker" as the environment
   - Or use "Python" environment with the render.yaml configuration

2. **Configure Build Settings**

   - Build Command: `pip install -r requirements.txt && pip install gunicorn`
   - Start Command: `gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 300 wsgi:app`

3. **Set Environment Variables**

   - Go to Environment tab in Render dashboard
   - Add all the required environment variables listed above
   - Generate a secure SECRET_KEY (use Render's auto-generate feature)

4. **Deploy**
   - Click "Create Web Service"
   - Render will automatically build and deploy your application

## Production Features Enabled:

- ✅ Gunicorn WSGI server for production
- ✅ Environment-based configuration
- ✅ Production-optimized JSON server (no ngrok dependency)
- ✅ Proper error handling and logging
- ✅ Security improvements (SECRET_KEY from environment)
- ✅ Cross-platform file path handling
- ✅ Automatic directory creation
- ✅ Health checks
- ✅ Persistent disk storage for uploads

## File Structure:

```
├── wsgi.py              # Production WSGI entry point
├── app_modular.py       # Main Flask application (updated for production)
├── Dockerfile           # Docker configuration
├── render.yaml          # Render-specific deployment config
├── requirements.txt     # Python dependencies (updated)
├── config.py            # Updated configuration
├── .gitignore           # Git ignore rules
├── uploads/.gitkeep     # Ensures upload directory exists
├── logs/.gitkeep        # Ensures logs directory exists
└── serving/.gitkeep     # Ensures serving directory exists
```

## Testing Before Deployment:

Run locally with production settings:

```bash
export FLASK_ENV=production
export SECRET_KEY=your-secret-key
gunicorn --bind 0.0.0.0:5000 wsgi:app
```

## Monitoring:

- Check logs in Render dashboard
- Monitor application health via the health check endpoint
- Use Render's built-in metrics for performance monitoring

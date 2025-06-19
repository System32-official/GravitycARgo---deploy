# 🚀 Render Deployment Fix Guide

## The Problem

When deployed on Render, the AR visualization throws:

```
net::ERR_BLOCKED_BY_CLIENT
Error starting AR visualization: TypeError: Failed to fetch
```

## Root Cause

The `net::ERR_BLOCKED_BY_CLIENT` error typically occurs due to:

1. **Ad blockers** blocking requests
2. **Browser security policies**
3. **CORS issues** (less likely with relative URLs)
4. **Environment configuration** issues

## 🔧 Solutions

### Solution 1: Environment Variables (CRITICAL)

Add these environment variables in your Render dashboard:

1. Go to your Render service dashboard
2. Click on "Environment" tab
3. Add these variables:

```bash
FLASK_ENV=production
DEBUG=False
JSON_SERVER_PORT=8000
```

Optional (for better URL detection):

```bash
RENDER_SERVICE_NAME=your-app-name
```

### Solution 2: Test Your Deployment

1. **Download and run the debug script:**

   ```bash
   python test_render_deployment.py
   ```

2. **Enter your Render URL when prompted** (e.g., `https://your-app.onrender.com`)

3. **Check all test results** - this will identify the specific issue

### Solution 3: Browser-Specific Fixes

**If the error persists:**

1. **Disable ad blockers** temporarily (uBlock Origin, AdBlock Plus, etc.)
2. **Try incognito/private mode**
3. **Check browser console** for additional error details
4. **Try a different browser** (Chrome, Firefox, Safari)

### Solution 4: Verify Render Deployment

1. **Check your Render logs:**

   - Go to Render dashboard → Your service → Logs
   - Look for startup errors or missing files

2. **Verify the app starts successfully:**

   - Should see: "Starting application on port XXXX"
   - Should see: "Running in production mode"

3. **Test basic endpoints:**
   - `https://your-app.onrender.com/health` should return JSON
   - `https://your-app.onrender.com/api/server-config` should return config

## 🧪 Quick Test Commands

### Test locally before deploying:

```bash
# Test the Flask app
python app_modular.py

# Test the AR functionality
python test_ar_integration.py

# Test the visualization
python standalone_visualization.py
```

### Test the deployed app:

```bash
# Replace YOUR_URL with your actual Render URL
curl https://YOUR_URL.onrender.com/health
curl https://YOUR_URL.onrender.com/api/server-config
```

## 📋 Common Issues & Fixes

### Issue: "Server not responding"

**Fix:** Check Render logs for startup errors. Ensure all dependencies are in `requirements.txt`.

### Issue: "Failed to start AR server"

**Fix:** Ensure `container_plans` directory exists with JSON files.

### Issue: "ERR_BLOCKED_BY_CLIENT"

**Fix:** Disable browser extensions, try incognito mode.

### Issue: "CORS policy" errors

**Fix:** The app includes Flask-CORS, but check browser console for specific CORS errors.

## 🔍 Debug Process

1. **Run the debug script** - this identifies 90% of issues
2. **Check Render logs** - look for Python errors
3. **Test in different browsers** - isolate browser-specific issues
4. **Check environment variables** - ensure production config is correct
5. **Verify file uploads** - ensure container plan JSON files exist

## 📞 If Still Not Working

1. **Share the output** of `test_render_deployment.py`
2. **Share Render logs** from the service dashboard
3. **Share browser console errors** (F12 → Console tab)
4. **Share your Render service URL** for direct testing

## ✅ Success Indicators

When working correctly, you should see:

- ✅ Health check passes
- ✅ Server config returns correct URL
- ✅ JSON server starts successfully
- ✅ AR instructions modal appears
- ✅ Unity-compatible URL is provided

The fixed version includes:

- 🔧 **Better environment detection**
- 🔧 **Enhanced error handling**
- 🔧 **Production URL auto-detection**
- 🔧 **Comprehensive debugging tools**

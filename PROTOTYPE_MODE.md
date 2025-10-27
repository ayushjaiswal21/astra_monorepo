# 🚀 Astra - Prototype Mode Setup

## ⚠️ IMPORTANT: Prototype Mode Active

This configuration has **relaxed security settings** for easy testing across multiple browsers and ports. 
**DO NOT USE IN PRODUCTION!**

## 🔓 Security Features Disabled

The following security features have been relaxed for prototype testing:

1. ✅ **CORS Enabled** - All origins allowed
2. ✅ **HTTP Allowed** - No HTTPS requirement
3. ✅ **Cross-Origin Cookies** - SameSite=None
4. ✅ **Insecure OAuth** - Works over HTTP
5. ✅ **Network Access** - Binds to 0.0.0.0 (all interfaces)
6. ✅ **Fixed Secret Key** - No environment variable required
7. ✅ **Data Persistence** - Database not dropped on restart

## 🚀 Quick Start

### Install Dependencies (if needed)
```bash
cd asta_authentication
pip install Flask-CORS
# or install all requirements
pip install -r requirements.txt
```

### Run on Default Port (5000)
```bash
cd asta_authentication
python run.py
```

### Run on Custom Port
```bash
python run.py 5001
python run.py 5002
python run.py 8080
```

## 🌐 Access URLs

Once running, you can access the application from:

- **Local Browser:** `http://127.0.0.1:5000`
- **Same Network:** `http://<your-ip>:5000`
- **Multiple Browsers:** Chrome, Firefox, Edge, Safari - all work!

## 🔄 Running Multiple Instances

You can run multiple instances on different ports simultaneously:

**Terminal 1:**
```bash
cd asta_authentication
python run.py 5000
```

**Terminal 2:**
```bash
cd asta_authentication
python run.py 5001
```

**Terminal 3:**
```bash
cd asta_authentication
python run.py 5002
```

Each instance will have its own database and session.

## 🧪 Testing Across Browsers

### Same Port, Different Browsers
1. Start server: `python run.py 5000`
2. Open Chrome: `http://127.0.0.1:5000`
3. Open Firefox: `http://127.0.0.1:5000`
4. Open Edge: `http://127.0.0.1:5000`

All browsers will share the same database and can interact with each other!

### Different Ports, Same Browser
1. Start servers on ports 5000, 5001, 5002
2. Open tabs in Chrome:
   - Tab 1: `http://127.0.0.1:5000`
   - Tab 2: `http://127.0.0.1:5001`
   - Tab 3: `http://127.0.0.1:5002`

Each port has independent data!

## 📱 Mobile/Tablet Testing

1. Find your computer's IP address:
   - Windows: `ipconfig` (look for IPv4)
   - Mac/Linux: `ifconfig` or `ip addr`

2. Start server: `python run.py 5000`

3. On mobile device (same WiFi):
   - Open browser
   - Go to: `http://<your-computer-ip>:5000`
   - Example: `http://192.168.1.100:5000`

## 🛠️ Configuration Changes Made

### app.py
- ✅ CORS enabled for all origins
- ✅ Session cookies allow cross-origin
- ✅ HTTP cookies allowed (not HTTPS only)
- ✅ OAuth insecure transport enabled
- ✅ Database persistence (no auto-drop)

### run.py
- ✅ Binds to 0.0.0.0 (all network interfaces)
- ✅ Accepts port as command line argument
- ✅ Shows network access URL
- ✅ Allows unsafe Werkzeug for development

### requirements.txt
- ✅ Added Flask-CORS==4.0.0

## 🔒 Re-enabling Security for Production

When ready for production, you MUST:

1. **Remove CORS wildcard:**
   ```python
   CORS(app, resources={r"/*": {"origins": "https://yourdomain.com"}})
   ```

2. **Use environment variables:**
   ```python
   app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
   ```

3. **Enable secure cookies:**
   ```python
   app.config['SESSION_COOKIE_SECURE'] = True
   app.config['SESSION_COOKIE_HTTPONLY'] = True
   app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
   ```

4. **Disable insecure OAuth:**
   ```python
   # Remove: os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
   ```

5. **Bind to localhost only:**
   ```python
   socketio.run(app, host='127.0.0.1', port=port)
   ```

6. **Use production database:**
   ```python
   app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
   ```

## 📊 Current Features Working

All analytics features work in prototype mode:

### Seeker Dashboard
- ✅ Course enrollment tracking
- ✅ Progress monitoring
- ✅ Internship applications
- ✅ Job applications
- ✅ Workshop registrations

### Provider Dashboard
- ✅ Announcement performance
- ✅ Application tracking
- ✅ Connected seekers
- ✅ Seeker progress monitoring

### Common Features
- ✅ Login tracking
- ✅ Profile views
- ✅ Connections
- ✅ Activity feed

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Try a different port
python run.py 5001
```

### Can't Access from Mobile
- Check firewall settings
- Ensure devices on same WiFi
- Try `http://` not `https://`

### CORS Errors
- Already fixed! CORS is enabled for all origins

### Session Not Persisting
- Already fixed! Cookies work across origins

## ✅ You're All Set!

Your Astra application is now configured for easy prototype testing across:
- ✅ Multiple browsers
- ✅ Multiple ports
- ✅ Multiple devices
- ✅ Cross-origin requests

**Happy Testing! 🎉**

---

**Remember:** This is PROTOTYPE MODE only. Never deploy with these settings to production!

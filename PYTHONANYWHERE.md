# SHEDS POS - PythonAnywhere Hosting Setup

## Step 1: Create Account
- Go to https://www.pythonanywhere.com/
- Sign up for a **free account**
- Verify your email

## Step 2: Upload Files
1. Log in to PythonAnywhere
2. Go to the **Files** tab
3. Navigate to `/home/yourusername/`
4. Create a folder called `sheds-pos`
5. Upload these files to that folder:
   - `server.py`
   - `requirements.txt`
   - `api/index.py`
   - `api.js`
   - `pythonanywhere_wsgi.py`
   - All `.html` files (login.html, dashboard.html, etc.)
   - All `.css` and `.js` files

## Step 3: Install Dependencies
1. Go to the **Consoles** tab
2. Click **"Bash"**
3. Run:
```bash
cd ~/sheds-pos
pip install -r requirements.txt
```

## Step 4: Configure Web App
1. Go to the **Web** tab
2. Click **"Add a new web app"**
3. Click **"Next"**
4. Select **Manual configuration**
5. Choose **Python 3.11** (or latest available)
6. Click **"Next"**

## Step 5: Edit WSGI Configuration
1. In the **Web** tab, find the **WSGI configuration file** link
2. Click it to edit
3. Replace the ENTIRE content with:
```python
import sys
import os

# Add your project directory
project_home = '/home/yourusername/sheds-pos'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set secret key (generate your own!)
os.environ['SECRET_KEY'] = 'your-secret-key-here'

# Import the Flask app
from server import app as application
```
4. Replace `yourusername` with your actual PythonAnywhere username
5. Replace `your-secret-key-here` with a random string (use: `openssl rand -hex 16`)
6. Click **Save**

## Step 6: Configure Static Files
In the **Web** tab, scroll to **Static files**:
- **URL:** `/static/`
- **Directory:** `/home/yourusername/sheds-pos/`
- Click **Add** (if needed)

Also add these static file mappings:
- **URL:** `/api/` → **Directory:** `/home/yourusername/sheds-pos/api/`
- **URL:** `/*.css` → **Directory:** `/home/yourusername/sheds-pos/`
- **URL:** `/*.js` → **Directory:** `/home/yourusername/sheds-pos/`

## Step 7: Reload the App
1. In the **Web** tab, click the big green **Reload** button
2. Wait for it to finish

## Step 8: Test
- Click the **"Your web app URL"** link at the top of the Web tab
- Or visit: `https://yourusername.pythonanywhere.com`

## Step 9: Register a Pharmacy
1. Open your app URL
2. Click **"New Pharmacy"**
3. Fill in details
4. **Save the API key**
5. Login

---

## Important Notes

### Free Tier Limitations
- Your app will "sleep" after 1 month of inactivity
- Limited CPU/bandwidth
- Cannot run background tasks

### Keep App Awake (Optional)
Use a free service like UptimeRobot to ping your app every 5 minutes:
1. Go to https://uptimerobot.com/
2. Add a new monitor
3. URL: `https://yourusername.pythonanywhere.com/api/health`
4. Interval: 5 minutes

### Custom Domain (Paid plans only)
- Upgrade to a paid plan ($5/month or $12/month)
- Go to **Web** tab → **Custom domains**

### Database Backup
Your database (`danzona_pos.db`) is in your home directory. Download it regularly:
1. Go to **Files** tab
2. Navigate to `/home/yourusername/sheds-pos/`
3. Click the download button next to `danzona_pos.db`

---

## Troubleshooting

**"Application error" page:**
- Check the **Log** tab in the Web section
- Make sure the path in WSGI file is correct
- Verify `requirements.txt` installed successfully

**"Module not found" errors:**
- Make sure all files are uploaded to `/home/yourusername/sheds-pos/`
- Check that `api/` folder contains `index.py`
- Reload the web app

**Static files not loading (CSS/JS broken):**
- Verify static file mappings in the Web tab
- Make sure file paths are lowercase (PythonAnywhere is case-sensitive)

**Database errors:**
- Ensure `danzona_pos.db` is in `/home/yourusername/sheds-pos/`
- Check file permissions (should be readable by the web app)

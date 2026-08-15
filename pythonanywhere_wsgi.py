"""
PythonAnywhere WSGI Configuration
Path: /var/www/yourusername_pythonanywhere_com_wsgi.py
"""
import sys
import os

# Add your project directory to sys.path
project_home = '/home/yourusername/sheds-pos'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables
os.environ['SECRET_KEY'] = 'change-me-to-a-random-secret-key'
os.environ['DB_PATH'] = os.path.join(project_home, 'danzona_pos.db')

# Import the Flask app
from server import app as application

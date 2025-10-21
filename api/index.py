"""
Vercel Serverless Function Entry Point
This file is required by Vercel to deploy the Flask application.
"""
import os
import sys

# Add the parent directory to sys.path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Vercel requires the app to be exported as 'app' or handler function
# The Flask app instance is already configured in app.py
app = app

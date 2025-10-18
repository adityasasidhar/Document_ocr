#!/bin/bash

# Document OCR - Render Deployment Script
echo "🚀 Preparing Document OCR for Render deployment..."

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📦 Initializing Git repository..."
    git init
    git add .
    git commit -m "Initial commit: Document OCR app ready for deployment"
    echo "✅ Git repository initialized"
else
    echo "📦 Adding files to Git..."
    git add .
    git commit -m "Update: Ready for Render deployment"
    echo "✅ Files committed to Git"
fi

echo ""
echo "🎯 Next steps for Render deployment:"
echo "1. Push to GitHub:"
echo "   git remote add origin <your-github-repo-url>"
echo "   git push -u origin main"
echo ""
echo "2. Go to https://dashboard.render.com"
echo "3. Click 'New +' → 'Web Service'"
echo "4. Connect your GitHub repository"
echo "5. Configure:"
echo "   - Build Command: pip install -r requirements.txt"
echo "   - Start Command: gunicorn app:app"
echo "6. Set environment variables:"
echo "   - FLASK_SECRET_KEY: (generate a secure key)"
echo "   - ANTHROPIC_API_KEY: (your API key)"
echo "   - FLASK_DEBUG: False"
echo "   - PORT: 5000"
echo ""
echo "✨ Your app will be ready for deployment!"
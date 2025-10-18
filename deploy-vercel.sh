#!/bin/bash

# Vercel deployment script
echo "🚀 Deploying to Vercel..."

# Install Vercel CLI if not installed
if ! command -v vercel &> /dev/null; then
    echo "📦 Installing Vercel CLI..."
    npm install -g vercel
fi

# Deploy to Vercel
echo "🚀 Deploying..."
vercel --prod

echo "✅ Deployment complete!"
echo "🌐 Your app will be available at the URL shown above"

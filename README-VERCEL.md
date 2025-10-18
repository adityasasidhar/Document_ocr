# Document OCR - Vercel Deployment

## 🚀 Quick Deploy to Vercel

### Prerequisites
- Node.js installed
- Vercel account (free)

### Deployment Steps

1. **Install Vercel CLI:**
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel:**
   ```bash
   vercel login
   ```

3. **Deploy:**
   ```bash
   vercel --prod
   ```

4. **Set Environment Variables:**
   ```bash
   vercel env add ANTHROPIC_API_KEY
   vercel env add FLASK_SECRET_KEY
   ```

### Environment Variables Required:
- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `FLASK_SECRET_KEY`: Random secret key (auto-generated)

### Features:
- ✅ **5-minute timeout** (vs 30s on Render)
- ✅ **Full AI processing** (all 4 phases)
- ✅ **Serverless scaling**
- ✅ **Global CDN**
- ✅ **Automatic HTTPS**

### File Structure:
```
├── app.py              # Main Flask app
├── secondary.py        # AI processing logic
├── vercel.json         # Vercel configuration
├── requirements.txt    # Python dependencies
├── .vercelignore      # Files to ignore
└── templates/         # HTML templates
```

### Testing:
- Visit `/test` endpoint to check configuration
- Visit `/health` endpoint for health check
- Upload a PDF to test full functionality

### Troubleshooting:
- Check Vercel function logs in dashboard
- Ensure environment variables are set
- Verify API key is valid

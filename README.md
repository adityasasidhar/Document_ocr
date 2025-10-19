# Document OCR - AI-Powered Balance Sheet Generator

A Flask web application that uses Claude AI to process financial PDF documents and generate professional Italian balance sheets. The application extracts financial data from uploaded PDFs and creates formatted balance sheets ready for business use.

## Features

- 🤖 **AI-Powered Processing**: Uses Claude AI for intelligent document analysis
- 📄 **PDF Upload**: Support for multiple PDF file uploads (up to 5 files, 50MB each)
- 🔒 **Secure Processing**: CSRF protection and secure file handling
- 📊 **Professional Output**: Generates formatted Italian balance sheets
- ⚡ **Fast Processing**: Multi-agent system for efficient document processing
- 🎨 **Modern UI**: Beautiful, responsive web interface

## Technology Stack

- **Backend**: Flask (Python)
- **AI**: Anthropic Claude API
- **PDF Generation**: ReportLab
- **Frontend**: HTML5, CSS3, JavaScript
- **Deployment**: Vercel

## Prerequisites

- Python 3.8+
- Anthropic API key
- Git (for deployment)

## Local Development

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd PythonProject
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Setup

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` file with your configuration:

```env
FLASK_SECRET_KEY=your-secret-key-here
FLASK_DEBUG=True
ANTHROPIC_API_KEY=your-anthropic-api-key-here
PORT=5000
```

### 5. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Deployment on Vercel

### Method 1: Using Vercel CLI (Recommended)

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel**
   ```bash
   vercel login
   ```

3. **Deploy**
   ```bash
   vercel --prod
   ```

4. **Set Environment Variables**
   ```bash
   vercel env add ANTHROPIC_API_KEY
   vercel env add FLASK_SECRET_KEY
   ```

### Method 2: Using Vercel Dashboard

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

2. **Connect to Vercel**
   - Go to [Vercel Dashboard](https://vercel.com/dashboard)
   - Click "New Project"
   - Import your GitHub repository

3. **Configure Project**
   - **Framework Preset**: Other
   - **Root Directory**: `./`
   - **Build Command**: `pip install -r requirements.txt`
   - **Output Directory**: `./`

4. **Set Environment Variables**
   - `ANTHROPIC_API_KEY`: Your Anthropic API key
   - `FLASK_SECRET_KEY`: A secure random string

5. **Deploy**
   - Click "Deploy"
   - Wait for deployment to complete
   - Your app will be available at the provided URL

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `FLASK_SECRET_KEY` | Secret key for Flask sessions | Yes | - |
| `ANTHROPIC_API_KEY` | API key for Anthropic Claude | Yes | - |
| `FLASK_DEBUG` | Enable debug mode | No | `False` |
| `PORT` | Port to run the application | No | `5000` |

## API Endpoints

- `GET /` - Main upload page
- `POST /upload` - File upload and processing
- `GET /download/<filename>` - Download generated PDF
- `GET /health` - Health check endpoint

## File Structure

```
PythonProject/
├── app.py                 # Main Flask application
├── secondary.py           # AI processing logic
├── requirements.txt       # Python dependencies
├── vercel.json           # Vercel deployment config
├── .vercelignore         # Vercel ignore file
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
├── README.md             # This file
├── static/               # Static files
│   └── style.css         # CSS styles
├── templates/            # HTML templates
│   ├── index.html        # Upload page
│   └── results.html      # Results page
├── uploads/              # Uploaded files (created at runtime)
└── outputs/              # Generated files (created at runtime)
```

## Security Features

- CSRF token protection
- File type validation (PDF only)
- File size limits (50MB per file)
- Secure filename handling
- Session-based file access control

## Performance Considerations

- Files are processed in memory for better performance
- Temporary files are cleaned up after processing
- Multi-agent AI processing for efficiency
- Responsive design for mobile devices

## Troubleshooting

### Common Issues

1. **API Key Not Found**
   - Ensure `ANTHROPIC_API_KEY` is set in environment variables
   - Check that the API key is valid and has sufficient credits

2. **File Upload Fails**
   - Verify file is PDF format
   - Check file size is under 50MB
   - Ensure uploads directory has write permissions

3. **Deployment Issues**
   - Check that all environment variables are set
   - Verify requirements.txt includes all dependencies
   - Check Vercel function logs for specific error messages

### Debug Mode

To enable debug mode locally:
```bash
export FLASK_DEBUG=True
python app.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support or questions:
- Create an issue in the GitHub repository
- Check the troubleshooting section above
- Review Vercel function logs

## Changelog

### Version 1.0.0
- Initial release
- AI-powered PDF processing
- Italian balance sheet generation
- Modern web interface
- Vercel deployment ready
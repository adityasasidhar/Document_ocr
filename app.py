import os
import secrets
from flask import Flask, render_template, request, url_for, session, send_file
from werkzeug.utils import secure_filename
from pathlib import Path
from dotenv import load_dotenv
import traceback
import time

# Import our balance sheet generator
from secondary import generate_balance_sheet, create_pdf

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))

# Configuration
UPLOAD_FOLDER = Path('uploads')
OUTPUT_FOLDER = Path('outputs')
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILES = 5
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Ensure directories exist
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)


def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_csrf_token():
    """Generate CSRF token and store in session"""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']


def validate_csrf_token(token):
    """Validate CSRF token against session"""
    return token == session.get('csrf_token')


@app.route('/')
def index():
    """Render upload form"""
    # Generate new session ID if not exists
    if 'session_id' not in session:
        session['session_id'] = secrets.token_hex(16)

    csrf_token = generate_csrf_token()
    return render_template('index.html', csrf_token=csrf_token)


@app.route('/upload', methods=['POST'])
def upload():
    """Handle file upload and processing"""
    try:
        # Initialize agent telemetry
        start_time = time.time()
        stage_start = start_time
        agent_steps = []
        agent_logs = []
        agent_logs.append("Session started. Validating request and security token...")
        # Validate CSRF token
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            return render_template('results.html',
                                   error='Invalid security token. Please refresh and try again.'), 403

        # Check if files were uploaded
        if 'files' not in request.files:
            return render_template('results.html',
                                   error='No files uploaded. Please select at least one PDF file.'), 400

        files = request.files.getlist('files')

        # Validate number of files
        if len(files) == 0 or files[0].filename == '':
            return render_template('results.html',
                                   error='No files selected. Please choose at least one PDF file.'), 400

        if len(files) > MAX_FILES:
            return render_template('results.html',
                                   error=f'Too many files. Maximum {MAX_FILES} files allowed.'), 400

        # Validate and save files
        session_id = session.get('session_id', secrets.token_hex(16))
        session['session_id'] = session_id

        saved_files = []
        for file in files:
            # Validate file
            if not allowed_file(file.filename):
                return render_template('results.html',
                                       error=f'Invalid file type: {file.filename}. Only PDF files are allowed.'), 400

            # Save file with unique name
            filename = secure_filename(file.filename)
            unique_filename = f"{session_id}_{filename}"
            filepath = UPLOAD_FOLDER / unique_filename

            file.save(filepath)
            saved_files.append(str(filepath))

        print(f"\n📁 Files saved: {len(saved_files)}")
        for f in saved_files:
            print(f"  - {f}")

        # Process files with Claude
        # Mark files saved step
        agent_logs.append(f"Saved {len(saved_files)} file(s) to disk.")
        agent_steps.append({'label': 'Files uploaded and saved', 'duration_ms': int((time.time() - stage_start)*1000)})
        stage_start = time.time()
        agent_logs.append("Sending documents to Claude for analysis...")
        print("\n🚀 Starting balance sheet generation...")
        balance_sheet_text = generate_balance_sheet(saved_files)
        agent_steps.append({'label': 'AI analysis (Claude)', 'duration_ms': int((time.time() - stage_start)*1000)})
        agent_logs.append("Received structured balance sheet from Claude.")
        stage_start = time.time()

        # Generate PDF output
        output_filename = f"{session_id}_bilancio.pdf"
        output_path = OUTPUT_FOLDER / output_filename

        print(f"\n📝 Creating PDF: {output_path}")
        create_pdf(balance_sheet_text, str(output_path))
        agent_steps.append({'label': 'PDF generation', 'duration_ms': int((time.time() - stage_start)*1000)})
        agent_logs.append(f"PDF generated at {output_path}.")
        stage_start = time.time()

        # Save text output as well
        text_output_path = OUTPUT_FOLDER / f"{session_id}_bilancio.txt"
        with open(text_output_path, 'w', encoding='utf-8') as f:
            f.write(balance_sheet_text)
        agent_steps.append({'label': 'Save text backup', 'duration_ms': int((time.time() - stage_start)*1000)})
        agent_logs.append(f"Saved text backup at {text_output_path}.")
        stage_start = time.time()

        # Finalize
        agent_steps.append({'label': 'Finalize & prepare download', 'duration_ms': int((time.time() - stage_start)*1000)})
        agent_logs.append("Finalized processing and prepared download link.")

        print(f"\n✅ Success! Generated: {output_filename}")

        # Store output filename in session
        session['output_file'] = output_filename

        # Regenerate CSRF token for security
        session.pop('csrf_token', None)

        return render_template('results.html',
                               success=True,
                               filename=output_filename,
                               download_url=url_for('download', filename=output_filename),
                               agent_steps=agent_steps,
                               agent_logs=agent_logs)

    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        traceback.print_exc()
        error_message = str(e)

        # Make error message more user-friendly
        if "API key not found" in error_message:
            error_message = "API configuration error. Please contact the administrator."
        elif "Maximum 5 files" in error_message:
            error_message = "Too many files. Please upload maximum 5 PDF files."

        return render_template('results.html',
                               error=f'Error processing files: {error_message}',
                               agent_steps=agent_steps if 'agent_steps' in locals() else [],
                               agent_logs=agent_logs if 'agent_logs' in locals() else []), 500


@app.route('/download/<filename>')
def download(filename):
    """Download generated file"""
    try:
        # Security: Validate filename belongs to current session
        session_id = session.get('session_id')
        expected_filename = session.get('output_file')

        if not session_id or filename != expected_filename:
            return render_template('results.html',
                                   error='Invalid download request.'), 403

        filepath = OUTPUT_FOLDER / filename

        if not filepath.exists():
            return render_template('results.html',
                                   error='File not found. It may have been deleted.'), 404

        print(f"\n📥 Downloading: {filename}")

        # Send file to user
        return send_file(
            filepath,
            as_attachment=True,
            download_name='bilancio_completo.pdf',
            mimetype='application/pdf'
        )

    except Exception as e:
        print(f"\n❌ Error during download: {e}")
        return render_template('results.html',
                               error=f'Error downloading file: {str(e)}'), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'healthy', 'service': 'DocumentOCR'}, 200


# Custom error handlers
@app.errorhandler(404)
def not_found(_):
    return render_template('results.html',
                           error='Page not found.'), 404


@app.errorhandler(500)
def internal_error(_):
    return render_template('results.html',
                           error='Internal server error. Please try again.'), 500


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("🚀 Document OCR Flask Application Starting...".center(70))
    print("=" * 70)
    print(f"\n📁 Upload folder: {UPLOAD_FOLDER.absolute()}")
    print(f"📁 Output folder: {OUTPUT_FOLDER.absolute()}")
    print(f"🔒 Max files: {MAX_FILES}")
    print(f"📊 Max file size: {MAX_FILE_SIZE / 1024 / 1024:.0f}MB")
    print(f"\n🌐 Access the application at: http://localhost:5000")
    print("=" * 70 + "\n")

    # Get port from environment variable (for production deployment)
    port = int(os.getenv('PORT', 5000))
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Run the app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode
    )
"""
Flask uploader for Givebutter donation files
Uploads land in INTAKE_DIR (intake/new)
"""

import os
from pathlib import Path
from datetime import datetime
from flask import Flask, request, render_template_string
from werkzeug.utils import secure_filename

# 1. Import env_manager first - it auto-discovers rules and creates intake/review folders
import scripts.env_manager
from dotenv import load_dotenv

# 2. Use the project root that env_manager already resolved
ROOT = scripts.env_manager.PROJECT_ROOT
load_dotenv(ROOT / ".env")

# 3. Read paths from .env (with safe defaults)
UPLOAD_FOLDER = ROOT / os.getenv("INTAKE_DIR", "intake/new")
RULES_FILE = ROOT / os.getenv("RULES_FILE", "config/rules/rules_v2.4.json")

print(f"[app] Pending folder: {UPLOAD_FOLDER}")
print(f"[app] Rules: {RULES_FILE}")

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

HTML = """
<!doctype html>
<title>Givebutter Uploader</title>
<style>
 body { font-family: system-ui; max-width: 600px; margin: 40px auto; padding: 20px; }
 h2 { color: #333; }
 .info { background: #f0f7ff; padding: 12px; border-radius: 6px; margin: 20px 0; }
</style>
<h2>Upload Givebutter Donation CSV</h2>
<div class="info">
  <strong>Files go to:</strong> intake/new/<br>
  <strong>Processor flags to:</strong> review/flagged/
</div>
<form method=post enctype=multipart/form-data>
  <input type=file name=file required>
  <input type=submit value="Upload">
</form>
"""

@app.route('/', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        f = request.files.get('file')
        if not f or f.filename == '':
            return "No file selected", 400
        
        filename = secure_filename(f.filename)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = Path(app.config['UPLOAD_FOLDER']) / f"upload_{ts}_{filename}"
        
        # ensure folder exists
        dest.parent.mkdir(parents=True, exist_ok=True)
        f.save(dest)
        
        return f"""
        <h3>✓ Uploaded successfully</h3>
        <p>Saved as: <code>{dest.name}</code></p>
        <p>Location: <code>intake/new/</code></p>
        <p><a href="/">Upload another</a></p>
        """
    
    return render_template_string(HTML)

if __name__ == '__main__':
    # Works both ways: python3 app.py (from uploader) or python3 -m scripts.uploader.app (from Givebutter)
    app.run(debug=True, port=5000, host='127.0.0.1')

# Setup Guide
## How to Get the Givebutter Donation Processor Running (First Time)

**This guide is for the technical person setting up the system.** If you're an operator, skip this and go to [OPERATOR_MANUAL.md](OPERATOR_MANUAL.md).

**Estimated time:** 30 minutes for first-time setup, 5 minutes for testing.

---

## What You'll Need

### Required
- [ ] **Computer:** Mac or Windows (Linux also works)
- [ ] **Python 3.8+:** Check if you have it: `python --version`
- [ ] **The code folder:** Either cloned from git or provided as a .zip file
- [ ] **A web browser:** Chrome, Safari, Firefox, or Edge (for testing)
- [ ] **A sample Givebutter CSV file:** For testing the system

### Optional (for advanced use)
- [ ] Git (if you want to version-control changes)
- [ ] Claude Code (if you want to let Claude help with rules)

---

## Step 0: Prepare the System

### 0.1 Check Python Version

Open a terminal and run:
```bash
python --version
```

**You should see:**
```
Python 3.8.x, 3.9.x, 3.10.x, 3.11.x, 3.12.x, or newer
```

**If not found:**
- **Mac:** Install from https://www.python.org/downloads/
- **Windows:** Install from https://www.python.org/downloads/ (check "Add Python to PATH" during install)

### 0.2 Navigate to the Givebutter Folder

In your terminal, go to the Givebutter folder:

**Mac/Linux:**
```bash
cd /Users/gautambiswas/Claude\ Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter
```

**Windows:**
```cmd
cd "C:\Users\YourUsername\[path]\Givebutter"
```

**You should be in a folder that contains:**
- `scripts/` (folder)
- `config/` (folder)
- `README.md` (file)
- `OPERATOR_MANUAL.md` (file)
- `requirements.txt` (file)

If not, you're in the wrong folder. Go back and find the Givebutter folder.

### 0.3 Create Virtual Environment

The virtual environment keeps this project's dependencies separate from your system Python.

**Mac/Linux:**
```bash
python3 -m venv .venv
```

**Windows:**
```cmd
python -m venv .venv
```

**You should see a new `.venv/` folder appear.** (It might take 10-30 seconds.)

### 0.4 Activate Virtual Environment

**Mac/Linux:**
```bash
source .venv/bin/activate
```

**Windows (PowerShell):**
```cmd
.\.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
.venv\Scripts\activate.bat
```

**You should see `(.venv)` appear at the start of your terminal prompt.**

Example:
```
(.venv) ~/Givebutter $
```

**If you don't see `(.venv)`, the activation failed. Try the activation command again.**

---

## Step 1: Install Dependencies

While still in the virtual environment (with `(.venv)` showing), run:

```bash
pip install -r requirements.txt
```

**You should see:**
```
Collecting Flask==...
Collecting pandas==...
Collecting python-dotenv==...
...
Successfully installed Flask-3.1.3 pandas-3.0.3 python-dotenv-1.2.2 ...
```

This might take 2-5 minutes. **That's normal.** It's downloading and installing libraries.

**If you see errors:**
- Try `pip install --upgrade pip` first
- Then try `pip install -r requirements.txt` again

### Troubleshooting: Permission Denied

**If you see:** `ERROR: Permission denied`

Try:
```bash
pip install --user -r requirements.txt
```

---

## Step 2: Start the Uploader

Still in the virtual environment, run:

```bash
python -m scripts.uploader.app
```

**You should see:**
```
 * Running on http://127.0.0.1:5000
 * Restarting with reloader
 * Debugger is active!
```

**If you see** `Address already in use`:
- Another program is using port 5000
- Change the port in `scripts/uploader/app.py` (advanced)
- Or stop whatever's using port 5000

**The uploader is now running.** Leave this terminal window open.

---

## Step 3: Open the Uploader in Your Browser

Open a NEW terminal window (don't close the one running the uploader).

Go to:
```
http://localhost:5000
```

**You should see a simple form:**

```
Upload Givebutter Donation CSV

[Choose File] [Upload]
```

**If you see nothing:**
- Wait 3 seconds (sometimes takes a moment to start)
- Refresh your browser (F5 or Cmd+R)
- Try `http://127.0.0.1:5000` instead

**If the page still won't load:**
- Check the uploader terminal—are there errors?
- Make sure the first terminal is still showing the uploader message

---

## Step 4: Prepare a Test CSV File

You'll need a sample Givebutter CSV to test with.

### Option A: Use an Existing Export

If you have a real Givebutter export:
1. Log into Givebutter
2. Go to **Donations** → **Export**
3. Download the CSV
4. Save it somewhere you can easily find

### Option B: Create a Test File

If you don't have a real export, create a simple test CSV:

1. Open a text editor (Notepad, TextEdit, etc.)
2. Copy and paste this:

```csv
donor_name,email,donation_amount,donation_date
John Smith,john@gmail.com,100,2026-05-25
Jane Doe,jane@gmai.com,50,2026-05-25
Bob Wilson,bob@yahoo.com,75,2026-05-25
Alice Brown,alice@yaho.com,200,2026-05-25
```

3. Save as: `test_donations.csv`

**Note the typos:** `gmai.com` (missing 'i'), `yaho.com` (missing 'o'). The system will flag these.

---

## Step 5: Upload Your Test File

1. Go back to http://localhost:5000
2. Click **"Choose File"**
3. Select your CSV file (test_donations.csv or your real export)
4. Click **"Upload"**

**You should see:**
```
File received
```

**The file is now being processed. Wait 5-10 seconds.**

---

## Step 6: Check for Flagged Records

Open your file explorer and navigate to the Givebutter folder.

Look for a new folder called **`review/flagged/`**

Inside, you should see a file like:
```
flagged_20260525_143045_upload_20260525_143022_test_donations.csv
```

**Open that file in Excel, Google Sheets, or a text editor.**

**You should see:**
```
donor_name,email,donation_amount,donation_date
Jane Doe,jane@gmai.com,50,2026-05-25
Alice Brown,alice@yaho.com,200,2026-05-25
```

**These are the records with email typos that the system flagged.**

---

## Step 7: Test the Full Workflow

Now test the complete 5-step workflow:

### 7.1 Review Flagged Records

You're already looking at them (the CSV file from Step 6).

Ask yourself: "Are these actually typos?"
- jane@gmai.com → Yes, should be gmail.com
- alice@yaho.com → Yes, should be yahoo.com

### 7.2 Approve the Records

Move the flagged file to the approved folder:

1. In file explorer, find the flagged file
2. Right-click it
3. Select **"Cut"** (or press Cmd+X on Mac, Ctrl+X on Windows)
4. Navigate to **`review/approved/`** folder
5. Right-click empty space
6. Select **"Paste"** (or press Cmd+V on Mac, Ctrl+V on Windows)

**The file should now be in `review/approved/`**

### 7.3 Report a Pattern (Optional - Advanced)

If you approved that file, you'd now tell your tech lead:

> "I found 2 email typos in the test batch:
> - gmai.com (should be gmail.com)  
> - yaho.com (should be yahoo.com)"

They would then propose rules to catch these automatically next time.

---

## Step 8: Success Checklist

If you see all of these, **the system is working!** ✅

- [ ] Uploader runs without errors on http://localhost:5000
- [ ] You can upload a CSV file
- [ ] Uploader says "File received"
- [ ] A file appears in `review/flagged/` within 10 seconds
- [ ] The flagged file contains the problematic records
- [ ] You can move the file to `review/approved/`
- [ ] No error messages in the uploader terminal

---

## Step 9: Train Your Team

Now that the system is working:

1. **Print [QUICK_START.md](docs/QUICK_START.md)** — Give a copy to each operator
2. **Share [OPERATOR_MANUAL.md](OPERATOR_MANUAL.md)** — They'll need to read this
3. **Give them the uploader URL** — `http://localhost:5000` or your server address
4. **Do a practice upload together** — Let them walk through it once

---

## Step 10: Next Steps (After Testing)

### A. Set Up Regular Uploads

Decide on a schedule:
- Daily? (Run uploader in the morning)
- Weekly? (Run every Monday)
- Monthly? (Run on the 1st)

**For now, the uploader runs manually.** Advanced setups can automate this later.

### B. Set Up Backups (Optional)

Keep the original CSV files safe:

1. Copy `intake/archive/` to a backup location (Google Drive, external drive, cloud storage)
2. Do this weekly or monthly
3. Keep at least 3 months of backups

**Why?** In case you need to recover old data.

### C. Monitor Rules

Check with your operators monthly:
- "Any patterns emerging?"
- "Should we add new rules?"
- "Any false positives?"

Use their feedback to improve rules over time.

### D. Keep the Processor Running

**Important:** The processor needs to keep running for files to be processed.

Options:
1. **Keep the terminal window open** (simple, but only works while computer is on)
2. **Run as a background service** (advanced—requires help from your IT person)
3. **Run on a server** (advanced—requires cloud setup)

For now, just keep the terminal window open when you need to process files.

---

## Troubleshooting Setup Issues

### Problem: Python not found

**You see:** `command not found: python` or `python is not recognized`

**Solutions:**
1. Install Python from https://www.python.org/downloads/
2. On Windows, during installation, check "Add Python to PATH"
3. Restart your terminal and try again

---

### Problem: Virtual environment won't activate

**You see:** `command not found: source` or `.venv\Scripts\activate.bat is not recognized`

**Solutions:**
- Mac/Linux: Make sure you're using `source .venv/bin/activate` (with the word "source")
- Windows: Make sure you're in the Givebutter folder and use the right activation command for your shell type

---

### Problem: pip install fails

**You see:** `ERROR: Collecting [package]...`

**Solutions:**
1. Check your internet connection
2. Try updating pip: `pip install --upgrade pip`
3. Try installing again: `pip install -r requirements.txt`

---

### Problem: Uploader says "Address already in use"

**You see:** `Address already in use, port 5000`

**Solutions:**
1. Another program is using port 5000
2. Close that program or kill the process:
   - **Mac/Linux:** `lsof -i :5000` then `kill [PID]`
   - **Windows:** `netstat -ano | findstr :5000`

---

### Problem: File uploads but nothing appears in review/flagged/

**Solutions:**
1. Wait 10 seconds (processing takes a moment)
2. Check `intake/new/` — is your file there? (If yes, processor is watching it)
3. Check `intake/failed/` — is your file there? (If yes, CSV format is wrong)
4. Check `intake/archive/` — is your file there? (If yes, data was clean—no problems found!)

---

### Problem: Browser can't reach http://localhost:5000

**You see:** "This site can't be reached" or connection error

**Solutions:**
1. Make sure the uploader terminal is still running (didn't close it?)
2. Make sure you see the "Running on" message in the terminal
3. Try refreshing the page (F5)
4. Try http://127.0.0.1:5000 instead
5. Check if port 5000 is in use (see "Address already in use" above)

---

### Problem: CSV file won't upload

**You see:** "No file selected" or file upload fails

**Solutions:**
1. Make sure file is CSV format (not XLS, XLSX, or JSON)
2. Make sure file is under 16 MB
3. Try a different CSV file
4. Check file naming (no special characters like `@`, `*`, etc.)

---

## What's Next?

### For Operators (send them this):
- Read [README.md](README.md) (5 minutes)
- Read [OPERATOR_MANUAL.md](OPERATOR_MANUAL.md) (30 minutes)
- Keep [QUICK_START.md](QUICK_START.md) at your desk (print it!)

### For Technical Maintenance:
- Read [ARCHITECTURE.md](docs/ARCHITECTURE.md) — Understand how it works
- Read [DEVELOPER.md](docs/DEVELOPER.md) — Maintain and update rules
- Check [CHANGELOG.md](docs/CHANGELOG.md) — Track version history

### For Management/Leadership:
- Read [README.md](README.md) — Understand the purpose
- Review [OPERATOR_MANUAL.md](OPERATOR_MANUAL.md) — Know what your team does
- Check on operators monthly — Ask about patterns and rule improvements

---

## Quick Command Reference

**Start the uploader:**
```bash
cd /Users/gautambiswas/Claude\ Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter
source .venv/bin/activate
python -m scripts.uploader.app
```

**Open the uploader:**
```
http://localhost:5000
```

**Check for flagged files:**
```bash
ls review/flagged/
```

**Deactivate virtual environment (when done):**
```bash
deactivate
```

---

## Common Questions

### Q: Can I run this on a different computer?

**A:** Yes! Follow the setup steps on that computer. The system is designed to run anywhere Python 3.8+ is available.

---

### Q: Can I use this without the web uploader?

**A:** Yes. Advanced users can drop CSV files directly into `intake/new/` folder without using the web form.

---

### Q: What happens if I close the uploader terminal?

**A:** The uploader stops. Files can't be uploaded until you restart it. Open a new terminal and run the command again.

---

### Q: How do I update the system?

**A:** 
1. New rules files are auto-discovered (drop into `config/rules/`)
2. Code updates require git pull or manual file replacement
3. See [DEVELOPER.md](docs/DEVELOPER.md) for maintenance

---

### Q: Can multiple people upload at the same time?

**A:** Yes. The uploader can handle multiple users. The processor will queue files automatically.

---

### Q: Where are the donation records actually stored?

**A:** They're stored as CSV files in the `intake/` and `review/` folders. No database. Everything is files, which you can back up easily.

---

## Support

- **Operator questions?** → Point them to [OPERATOR_MANUAL.md](OPERATOR_MANUAL.md)
- **Technical issues?** → Check [Troubleshooting](#troubleshooting-setup-issues) above
- **Architecture/maintenance?** → Read [DEVELOPER.md](docs/DEVELOPER.md)
- **System overview?** → Read [ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## You're Done! 🎉

The system is now set up and tested. 

**Next:**
1. Show operators how to use it (point them to [OPERATOR_MANUAL.md](OPERATOR_MANUAL.md))
2. Run real uploads and monitor for issues
3. Collect operator feedback on rules
4. Improve rules as patterns emerge

Welcome to the Givebutter Donation Processor. Your data is about to get much cleaner! 📊

---

**Last updated:** May 25, 2026  
**Setup version:** 1.0

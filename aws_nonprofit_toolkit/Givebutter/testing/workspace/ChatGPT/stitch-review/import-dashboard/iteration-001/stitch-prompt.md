# Stitch Revision Prompt — Import Dashboard — Iteration 001

## Capture Failure: Wrong Screen

**No Stitch revision should be applied until the Import Dashboard preview is correctly captured.**

### Issue
The Stitch preview URL renders screen **"Q3 Donor Update_Final_v3.csv"** (node-id: `4d9abeed14714f3aa2202140280c81cb`), which is not the Householder Import Dashboard.

### Recapture Instructions
1. In Stitch, locate the **Import Dashboard** screen (v1 - not v2, not Export Console).
2. Note its screen ID (visible in Stitch URL bar as `node-id=...`).
3. Construct the preview URL:
   ```
   https://stitch.withgoogle.com/preview/9371274764538076058?node-id=<correct-screen-id>&raw=1
   ```
4. Provide the correct preview URL to Claude Code.
5. Re-run capture with correct URL.

### Once Correct Screen Is Captured
The capture-and-handoff workflow will resume with a fresh review for iteration-002.

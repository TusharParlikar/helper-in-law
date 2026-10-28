# Deploy the demo on Streamlit Community Cloud

A hosted copy of the web UI that clients can open in a browser to try the interface. It runs in verbatim mode (no local model on Streamlit's servers), with the full corpus shipped in the repo.

## What the repo already contains

| File | Purpose |
|---|---|
| `ui/app.py` | The app (entry point) |
| `ui/requirements.txt` | The UI's dependencies only; Streamlit Cloud reads this before `uv.lock` |
| `packages.txt` | DejaVu fonts for the PDF research report |
| `deploy/helperinlaw.db.gz` | The database (Constitution + 384 judgments, 31 MB); unpacked on first start |
| `.streamlit/config.toml` | Theme |

Judgment and Article links open the app's own reader (`?case=...`, `?statute=...`), so no API server is needed.

## Steps

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with the GitHub account that owns `TusharParlikar/helper-in-law`.
2. **Create app** -> **Deploy a public app from GitHub**:
   - Repository: `TusharParlikar/helper-in-law`
   - Branch: `main`
   - Main file path: `ui/app.py`
   - App URL: choose one, e.g. `helper-in-law`
3. **Advanced settings**:
   - Python version: **3.12**
   - Secrets:
     ```toml
     HIL_DEMO = "true"
     ```
     This gives every browser session its own answer style, so one client's choices don't change another's.
4. **Deploy**. The first start installs dependencies and unpacks the database (a few minutes); later visits open in seconds.

## Share it with clients only

1. Open the app's **Settings** -> **Sharing** -> **Only specific people can view this app**.
2. Click **Share**, enter each client's email, **Invite**. They get a link and sign in with Google or a one-time email link; they don't need a GitHub account.

Limits: one private app per account at a time, and invited viewers can invite others.

## Updating the data

After re-ingesting or rebuilding the index locally:

```bash
uv run python scripts/build_demo_db.py   # writes deploy/helperinlaw.db.gz
git add deploy/helperinlaw.db.gz && git commit -m "Refresh demo database" && git push
```

Then **Reboot** the app in Streamlit Cloud so it unpacks the new database.

## What clients get, and what they don't

- The full research flow: scenario -> governing Articles -> Supreme Court judgments with verified quotes, the judgment reader, Constitution lookup, the PDF research report, onboarding and answer styles.
- No AI drafting: the toggle is hidden because no local model runs on Streamlit's servers. Answers are the verbatim, verified passages (the measured default).
- Questions are processed on the demo server and not saved (history is off by default). Streamlit hosts the app; do not invite clients to enter confidential client facts.
- Not legal advice: it is a research aid over a limited corpus (Constitution of India + 384 Supreme Court judgments, 2014-2024).

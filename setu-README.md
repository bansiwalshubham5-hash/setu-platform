# Setu — Invoice Trust Score Platform

Predicts which manufacturing invoices will get repaid, using verified transaction data. No buyer cooperation needed.

## What it does
- Scores each invoice 0-100 based on buyer payment behavior
- Shows whether defaults cluster in low scores (the proof)
- Explains every score in plain English
- Maps buyer-level risk across a portfolio

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate sample data (200 auto-component invoices)
python generate_sample_data.py

# 3. Test the scoring engine
python test_scoring.py

# 4. Run the dashboard
streamlit run app.py
```

## Files
- `scoring_engine.py` — the core product (scoring logic)
- `app.py` — Streamlit dashboard
- `generate_sample_data.py` — creates realistic sample invoices
- `test_scoring.py` — verifies the score separates defaults
- `data/sample_invoices.csv` — 200 sample invoices

## Deploy to Streamlit Cloud (free)
1. Push this repo to GitHub
2. Go to share.streamlit.io
3. Connect your GitHub repo
4. Set main file path to `app.py`
5. Deploy

## Built by
A Physics student at IIT Bombay, researching MSME financing.

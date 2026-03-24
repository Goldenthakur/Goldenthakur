# Smart Expense Manager 💸

A lightweight Streamlit app for expense management with three input flows:

1. **Detect online spends** by importing a CSV bank/wallet statement.
2. **Add cash spends manually** through a simple form.
3. **Add spend from an audio note** (paste your transcribed voice note) and auto-categorize.

## Features

- Auto-categorization into:
  - Food & Dining
  - Groceries
  - Transport
  - Shopping
  - Entertainment
  - Bills & Utilities
  - Health
  - Rent & Housing
  - Other
- Online/Cash split dashboard metrics.
- Transaction table and CSV export.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## CSV format for online spends

Upload a CSV with these columns (case-insensitive):

- `date`
- `description`
- `amount`

Example:

```csv
date,description,amount
2026-03-20,UPI payment to Swiggy,452
2026-03-21,Amazon order #123,1299
```

## Audio note input

For now, the app expects a **transcribed** audio sentence in text, such as:

- `Spent 250 on Uber ride to office`
- `Paid 430 for dinner at restaurant`

The app extracts amount and category from the text automatically.

## Notes

- This is a starter MVP designed to be easy to extend.
- Real-time bank sync and speech-to-text can be integrated next (for example via Plaid and Whisper APIs).

## Android support

Yes — this project can be used on Android phones, with two practical approaches:

1. **Fastest (recommended): run as a hosted Streamlit web app**
   - Deploy the app to a server (Streamlit Community Cloud, Render, AWS, etc.).
   - Open it in Chrome on Android and optionally **"Add to Home screen"** for an app-like shortcut.
   - Best choice for MVPs and frequent updates.

2. **App-store style wrapper: package a WebView shell**
   - Wrap the hosted URL in an Android WebView container (for example with Capacitor/Cordova/native Android).
   - Gives you an APK/AAB for Play Store distribution.
   - Useful if you need push notifications, app listing, or tighter mobile branding.

### Important limitations for Android

- Streamlit is a **web framework**, not a native Android framework.
- For a fully offline/native experience, rebuild the frontend in a mobile stack (Flutter/React Native/Kotlin) and keep this Python logic behind an API.

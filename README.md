# FasTradeX

Expiry scalping command centre for NSE Nifty weekly options — live signals, Max Pain/OI context, STT calculator, trade journal, and Razorpay subscriptions.

## Stack

- **Backend:** Python, FastAPI, SQLite, APScheduler
- **Frontend:** React, Vite
- **Payments:** Razorpay (optional — dev mode activates plans without keys)

## Quick start

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

API docs: http://127.0.0.1:8000/docs
Health: http://127.0.0.1:8000/health

The backend also serves the frontend at http://127.0.0.1:8000/dashboard.html when `frontend/` exists.

### 2. Frontend (optional separate static server)

```powershell
cd frontend
python -m http.server 5500
```

Open http://127.0.0.1:5500/dashboard.html (API base defaults to port 8000).

## First-time user flow

1. Open `/login.html` → register → use **dev OTP** shown in the UI if SMTP is not configured (`DEV_EXPOSE_OTP=true` in `.env`).
2. Verify email → log in.
3. Open `/auth_subscription.html` → choose a plan (dev mode upgrades tier without Razorpay).
4. Use **Dashboard** (5s spot / 60s signals), **Calculator**, and **Journal**.

## Configuration

| Variable           | Purpose                                      |
| ------------------ | -------------------------------------------- |
| `JWT_SECRET`     | Signing key for access tokens                |
| `RAZORPAY_*`     | Live/test payment keys and webhook secret    |
| `SMTP_*`         | Email OTP delivery                           |
| `DEV_EXPOSE_OTP` | Return OTP in API response when SMTP missing |

## Market data

Live NSE fetches run when the server can reach `nseindia.com`. Otherwise the API falls back to **demo** spot/OI so the UI still works off-hours or behind restrictive networks.

## Disclaimer

Educational tool only — not SEBI-registered investment advice.

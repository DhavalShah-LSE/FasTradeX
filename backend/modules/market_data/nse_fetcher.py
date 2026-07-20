from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any

import requests

from config import ATM_STRIKE_INTERVAL

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

_lock = threading.Lock()
_session: requests.Session | None = None
_cache: dict[str, Any] = {
    "spot": None,
    "oi": None,
    "vix": None,
    "spot_updated": None,
    "oi_updated": None,
    "vix_updated": None,
    "source": "demo",
}


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(NSE_HEADERS)
        try:
            _session.get("https://www.nseindia.com", timeout=10)
        except requests.RequestException:
            pass
    return _session


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _demo_spot() -> float:
    # Stable demo spot for off-market / blocked NSE
    base = 24150.0
    return round(base + (time.time() % 120) - 60, 2)


def fetch_nifty_spot() -> dict[str, Any]:
    with _lock:
        try:
            s = _get_session()
            r = s.get(
                "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050",
                timeout=12,
            )
            r.raise_for_status()
            data = r.json()
            spot = float(data["data"][0]["last"])
            _cache["spot"] = spot
            _cache["spot_updated"] = _now_iso()
            _cache["source"] = "nse"
            return {"spot": spot, "updated_at": _cache["spot_updated"], "source": "nse"}
        except Exception:
            spot = _demo_spot()
            _cache["spot"] = spot
            _cache["spot_updated"] = _now_iso()
            if _cache.get("source") != "nse":
                _cache["source"] = "demo"
            delayed = _cache.get("oi_updated") is None
            return {
                "spot": spot,
                "updated_at": _cache["spot_updated"],
                "source": _cache["source"],
                "delayed": delayed,
                "message": "Using demo/cached data — NSE unreachable from this network",
            }


def fetch_vix() -> dict[str, Any]:
    with _lock:
        try:
            s = _get_session()
            r = s.get("https://www.nseindia.com/api/allIndices", timeout=12)
            r.raise_for_status()
            for item in r.json().get("data", []):
                if item.get("index") == "INDIA VIX":
                    vix = float(item.get("last", 0))
                    _cache["vix"] = vix
                    _cache["vix_updated"] = _now_iso()
                    return {"vix": vix, "updated_at": _cache["vix_updated"], "source": "nse"}
        except Exception:
            pass
        vix = _cache.get("vix") or 14.2
        _cache["vix"] = vix
        _cache["vix_updated"] = _now_iso()
        return {"vix": vix, "updated_at": _cache["vix_updated"], "source": _cache.get("source", "demo")}


def fetch_option_chain() -> dict[str, Any]:
    with _lock:
        try:
            s = _get_session()
            r = s.get(
                "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY",
                timeout=15,
            )
            r.raise_for_status()
            payload = r.json()
            records = payload.get("records", {})
            spot = float(records.get("underlyingValue") or _cache.get("spot") or _demo_spot())
            strikes = []
            for row in records.get("data", []):
                strike = row.get("strikePrice")
                ce = row.get("CE") or {}
                pe = row.get("PE") or {}
                strikes.append(
                    {
                        "strike": strike,
                        "ce_oi": ce.get("openInterest") or 0,
                        "pe_oi": pe.get("openInterest") or 0,
                        "ce_change_oi": ce.get("changeinOpenInterest") or 0,
                        "pe_change_oi": pe.get("changeinOpenInterest") or 0,
                        "ce_ltp": ce.get("lastPrice"),
                        "pe_ltp": pe.get("lastPrice"),
                    }
                )
            result = {
                "spot": spot,
                "expiry_dates": records.get("expiryDates", []),
                "strikes": strikes,
                "updated_at": _now_iso(),
                "source": "nse",
            }
            _cache["oi"] = result
            _cache["oi_updated"] = result["updated_at"]
            _cache["source"] = "nse"
            return result
        except Exception:
            spot = _cache.get("spot") or _demo_spot()
            atm = round(spot / ATM_STRIKE_INTERVAL) * ATM_STRIKE_INTERVAL
            demo_strikes = []
            for i in range(-5, 6):
                st = atm + i * ATM_STRIKE_INTERVAL
                demo_strikes.append(
                    {
                        "strike": st,
                        "ce_oi": max(1000, 50000 - abs(i) * 8000),
                        "pe_oi": max(1000, 45000 - abs(i) * 7000),
                        "ce_change_oi": -500 if i == 0 else 100,
                        "pe_change_oi": 200,
                        "ce_ltp": max(5.0, 45 - abs(i) * 8),
                        "pe_ltp": max(5.0, 40 - abs(i) * 7),
                    }
                )
            result = {
                "spot": spot,
                "expiry_dates": [],
                "strikes": demo_strikes,
                "updated_at": _now_iso(),
                "source": "demo",
                "message": "Demo OI chain — configure NSE access for live data",
            }
            _cache["oi"] = result
            _cache["oi_updated"] = result["updated_at"]
            return result


def get_cached_snapshot() -> dict[str, Any]:
    return {
        "spot": _cache.get("spot"),
        "vix": _cache.get("vix"),
        "oi": _cache.get("oi"),
        "source": _cache.get("source"),
    }

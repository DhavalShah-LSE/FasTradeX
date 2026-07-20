"""Index definitions for multi-index support (Nifty live; others stubbed)."""

INDICES = {
    "NIFTY": {
        "symbol": "NIFTY",
        "name": "Nifty 50",
        "lot_size": 75,
        "strike_interval": 50,
        "expiry_weekday": "tuesday",
        "tier_required": "basic",
    },
    "BANKNIFTY": {
        "symbol": "BANKNIFTY",
        "name": "Bank Nifty",
        "lot_size": 30,
        "strike_interval": 100,
        "expiry_weekday": "wednesday",
        "tier_required": "pro",
    },
    "FINNIFTY": {
        "symbol": "FINNIFTY",
        "name": "Fin Nifty",
        "lot_size": 65,
        "strike_interval": 50,
        "expiry_weekday": "tuesday",
        "tier_required": "pro",
    },
    "MIDCPNIFTY": {
        "symbol": "MIDCPNIFTY",
        "name": "Midcap Nifty",
        "lot_size": 120,
        "strike_interval": 25,
        "expiry_weekday": "monday",
        "tier_required": "pro",
    },
}

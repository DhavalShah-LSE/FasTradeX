from __future__ import annotations

from datetime import datetime
from typing import Any

from modules.market_data.max_pain import atm_strike, compute_max_pain, oi_crossover_bullish
from windows import current_window


def score_signals(
    spot: float,
    chain: dict[str, Any],
    vix: float,
    range_high: float | None = None,
    volume_spike: bool | None = None,
) -> dict[str, Any]:
    strikes = chain.get("strikes") or []
    mp = compute_max_pain(strikes)
    max_pain = mp.get("max_pain")
    pcr = mp.get("pcr")
    window = current_window()

    flags = {
        "above_max_pain": bool(max_pain is not None and spot > max_pain),
        "above_range_high": bool(range_high is not None and spot > range_high),
        "pcr_bullish": bool(pcr is not None and pcr > 1.2),
        "oi_crossover": oi_crossover_bullish(strikes, mp.get("resistance_strike")),
        "vix_low": vix < 18,
        "in_window": window is not None,
        "volume_spike": bool(volume_spike),
    }

    weights = window.signal_weights if window else {k: 1.0 for k in flags}
    raw = sum(weights.get(k, 1.0) for k, v in flags.items() if v)
    max_raw = sum(weights.get(k, 1.0) for k in flags)
    score = round(7 * (raw / max_raw), 2) if max_raw else 0.0

    if score >= 5:
        label = "STRONG"
        color = "green"
        recommendation = "Favourable buyer setup — confirm plan & size before entry"
    elif score >= 3:
        label = "WEAK"
        color = "yellow"
        recommendation = "Mixed signals — wait for clearer confluence"
    else:
        label = "NO TRADE"
        color = "red"
        recommendation = "Stay flat — conditions do not meet expiry scalp criteria"

    min_required = window.min_score if window else 4.0
    trade_ok = score >= min_required and flags["in_window"]

    return {
        "score": score,
        "max_score": 7,
        "label": label,
        "color": color,
        "recommendation": recommendation,
        "trade_ok": trade_ok,
        "min_score_required": min_required,
        "active_window": window.id if window else None,
        "signals": flags,
        "weights_used": weights,
        "max_pain": max_pain,
        "pcr": pcr,
        "resistance_strike": mp.get("resistance_strike"),
        "support_strike": mp.get("support_strike"),
        "atm_strike": atm_strike(spot),
        "spot": spot,
        "vix": vix,
        "computed_at": datetime.now().isoformat(),
    }

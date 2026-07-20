from __future__ import annotations

from typing import Any


def compute_max_pain(strikes: list[dict[str, Any]]) -> dict[str, Any]:
    if not strikes:
        return {"max_pain": None, "total_oi_ce": 0, "total_oi_pe": 0}

    strike_prices = sorted({s["strike"] for s in strikes if s.get("strike") is not None})
    if not strike_prices:
        return {"max_pain": None, "total_oi_ce": 0, "total_oi_pe": 0}

    min_pain = None
    max_pain_strike = strike_prices[0]
    for candidate in strike_prices:
        pain = 0.0
        for row in strikes:
            k = row["strike"]
            ce_oi = float(row.get("ce_oi") or 0)
            pe_oi = float(row.get("pe_oi") or 0)
            pain += max(0, candidate - k) * ce_oi
            pain += max(0, k - candidate) * pe_oi
        if min_pain is None or pain < min_pain:
            min_pain = pain
            max_pain_strike = candidate

    total_ce = sum(float(s.get("ce_oi") or 0) for s in strikes)
    total_pe = sum(float(s.get("pe_oi") or 0) for s in strikes)
    pcr = (total_pe / total_ce) if total_ce else None

    resistance = max(strikes, key=lambda s: float(s.get("ce_oi") or 0))
    support = max(strikes, key=lambda s: float(s.get("pe_oi") or 0))

    return {
        "max_pain": max_pain_strike,
        "pcr": round(pcr, 3) if pcr is not None else None,
        "total_oi_ce": int(total_ce),
        "total_oi_pe": int(total_pe),
        "resistance_strike": resistance.get("strike"),
        "support_strike": support.get("strike"),
    }


def atm_strike(spot: float, interval: int = 50) -> int:
    return int(round(spot / interval) * interval)


def oi_crossover_bullish(strikes: list[dict[str, Any]], resistance_strike: float | None) -> bool:
    if resistance_strike is None:
        return False
    for row in strikes:
        if row.get("strike") == resistance_strike:
            change = float(row.get("ce_change_oi") or 0)
            oi = float(row.get("ce_oi") or 1)
            return change < 0 and abs(change) > 0.05 * oi
    return False

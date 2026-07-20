from __future__ import annotations

from typing import Any

from config import BROKERAGE_ROUND_TRIP, NIFTY_LOT_SIZE, OTHER_CHARGES


def calculate_exit_pnl(
    entry_premium: float,
    exit_premium: float,
    lots: int,
    nifty_at_exit: float | None,
    strike: float,
    option_type: str,
    is_expiry_day: bool = True,
) -> dict[str, Any]:
    lot_size = NIFTY_LOT_SIZE
    gross = (exit_premium - entry_premium) * lots * lot_size

    # STT on sell of options (simplified per project docs)
    contract_value = (nifty_at_exit or strike) * lot_size * lots
    premium_value = exit_premium * lot_size * lots
    if is_expiry_day and nifty_at_exit is not None:
        if option_type.upper() == "CE" and nifty_at_exit > strike:
            stt = 0.00125 * contract_value
        elif option_type.upper() == "PE" and nifty_at_exit < strike:
            stt = 0.00125 * contract_value
        else:
            stt = 0.001 * premium_value
    else:
        stt = 0.001 * premium_value

    brokerage = BROKERAGE_ROUND_TRIP
    other = OTHER_CHARGES
    net = gross - stt - brokerage - other
    capital_deployed = entry_premium * lot_size * lots
    net_pct = (net / capital_deployed * 100) if capital_deployed else 0

    return {
        "gross_pnl": round(gross, 2),
        "stt": round(stt, 2),
        "brokerage": brokerage,
        "other_charges": other,
        "net_pnl": round(net, 2),
        "net_pnl_pct": round(net_pct, 2),
    }


def capital_buckets(total_capital: float) -> dict[str, float]:
    return {
        "trading_60pct": round(total_capital * 0.6, 2),
        "reserve_30pct": round(total_capital * 0.3, 2),
        "cost_buffer_10pct": round(total_capital * 0.1, 2),
        "max_risk_5pct": round(total_capital * 0.05, 2),
    }

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Any


@dataclass(frozen=True)
class TradingWindow:
    id: str
    name: str
    start: time
    end: time
    risk: str
    min_score: float
    audience: str
    description: str
    tips: list[str]
    indicators: list[str]
    signal_weights: dict[str, float]


WINDOWS: list[TradingWindow] = [
    TradingWindow(
        id="orb",
        name="ORB — Opening Range Breakout",
        start=time(9, 0),
        end=time(10, 0),
        risk="HIGH",
        min_score=4.5,
        audience="Experienced traders",
        description="First breakout after open; fast premiums.",
        tips=["Wait for 9:15 candle close", "Hard exit by 10:00 AM"],
        indicators=["VWAP", "EMA 9/21"],
        signal_weights={
            "above_max_pain": 0.8,
            "above_range_high": 1.2,
            "pcr_bullish": 0.7,
            "oi_crossover": 1.0,
            "vix_low": 0.9,
            "in_window": 1.0,
            "volume_spike": 1.3,
        },
    ),
    TradingWindow(
        id="midday",
        name="Midday Reversal",
        start=time(11, 45),
        end=time(13, 15),
        risk="MEDIUM",
        min_score=4.0,
        audience="Intermediate traders",
        description="Mean reversion after morning move.",
        tips=["Fib 61.8% retracement zone", "Lower premiums — good for small capital"],
        indicators=["VWAP", "Fib 61.8%", "RSI 14"],
        signal_weights={
            "above_max_pain": 1.0,
            "above_range_high": 0.8,
            "pcr_bullish": 1.0,
            "oi_crossover": 0.9,
            "vix_low": 1.0,
            "in_window": 1.0,
            "volume_spike": 0.8,
        },
    ),
    TradingWindow(
        id="expiry_rush",
        name="Expiry Rush — Gamma Blast",
        start=time(13, 30),
        end=time(14, 30),
        risk="MEDIUM",
        min_score=4.0,
        audience="Beginners and all levels",
        description="Classic expiry scalp; max pain gravity strongest.",
        tips=["Exit before STT danger at 3:00 PM", "Max Pain + OI crossover combo"],
        indicators=["Max Pain", "OI Crossover", "VWAP"],
        signal_weights={
            "above_max_pain": 1.2,
            "above_range_high": 1.0,
            "pcr_bullish": 1.1,
            "oi_crossover": 1.3,
            "vix_low": 1.0,
            "in_window": 1.1,
            "volume_spike": 1.0,
        },
    ),
    TradingWindow(
        id="last_hour",
        name="Last Hour Squeeze",
        start=time(14, 30),
        end=time(15, 15),
        risk="VERY HIGH",
        min_score=5.0,
        audience="Experienced traders",
        description="Final hour gamma sensitivity; STT trap risk max.",
        tips=["Hard exit before 3:10 PM", "Not for beginners"],
        indicators=["VWAP", "Max Pain"],
        signal_weights={
            "above_max_pain": 1.0,
            "above_range_high": 1.1,
            "pcr_bullish": 0.9,
            "oi_crossover": 1.2,
            "vix_low": 0.8,
            "in_window": 1.0,
            "volume_spike": 1.4,
        },
    ),
]


def current_window(now: datetime | None = None) -> TradingWindow | None:
    now = now or datetime.now()
    t = now.time()
    for w in WINDOWS:
        if w.start <= t <= w.end:
            return w
    return None


def window_to_dict(w: TradingWindow) -> dict[str, Any]:
    return {
        "id": w.id,
        "name": w.name,
        "start": w.start.isoformat(),
        "end": w.end.isoformat(),
        "risk": w.risk,
        "min_score": w.min_score,
        "audience": w.audience,
        "description": w.description,
        "tips": w.tips,
        "indicators": w.indicators,
    }


def list_windows() -> list[dict[str, Any]]:
    return [window_to_dict(w) for w in WINDOWS]

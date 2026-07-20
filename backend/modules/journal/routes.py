import csv
import io
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from db import get_connection, row_to_dict
from modules.auth.dependencies import CurrentUser, get_current_user
from modules.journal.pnl import calculate_exit_pnl, capital_buckets
from modules.subscriptions.feature_gate import require_feature
from windows import current_window

router = APIRouter(prefix="/journal", tags=["journal"])


class TradeEntry(BaseModel):
    expiry_date: str | None = None
    trade_date: str | None = None
    entry_time: str | None = None
    nifty_at_entry: float | None = None
    strike: float
    option_type: str = Field(pattern="^(CE|PE|ce|pe)$")
    entry_premium: float
    lots: int = Field(default=1, ge=1, le=10)
    stop_loss: float | None = None
    target: float | None = None
    max_pain_at_entry: float | None = None
    vix_at_entry: float | None = None
    pcr_at_entry: float | None = None
    oi_signal: str | None = None
    signal_score: float | None = None
    atm_or_otm: str | None = None
    range_high: float | None = None
    range_low: float | None = None
    trading_window: str | None = None
    emotional_state_entry: str | None = None
    trade_mode: str = "real"
    followed_plan: bool | None = None
    revenge_trade: bool = False
    notes: str | None = None


class TradeExit(BaseModel):
    exit_premium: float
    exit_time: str | None = None
    nifty_at_exit: float | None = None
    exit_reason: str | None = None


@router.get("/capital-calculator")
async def calc_capital(total: float = Query(..., gt=0)):
    return capital_buckets(total)


@router.post("/trade")
async def create_trade(
    body: TradeEntry,
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    require_feature(user.tier, "journal")
    w = current_window()
    trade_date = body.trade_date or datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO trades (
                user_id, expiry_date, trade_date, entry_time, nifty_at_entry,
                strike, option_type, entry_premium, lots, stop_loss, target,
                max_pain_at_entry, vix_at_entry, pcr_at_entry, oi_signal,
                signal_score, atm_or_otm, range_high, range_low, trading_window,
                emotional_state_entry, trade_mode, followed_plan, revenge_trade, notes
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                user.id,
                body.expiry_date,
                trade_date,
                body.entry_time or datetime.now().strftime("%H:%M:%S"),
                body.nifty_at_entry,
                body.strike,
                body.option_type.upper(),
                body.entry_premium,
                body.lots,
                body.stop_loss,
                body.target,
                body.max_pain_at_entry,
                body.vix_at_entry,
                body.pcr_at_entry,
                body.oi_signal,
                body.signal_score,
                body.atm_or_otm,
                body.range_high,
                body.range_low,
                body.trading_window or (w.id if w else None),
                body.emotional_state_entry,
                body.trade_mode,
                1 if body.followed_plan else 0 if body.followed_plan is not None else None,
                1 if body.revenge_trade else 0,
                body.notes,
            ),
        )
        conn.commit()
        trade_id = cur.lastrowid
        row = conn.execute("SELECT * FROM trades WHERE id = ?", (trade_id,)).fetchone()
    return {"trade": row_to_dict(row)}


@router.patch("/trade/{trade_id}/exit")
async def exit_trade(
    trade_id: int,
    body: TradeExit,
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    require_feature(user.tier, "journal")
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM trades WHERE id = ? AND user_id = ?",
            (trade_id, user.id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Trade not found")
        if row["exit_premium"] is not None:
            raise HTTPException(status_code=400, detail="Trade already closed")
        pnl = calculate_exit_pnl(
            entry_premium=row["entry_premium"],
            exit_premium=body.exit_premium,
            lots=row["lots"],
            nifty_at_exit=body.nifty_at_exit,
            strike=row["strike"],
            option_type=row["option_type"],
        )
        conn.execute(
            """
            UPDATE trades SET
                exit_premium = ?, exit_time = ?, nifty_at_exit = ?, exit_reason = ?,
                gross_pnl = ?, stt = ?, brokerage = ?, other_charges = ?,
                net_pnl = ?, net_pnl_pct = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                body.exit_premium,
                body.exit_time or datetime.now().strftime("%H:%M:%S"),
                body.nifty_at_exit,
                body.exit_reason,
                pnl["gross_pnl"],
                pnl["stt"],
                pnl["brokerage"],
                pnl["other_charges"],
                pnl["net_pnl"],
                pnl["net_pnl_pct"],
                trade_id,
            ),
        )
        conn.commit()
        updated = conn.execute("SELECT * FROM trades WHERE id = ?", (trade_id,)).fetchone()
    return {"trade": row_to_dict(updated), "pnl": pnl}


@router.get("/trades")
async def list_trades(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    trade_mode: str | None = None,
):
    require_feature(user.tier, "journal")
    query = "SELECT * FROM trades WHERE user_id = ?"
    params: list[Any] = [user.id]
    if trade_mode:
        query += " AND trade_mode = ?"
        params.append(trade_mode)
    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return {"trades": [row_to_dict(r) for r in rows]}


@router.get("/analytics/summary")
async def analytics_summary(user: Annotated[CurrentUser, Depends(get_current_user)]):
    require_feature(user.tier, "journal_analytics")
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM trades
            WHERE user_id = ? AND net_pnl IS NOT NULL
            """,
            (user.id,),
        ).fetchall()
    trades = [row_to_dict(r) for r in rows]
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0,
            "avg_net_pnl": 0,
            "total_net_pnl": 0,
            "best_window": None,
            "emotion_stats": {},
            "plan_discipline": {},
            "graduation": {"current_capital_tier": "10k", "next_milestone": "25k"},
        }

    wins = [t for t in trades if (t["net_pnl"] or 0) > 0]
    win_rate = round(len(wins) / len(trades) * 100, 2)
    avg_pnl = round(sum(t["net_pnl"] or 0 for t in trades) / len(trades), 2)
    total_pnl = round(sum(t["net_pnl"] or 0 for t in trades), 2)

    by_window: dict[str, list[float]] = {}
    for t in trades:
        w = t.get("trading_window") or "unknown"
        by_window.setdefault(w, []).append(t["net_pnl"] or 0)
    best_window = max(by_window, key=lambda k: sum(by_window[k]) / len(by_window[k]))

    emotion_stats: dict[str, dict[str, float]] = {}
    for t in trades:
        emo = t.get("emotional_state_entry") or "unknown"
        emotion_stats.setdefault(emo, {"count": 0, "wins": 0})
        emotion_stats[emo]["count"] += 1
        if (t["net_pnl"] or 0) > 0:
            emotion_stats[emo]["wins"] += 1
    for emo, stat in emotion_stats.items():
        stat["win_rate"] = round(stat["wins"] / stat["count"] * 100, 2)

    followed = [t for t in trades if t.get("followed_plan") == 1]
    not_followed = [t for t in trades if t.get("followed_plan") == 0]
    plan_discipline = {
        "followed_win_rate": round(
            len([t for t in followed if (t["net_pnl"] or 0) > 0]) / len(followed) * 100, 2
        )
        if followed
        else None,
        "broken_plan_win_rate": round(
            len([t for t in not_followed if (t["net_pnl"] or 0) > 0]) / len(not_followed) * 100, 2
        )
        if not_followed
        else None,
    }

    profitable_expiry_streak = 0
    for t in sorted(trades, key=lambda x: x["trade_date"], reverse=True):
        if (t["net_pnl"] or 0) > 0:
            profitable_expiry_streak += 1
        else:
            break

    graduation = {
        "profitable_streak": profitable_expiry_streak,
        "next_milestone": "25k"
        if profitable_expiry_streak < 8
        else "50k"
        if total_pnl < 50000
        else "1L",
        "message": "8 consecutive profitable expiries → eligible to scale toward ₹25K capital",
    }

    return {
        "total_trades": len(trades),
        "win_rate": win_rate,
        "avg_net_pnl": avg_pnl,
        "total_net_pnl": total_pnl,
        "best_window": best_window,
        "emotion_stats": emotion_stats,
        "plan_discipline": plan_discipline,
        "graduation": graduation,
    }


@router.get("/export.csv")
async def export_csv(user: Annotated[CurrentUser, Depends(get_current_user)]):
    require_feature(user.tier, "journal")
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM trades WHERE user_id = ? ORDER BY id",
            (user.id,),
        ).fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="No trades to export")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    for row in rows:
        writer.writerow(dict(row))
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=fastradex_trades.csv"},
    )

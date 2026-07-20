from typing import Annotated

from fastapi import APIRouter, Depends, Query

from modules.auth.dependencies import CurrentUser, get_optional_user
from modules.market_data import nse_fetcher
from modules.market_data.max_pain import compute_max_pain
from modules.market_data.signal_engine import score_signals
from modules.subscriptions.feature_gate import require_feature
from windows import current_window, list_windows

router = APIRouter(prefix="/api", tags=["market"])


@router.get("/windows")
async def trading_windows():
    return {"windows": list_windows(), "active": current_window().id if current_window() else None}


@router.get("/spot")
async def spot():
    return nse_fetcher.fetch_nifty_spot()


@router.get("/vix")
async def vix():
    return nse_fetcher.fetch_vix()


@router.get("/oi")
async def oi_chain(user: Annotated[CurrentUser | None, Depends(get_optional_user)] = None):
    if user:
        require_feature(user.tier, "dashboard")
    chain = nse_fetcher.fetch_option_chain()
    analytics = compute_max_pain(chain.get("strikes") or [])
    return {**chain, **analytics}


@router.get("/signals")
async def signals(
    user: Annotated[CurrentUser | None, Depends(get_optional_user)] = None,
    range_high: float | None = Query(default=None),
    volume_spike: bool | None = Query(default=None),
):
    if user:
        require_feature(user.tier, "signals")
    spot_data = nse_fetcher.fetch_nifty_spot()
    vix_data = nse_fetcher.fetch_vix()
    chain = nse_fetcher.fetch_option_chain()
    spot = float(spot_data["spot"])
    vix = float(vix_data["vix"])
    result = score_signals(spot, chain, vix, range_high=range_high, volume_spike=volume_spike)
    result["data_source"] = chain.get("source", "unknown")
    result["window"] = current_window().id if current_window() else None
    return result

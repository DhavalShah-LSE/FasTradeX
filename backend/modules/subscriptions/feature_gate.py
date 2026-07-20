from fastapi import HTTPException

from modules.subscriptions.plans import FEATURE_MIN_TIER, TIER_RANK


def require_feature(user_tier: str, feature: str) -> None:
    tier = (user_tier or "free").lower()
    required = FEATURE_MIN_TIER.get(feature, "basic")
    if TIER_RANK.get(tier, 0) < TIER_RANK.get(required, 1):
        raise HTTPException(
            status_code=403,
            detail=f"Upgrade required for '{feature}' (need {required} plan or higher)",
        )


def tier_has_feature(user_tier: str, feature: str) -> bool:
    try:
        require_feature(user_tier, feature)
        return True
    except HTTPException:
        return False

"""Style profiles: storage, versioned updates, and feedback-driven suggestions (never applied
silently)."""

from typing import Any

from helperinlaw.core.store import Store
from helperinlaw.core.types import STYLE_FIELDS, Profile


def update_profile(store: Store, profile_id: str, changes: dict[str, Any]) -> Profile:
    """Only style fields may change (§5.4); anything else is rejected, not ignored."""
    bad = set(changes) - STYLE_FIELDS
    if bad:
        raise ValueError(f"not a style setting: {sorted(bad)}")
    current = store.get_profile(profile_id)
    merged = Profile.model_validate(
        {
            **current.model_dump(),
            **changes,
            "profile_id": profile_id,
            "version": current.version + 1,
        }
    )
    store.put_profile(merged)
    return merged


def apply_style(profile: Profile, patch: dict[str, Any]) -> Profile:
    """One-off per-request override. Doesn't persist."""
    clean = {k: v for k, v in patch.items() if k in STYLE_FIELDS}
    return Profile.model_validate({**profile.model_dump(), **clean})


def suggest_setting(store: Store, profile_id: str) -> str | None:
    """Looks at recent feedback and proposes a change. The user decides."""
    profile = store.get_profile(profile_id)
    reasons = [f["reason"] for f in store.recent_feedback(profile_id, 5)]
    if reasons.count("too_long") >= 3 and profile.depth != "quick":
        return "You often find answers too long. Switch your default depth to Quick?"
    if reasons.count("too_technical") >= 3 and profile.tone == "technical":
        return "You often find answers too technical. Switch your tone to Plain English?"
    if reasons.count("too_short") >= 3 and profile.depth != "deep":
        return "You often want more detail. Switch your default depth to Deep?"
    return None

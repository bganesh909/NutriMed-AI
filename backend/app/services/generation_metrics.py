"""
Records the outcome of every AI plan generation.

The accuracy safeguards degrade quietly by design: if the model misbehaves,
verification drops what it produced and a template fallback takes over, and the
user still receives a sensible plan. That is the right behaviour, but it means
a deployment can serve template plans to every user for weeks without anyone
noticing the LLM is broken.

Each generation therefore writes one small document recording what actually
happened, so the fallback rate and drop rate are observable in production
rather than buried in worker logs.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger("nutrimed.metrics")

COLLECTION = "generation_metrics"

#: Outcomes, most to least healthy.
OUTCOME_LLM_VERIFIED = "llm_verified"  # model output used, passed verification
OUTCOME_LLM_REPAIRED = "llm_repaired"  # used, but some items were dropped
OUTCOME_FALLBACK = "template_fallback"  # model output unusable; template served
OUTCOME_FAILED = "failed"  # nothing could be produced


def record_generation(
    db,
    *,
    kind: str,
    outcome: str,
    user_id: str | None = None,
    report_id: str | None = None,
    dropped: list[str] | None = None,
    reasons: list[str] | None = None,
    model: str | None = None,
) -> None:
    """
    Write one generation outcome. Synchronous (pymongo), for Celery workers.

    Never raises: metrics must not be able to fail a user's plan generation.
    """
    try:
        db[COLLECTION].insert_one(_metric_doc(kind, outcome, user_id, report_id, dropped, reasons, model))
    except Exception:
        logger.warning("Could not record generation metrics", exc_info=True)


async def record_generation_async(
    db,
    *,
    kind: str,
    outcome: str,
    user_id: str | None = None,
    report_id: str | None = None,
    dropped: list[str] | None = None,
    reasons: list[str] | None = None,
    model: str | None = None,
) -> None:
    """`record_generation` for request handlers (motor). Never raises."""
    try:
        await db[COLLECTION].insert_one(_metric_doc(kind, outcome, user_id, report_id, dropped, reasons, model))
    except Exception:
        logger.warning("Could not record generation metrics", exc_info=True)


def _metric_doc(kind, outcome, user_id, report_id, dropped, reasons, model) -> dict[str, Any]:
    return {
        "kind": kind,  # "diet" | "workout" | "analysis"
        "outcome": outcome,
        "user_id": user_id,
        "report_id": report_id,
        "dropped": (dropped or [])[:20],
        "reasons": (reasons or [])[:10],
        "model": model,
        "created_at": datetime.now(UTC),
    }


async def summarise(db, days: int = 7) -> dict[str, Any]:
    """
    Aggregate recent outcomes for the health/monitoring endpoint (motor).

    A high `template_fallback` share means the LLM is effectively not
    contributing and should be investigated.
    """
    since = datetime.now(UTC) - timedelta(days=days)
    summary: dict[str, Any] = {"window_days": days, "kinds": {}}

    try:
        cursor = db[COLLECTION].aggregate(
            [
                {"$match": {"created_at": {"$gte": since}}},
                {"$group": {"_id": {"kind": "$kind", "outcome": "$outcome"}, "n": {"$sum": 1}}},
            ]
        )
        async for row in cursor:
            kind = row["_id"]["kind"]
            outcome = row["_id"]["outcome"]
            summary["kinds"].setdefault(kind, {})[outcome] = row["n"]
    except Exception:
        logger.warning("Could not summarise generation metrics", exc_info=True)
        return {**summary, "available": False}

    for counts in summary["kinds"].values():
        total = sum(counts.values())
        fallbacks = counts.get(OUTCOME_FALLBACK, 0) + counts.get(OUTCOME_FAILED, 0)
        counts["total"] = total
        counts["fallback_rate"] = round(fallbacks / total, 3) if total else 0.0

    summary["available"] = True
    return summary

"""
Progress tracking service -- log body metrics over time and compute trends.
"""

from datetime import datetime, timezone
from typing import Optional

from app.repositories.progress_repository import ProgressRepository


class ProgressService:
    def __init__(self, progress_repo: ProgressRepository) -> None:
        self.progress_repo = progress_repo

    async def log_progress(self, user_id: str, data: dict) -> dict:
        doc = {
            "user_id": user_id,
            "weight_kg": data.get("weight_kg"),
            "body_fat_pct": data.get("body_fat_pct"),
            "waist_cm": data.get("waist_cm"),
            "hip_cm": data.get("hip_cm"),
            "neck_cm": data.get("neck_cm"),
            "notes": data.get("notes", ""),
            "recorded_at": datetime.now(timezone.utc),
        }
        return await self.progress_repo.create(doc)

    async def get_history(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        entries = await self.progress_repo.get_history(
            user_id, start_date=start_date, end_date=end_date
        )
        total = len(entries)
        trends = self._compute_trends(entries)
        return {"entries": entries, "total": total, "trends": trends}

    async def get_latest(self, user_id: str) -> Optional[dict]:
        return await self.progress_repo.get_latest(user_id)

    @staticmethod
    def _compute_trends(entries: list[dict]) -> dict:
        """
        Compute simple trends from progress entries (oldest -> newest).
        Returns change and direction for weight and body fat.
        """
        if len(entries) < 2:
            return {}

        # entries are sorted newest-first from the repo
        newest = entries[0]
        oldest = entries[-1]

        trends: dict = {}
        for field in ("weight_kg", "body_fat_pct", "waist_cm"):
            new_val = newest.get(field)
            old_val = oldest.get(field)
            if new_val is not None and old_val is not None:
                change = round(new_val - old_val, 2)
                if change > 0:
                    direction = "increasing"
                elif change < 0:
                    direction = "decreasing"
                else:
                    direction = "stable"
                trends[field] = {
                    "first_value": old_val,
                    "latest_value": new_val,
                    "change": change,
                    "direction": direction,
                    "entries_count": len(entries),
                }
        return trends

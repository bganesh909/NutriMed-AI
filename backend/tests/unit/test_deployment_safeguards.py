"""
Tests for the safeguards that keep generated output trustworthy in production.

This service degrades quietly: with a broken dataset or an unreachable model it
still answers requests and still returns plans, just template ones for every
user. These cover the machinery that makes that visible.
"""

import pytest

from app.services import grounding_selfcheck as sc
from app.services.generation_metrics import (
    OUTCOME_FALLBACK,
    OUTCOME_LLM_REPAIRED,
    OUTCOME_LLM_VERIFIED,
    summarise,
)


class TestGroundingSelfCheck:
    def test_passes_on_a_healthy_deployment(self):
        report = sc.check_grounding_data()
        assert report["ok"], report["problems"]
        assert report["foods"] >= sc.MIN_FOODS
        assert report["exercises"] >= sc.MIN_EXERCISES

    def test_detects_truncated_food_database(self, monkeypatch):
        import app.data.food_database as fd
        monkeypatch.setattr(fd, "FOOD_DATABASE", fd.FOOD_DATABASE[:5])
        report = sc.check_grounding_data()
        assert not report["ok"]
        assert any("food database has only" in p for p in report["problems"])

    def test_detects_missing_food_categories(self, monkeypatch):
        import app.data.food_database as fd
        proteins = [f for f in fd.FOOD_DATABASE if f["category"] == "protein"]
        monkeypatch.setattr(fd, "FOOD_DATABASE", proteins * 20)
        report = sc.check_grounding_data()
        assert not report["ok"]
        assert any("missing categories" in p for p in report["problems"])

    def test_detects_exercises_without_form_instructions(self, monkeypatch):
        import app.data.exercise_database as ed
        stripped = [{**e, "instructions": ""} for e in ed.EXERCISE_DATABASE[:3]]
        monkeypatch.setattr(ed, "EXERCISE_DATABASE", stripped + list(ed.EXERCISE_DATABASE[3:]))
        report = sc.check_grounding_data()
        assert not report["ok"]
        assert any("form instructions" in p for p in report["problems"])

    def test_never_raises_even_when_data_is_nonsense(self, monkeypatch):
        import app.data.exercise_database as ed
        monkeypatch.setattr(ed, "EXERCISE_DATABASE", [])
        report = sc.check_grounding_data()
        assert report["ok"] is False
        assert isinstance(report["problems"], list)


@pytest.mark.asyncio
class TestGenerationMetrics:
    async def test_summarise_reports_fallback_rate(self, test_db):
        from app.services.generation_metrics import COLLECTION, record_generation

        # record_generation is sync (pymongo in Celery); insert directly here.
        docs = (
            [{"kind": "diet", "outcome": OUTCOME_LLM_VERIFIED}] * 6
            + [{"kind": "diet", "outcome": OUTCOME_LLM_REPAIRED}] * 2
            + [{"kind": "diet", "outcome": OUTCOME_FALLBACK}] * 2
        )
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        await test_db[COLLECTION].insert_many([{**d, "created_at": now} for d in docs])

        summary = await summarise(test_db, days=7)
        assert summary["available"] is True
        diet = summary["kinds"]["diet"]
        assert diet["total"] == 10
        assert diet["fallback_rate"] == pytest.approx(0.2)

    async def test_summarise_is_empty_without_data(self, test_db):
        summary = await summarise(test_db, days=7)
        assert summary["kinds"] == {}
        assert summary["available"] is True

    async def test_recording_never_raises_on_a_broken_db(self):
        from app.services.generation_metrics import record_generation

        class Broken:
            def __getitem__(self, name):
                raise RuntimeError("mongo is down")

        # Must not propagate: metrics cannot be allowed to fail a user's plan.
        record_generation(Broken(), kind="diet", outcome=OUTCOME_FALLBACK)


@pytest.mark.asyncio
class TestReadinessEndpoint:
    async def test_liveness_stays_cheap_and_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_readiness_reports_grounding_and_dependencies(self, client):
        resp = await client.get("/health/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in ("ready", "degraded")
        assert body["checks"]["grounding"]["foods"] >= sc.MIN_FOODS
        # Whatever the environment, the shape must be reportable.
        assert "llm" in body["checks"]
        assert "ocr" in body["checks"]

    async def test_readiness_flags_degraded_grounding(self, client, monkeypatch):
        import app.data.food_database as fd
        monkeypatch.setattr(fd, "FOOD_DATABASE", fd.FOOD_DATABASE[:2])
        resp = await client.get("/health/ready")
        body = resp.json()
        assert body["status"] == "degraded"
        assert "grounding" in body["degraded"]


def test_env_example_parses():
    """Copying .env.example to .env (the documented setup) must give a working config."""
    from pathlib import Path

    from app.core.config import Settings

    example = Path(__file__).resolve().parents[3] / ".env.example"
    settings = Settings(_env_file=example)
    assert settings.ALLOWED_ORIGINS
    assert all(origin.startswith("http") for origin in settings.ALLOWED_ORIGINS)

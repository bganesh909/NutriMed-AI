"""CORS must wrap every other middleware (see the note in app/main.py)."""

from starlette.middleware.cors import CORSMiddleware

from app.main import app
from app.middleware.rate_limiting import RateLimitingMiddleware


def test_cors_is_outermost():
    # user_middleware[0] is the outermost layer.
    assert app.user_middleware[0].cls is CORSMiddleware


def test_rate_limiter_runs_inside_cors():
    classes = [m.cls for m in app.user_middleware]
    assert classes.index(CORSMiddleware) < classes.index(RateLimitingMiddleware)

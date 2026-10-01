"""Web API tests. No network: providers are disabled by default."""
from fastapi.testclient import TestClient

from core.config import Config
from web.app import create_app
from web.ratelimit import DailyCounter, SlidingWindowLimiter
from web.settings import WebSettings


def make_client(**kw):
    settings = WebSettings(**kw)
    return TestClient(create_app(settings, Config()))


def test_lookup_returns_metadata_risk_and_dorks():
    r = make_client().post("/api/lookup", json={"number": "+442083661177"})
    assert r.status_code == 200
    data = r.json()
    assert data["metadata"]["e164"] == "+442083661177"
    assert data["risk"]["level"] == "LOW"
    assert data["dorks"] and set(data["dorks"][0]["urls"]) == {
        "google", "duckduckgo", "bing"}
    assert r.headers["cache-control"] == "no-store"


def test_security_headers_present():
    r = make_client().get("/")
    assert r.status_code == 200
    assert "script-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["x-content-type-options"] == "nosniff"


def test_rate_limit_per_ip_returns_429_with_retry_after():
    c = make_client(rate_limit=2, rate_window=60)
    body = {"number": "+442083661177"}
    assert c.post("/api/lookup", json=body).status_code == 200
    assert c.post("/api/lookup", json=body).status_code == 200
    r = c.post("/api/lookup", json=body)
    assert r.status_code == 429 and int(r.headers["retry-after"]) >= 1


def test_global_limit_enforced():
    c = make_client(rate_limit=100, global_limit=1)
    body = {"number": "+442083661177"}
    assert c.post("/api/lookup", json=body).status_code == 200
    assert c.post("/api/lookup", json=body).status_code == 429


def test_validation_errors():
    c = make_client()
    assert c.post("/api/lookup", json={"number": "x"}).status_code == 422
    assert c.post("/api/lookup", json={"number": "+442083661177",
                                       "region": "ZZ"}).status_code == 422
    assert c.post("/api/lookup", json={"number": "+442083661177",
                                       "categories": ["nope"]}).status_code == 422
    assert c.post("/api/lookup", json={"number": "1" * 500}).status_code == 422


def test_number_never_accepted_via_get():
    assert make_client().get("/api/lookup?number=+442083661177"
                             ).status_code == 405


def test_docs_disabled():
    c = make_client()
    assert c.get("/docs").status_code == 404
    assert c.get("/openapi.json").status_code == 404


def test_xff_ignored_unless_proxy_trusted():
    c = make_client(rate_limit=1, trusted_proxy_hops=0)
    body = {"number": "+442083661177"}
    assert c.post("/api/lookup", json=body,
                  headers={"x-forwarded-for": "1.1.1.1"}).status_code == 200
    # spoofed header must NOT give a fresh bucket
    assert c.post("/api/lookup", json=body,
                  headers={"x-forwarded-for": "2.2.2.2"}).status_code == 429


def test_limiter_window_and_daily_counter():
    t = [0.0]
    lim = SlidingWindowLimiter(1, 10, clock=lambda: t[0])
    assert lim.allow("a")[0] and not lim.allow("a")[0]
    t[0] = 11
    assert lim.allow("a")[0]
    d = DailyCounter(1)
    assert d.take() and not d.take()

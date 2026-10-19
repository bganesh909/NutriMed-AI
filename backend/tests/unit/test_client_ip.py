"""
The visitor's address behind a hosting proxy (app/middleware/client_ip.py).

The rate limiter keys anonymous requests (sign-in, sign-up, password reset)
on this address, so it must be the visitor's and must not be choosable by the
visitor.
"""

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.middleware.client_ip import ClientIPMiddleware, address_from_header


def _echo(request: Request) -> JSONResponse:
    return JSONResponse({"client": request.client.host if request.client else None, "scheme": request.url.scheme})


def _client(header: str = "", hops: int = 1) -> TestClient:
    app = Starlette(routes=[Route("/", _echo)])
    app.add_middleware(ClientIPMiddleware, header=header, hops=hops)
    # TestClient connects as "testclient", standing in for the proxy's address.
    return TestClient(app)


class TestAddressFromHeader:
    def test_single_value(self):
        assert address_from_header(["198.51.100.7"], 1) == "198.51.100.7"

    def test_reads_from_the_right(self):
        assert address_from_header(["203.0.113.9, 198.51.100.7"], 1) == "198.51.100.7"
        assert address_from_header(["203.0.113.9, 198.51.100.7, 10.0.0.2"], 2) == "198.51.100.7"

    def test_repeated_header_lines_form_one_list(self):
        assert address_from_header(["203.0.113.9", "198.51.100.7"], 1) == "198.51.100.7"

    def test_fewer_entries_than_hops(self):
        assert address_from_header(["198.51.100.7"], 2) is None
        assert address_from_header([], 1) is None

    def test_rejects_values_that_are_not_addresses(self):
        assert address_from_header(["unknown"], 1) is None
        assert address_from_header(["198.51.100.7:4711"], 1) is None

    def test_normalises_ipv6(self):
        assert address_from_header(["2001:DB8:0:0:0:0:0:1"], 1) == "2001:db8::1"


class TestClientIPMiddleware:
    def test_does_nothing_unless_configured(self):
        headers = {"X-Forwarded-For": "203.0.113.9", "CF-Connecting-IP": "203.0.113.9", "X-Forwarded-Proto": "https"}
        response = _client().get("/", headers=headers)
        assert response.json() == {"client": "testclient", "scheme": "http"}

    def test_uses_the_configured_header(self):
        response = _client("CF-Connecting-IP").get(
            "/", headers={"CF-Connecting-IP": "198.51.100.7", "X-Forwarded-For": "203.0.113.9"}
        )
        assert response.json()["client"] == "198.51.100.7"

    def test_client_supplied_forwarded_for_entries_are_ignored(self):
        # The visitor sent 203.0.113.9 itself; the proxy appended the real address.
        response = _client("X-Forwarded-For").get("/", headers={"X-Forwarded-For": "203.0.113.9, 198.51.100.7"})
        assert response.json()["client"] == "198.51.100.7"

    def test_keeps_the_connecting_address_when_the_header_is_missing_or_bad(self):
        client = _client("CF-Connecting-IP")
        # Not uvicorn's choice of the leftmost X-Forwarded-For entry, which the visitor controls.
        assert client.get("/", headers={"X-Forwarded-For": "203.0.113.9"}).json()["client"] == "testclient"
        assert client.get("/", headers={"CF-Connecting-IP": "not-an-ip"}).json()["client"] == "testclient"

    def test_takes_the_scheme_the_visitor_used(self):
        client = _client("CF-Connecting-IP")
        assert client.get("/", headers={"X-Forwarded-Proto": "https"}).json()["scheme"] == "https"
        assert client.get("/", headers={"X-Forwarded-Proto": "https, http"}).json()["scheme"] == "https"
        assert client.get("/", headers={"X-Forwarded-Proto": "gopher"}).json()["scheme"] == "http"

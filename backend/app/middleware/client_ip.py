"""
Client address behind a hosting proxy.

The rate limiter and the audit log use ``request.client.host``. Behind a
platform proxy (Render, ...) that is the proxy's own address, shared by every
visitor, so all of them would share one rate limit. With ``CLIENT_IP_HEADER``
set, this middleware takes the visitor's address from that header instead.

Proxies add to list headers such as X-Forwarded-For after whatever the client
sent, so the address is read ``hops`` entries from the right: a client cannot
pick its own address by sending the header. If the header is missing or
malformed the connecting address is kept, which is never client-controlled.

The proxy also says whether the visitor used HTTPS (X-Forwarded-Proto), so
redirects the API builds keep https. This replaces uvicorn's own proxy-header
handling, which trusts the leftmost (client-supplied) X-Forwarded-For entry;
do not combine it with uvicorn's ``--forwarded-allow-ips``.
"""

import ipaddress

from starlette.types import ASGIApp, Receive, Scope, Send


def address_from_header(values: list[str], hops: int) -> str | None:
    """The valid IP address `hops` entries from the right of a (possibly repeated) list header."""
    entries = [entry.strip() for value in values for entry in value.split(",") if entry.strip()]
    if len(entries) < hops:
        return None
    try:
        return str(ipaddress.ip_address(entries[-hops]))
    except ValueError:
        return None


class ClientIPMiddleware:
    """Set the request's client address and scheme from headers a trusted proxy sets."""

    def __init__(self, app: ASGIApp, header: str = "", hops: int = 1) -> None:
        self.app = app
        # ASGI header names are lower-case bytes.
        self.header = header.strip().lower().encode("latin-1")
        self.hops = max(1, hops)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self.header or scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        values = [value.decode("latin-1") for name, value in scope["headers"] if name == self.header]
        scope = dict(scope)
        address = address_from_header(values, self.hops)
        if address:
            port = scope["client"][1] if scope.get("client") else 0
            scope["client"] = (address, port)

        for name, value in scope["headers"]:
            if name == b"x-forwarded-proto":
                # The scheme the visitor used is the first entry.
                proto = value.decode("latin-1").split(",")[0].strip().lower()
                if proto in ("http", "https"):
                    scope["scheme"] = proto.replace("http", "ws") if scope["type"] == "websocket" else proto
                break

        await self.app(scope, receive, send)

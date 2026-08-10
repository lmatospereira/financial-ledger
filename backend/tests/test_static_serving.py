"""Tests for the SPA catch-all static file route in main.py."""
from pathlib import Path

import pytest

_FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

# The catch-all route is only mounted when frontend/dist exists (see
# main.py) -- CI's backend-tests job never builds the frontend (that's
# frontend-build's job, run separately), so this route isn't registered
# there and any path just 404s instead of exercising the fix. Only
# meaningful to run where the frontend is actually built, same condition
# the app itself uses.
pytestmark = pytest.mark.skipif(
    not _FRONTEND_DIST.is_dir(),
    reason="frontend/dist not built -- the SPA catch-all route isn't mounted",
)


def test_path_traversal_falls_back_to_index_html(client):
    """SECURITY regression test.

    The catch-all route used to join `full_path` straight onto
    `_frontend_dist` without resolving/containing it, so a request like
    `/../../../../../../proc/self/environ` let an unauthenticated caller
    read arbitrary files off the container's filesystem via FileResponse.
    This was caught being actively probed by a scanner in production.

    Percent-encode the dot segments (%2e%2e) rather than writing literal
    ".." in the URL: httpx's own client-side URL normalization (RFC 3986
    dot-segment removal) collapses a literal ".." before the request is
    even sent, which would make this test pass regardless of the server-side
    fix and silently not exercise the vulnerable code path at all. A real
    scanner/attacker (and the one caught in prod) percent-encodes for
    exactly this reason: uvicorn/Starlette percent-decode path params
    server-side, after any client/proxy-level normalization already ran.
    Confirmed this reproduces the original leak against the pre-fix code
    (returned actual /etc/passwd contents) before adding the fix.

    Any traversal attempt must fall back to index.html (200, same as any
    other unknown client-side route), never leak file contents from
    outside frontend/dist.
    """
    response = client.get("/%2e%2e/%2e%2e/%2e%2e/%2e%2e/%2e%2e/%2e%2e/etc/passwd")
    assert response.status_code == 200
    assert "root:" not in response.text
    assert response.headers["content-type"].startswith("text/html")

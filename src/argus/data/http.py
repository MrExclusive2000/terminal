"""
Shared HTTP fetch with the politeness every provider adapter needs.

Retry with jittered exponential backoff, a declared User-Agent (SEC requires
one and will serve a block page without it), and a hard cap on attempts so a
dead provider degrades instead of hanging the caller.
"""
from __future__ import annotations

import random
import time
import urllib.error
import urllib.request

USER_AGENT = "argus-terminal/0.1 (single-user personal research)"


class FetchError(RuntimeError):
    pass


def get(url: str, *, timeout: float = 60.0, attempts: int = 4,
        backoff: float = 1.5, headers: dict[str, str] | None = None,
        user_agent: str | None = USER_AGENT) -> str:
    """GET `url` as text, retrying transient failures.

    Retries timeouts, 429 and 5xx. Does not retry 4xx other than 429 - a 404
    is an answer, not a hiccup.

    `user_agent` is per-adapter on purpose. SEC EDGAR *requires* a declared
    identifying UA and serves a block page without one. Other hosts have no
    such rule, and some corporate proxies and CDNs stall on unrecognised UAs -
    observed against FRED from behind an inspecting proxy, where the default
    urllib UA returned in 0.4s and a custom one timed out at 25s. Pass None to
    send no custom UA.
    """
    hdrs: dict[str, str] = {}
    if user_agent:
        hdrs["User-Agent"] = user_agent
    if headers:
        hdrs.update(headers)

    last: Exception | None = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code != 429 and exc.code < 500:
                raise FetchError(f"{url} -> HTTP {exc.code}") from exc
        except Exception as exc:  # noqa: BLE001 - timeouts, resets, DNS
            last = exc

        if attempt < attempts - 1:
            delay = (backoff ** attempt) + random.uniform(0, 0.75)
            time.sleep(delay)

    raise FetchError(f"{url} failed after {attempts} attempts: {last}")

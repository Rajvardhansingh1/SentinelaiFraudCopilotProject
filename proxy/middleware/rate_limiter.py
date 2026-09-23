import time
from collections import defaultdict

from proxy.config import settings

# ponytail: in-process counter, single-worker demo deployment assumed.
# Upgrade to a shared store (redis) if the proxy ever runs multi-worker.
_session_counts: dict[str, int] = defaultdict(int)


def check_and_increment(session_id: str, limit: int | None = None) -> bool:
    """Returns True if the call is allowed, False if the session is over quota."""
    cap = limit if limit is not None else settings.rate_limit_per_session
    if _session_counts[session_id] >= cap:
        return False
    _session_counts[session_id] += 1
    return True


def remaining(session_id: str, limit: int | None = None) -> int:
    cap = limit if limit is not None else settings.rate_limit_per_session
    return max(0, cap - _session_counts[session_id])


def reset(session_id: str | None = None) -> None:
    if session_id is None:
        _session_counts.clear()
    else:
        _session_counts.pop(session_id, None)


# Phase 12 (D-059): fixed-window rate limiting for signup/login — unlike
# check_and_increment() above (which never decays, fine for a one-run demo
# session), auth attempts need a window that actually expires, or a shared
# IP (NAT, office network) would eventually be locked out permanently.
_window_counts: dict[str, tuple[float, int]] = {}


def check_auth_rate_limit(key: str, limit: int, window_seconds: int) -> bool:
    """Returns True if allowed, False if `key` (e.g. client IP) is over
    `limit` attempts within the current `window_seconds` window."""
    now = time.monotonic()
    window_start, count = _window_counts.get(key, (now, 0))
    if now - window_start >= window_seconds:
        window_start, count = now, 0
    if count >= limit:
        _window_counts[key] = (window_start, count)
        return False
    _window_counts[key] = (window_start, count + 1)
    return True


def reset_auth_rate_limit() -> None:
    _window_counts.clear()

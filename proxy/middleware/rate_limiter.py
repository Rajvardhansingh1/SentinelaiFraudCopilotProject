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

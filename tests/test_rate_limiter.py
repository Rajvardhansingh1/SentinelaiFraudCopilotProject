from proxy.middleware import rate_limiter


def test_allows_up_to_limit_then_blocks():
    rate_limiter.reset("s1")
    for _ in range(3):
        assert rate_limiter.check_and_increment("s1", limit=3) is True
    assert rate_limiter.check_and_increment("s1", limit=3) is False


def test_sessions_are_independent():
    rate_limiter.reset()
    assert rate_limiter.check_and_increment("a", limit=1) is True
    assert rate_limiter.check_and_increment("b", limit=1) is True

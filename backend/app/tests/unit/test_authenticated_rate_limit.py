import uuid

from app.services.rate_limit import ai_user_rate_limiter


def test_authenticated_rate_limit_state_reset_is_clean():
    identity = str(uuid.uuid4())
    for _ in range(10):
        assert ai_user_rate_limiter.check(identity).allowed
    assert not ai_user_rate_limiter.check(identity).allowed

    ai_user_rate_limiter.reset_for_tests()
    assert ai_user_rate_limiter.check(identity).allowed

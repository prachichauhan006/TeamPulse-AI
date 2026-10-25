import uuid

import pytest

from app.core.security import (
    TokenValidationError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)


def test_argon2_password_hashing_and_verification():
    password = "StrongPassword123!"
    password_hash = hash_password(password)
    assert password_hash != password
    assert password_hash.startswith("$argon2")
    assert verify_password(password, password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_access_token_round_trip_and_type_enforcement():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    payload = decode_token(token, "access")
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"
    with pytest.raises(TokenValidationError):
        decode_token(token, "refresh")


def test_refresh_token_contains_unique_id_and_hashes_are_deterministic():
    user_id = uuid.uuid4()
    first, first_id, _ = create_refresh_token(user_id)
    second, second_id, _ = create_refresh_token(user_id)
    assert first_id != second_id
    assert first != second
    assert hash_token(first) == hash_token(first)
    assert hash_token(first) != hash_token(second)
    assert len(hash_token(first)) == 64


def test_malformed_token_is_rejected():
    with pytest.raises(TokenValidationError):
        decode_token("not-a-jwt", "access")

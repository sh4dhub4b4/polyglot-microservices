from uuid import uuid4
from use_cases.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)


class TestAuthService:

    def test_hash_and_verify_password(self):
        hashed = hash_password("mysecret")
        assert hashed != "mysecret"
        assert verify_password("mysecret", hashed) is True
        assert verify_password("wrong", hashed) is False

    def test_create_and_decode_token(self):
        user_id = uuid4()
        token = create_access_token(user_id, "student", uuid4())
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["role"] == "student"

    def test_invalid_token_returns_none(self):
        assert decode_access_token("invalid.jwt.token") is None
        assert decode_access_token("") is None

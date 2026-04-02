from app.auth.utils import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_and_verify():
    plain = "StrongPass123!"
    hashed = hash_password(plain)

    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("wrong-pass", hashed)


def test_jwt_create_and_decode():
    token, expires_in = create_access_token("user_abc123")
    payload = decode_access_token(token)

    assert expires_in > 0
    assert payload["sub"] == "user_abc123"

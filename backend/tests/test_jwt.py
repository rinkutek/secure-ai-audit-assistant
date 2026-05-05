import pytest
from app.core.security import create_access_token, decode_and_validate_jwt
from app.core.exceptions import AppError
import time

def test_jwt_roundtrip():
    t = create_access_token(user_id="u1", roles=["auditor"])
    p = decode_and_validate_jwt(t, expected_type="access")
    assert p["sub"] == "u1"
    assert "auditor" in p["roles"]

def test_jwt_expired():
    # Manually create a token that expired 1 hour ago
    import jwt
    from app.core.config import settings
    now = int(time.time())
    payload = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "sub": "u1",
        "roles": ["auditor"],
        "iat": now - 7200,
        "exp": now - 3600,
        "typ": "access",
    }
    t = jwt.encode(payload, settings.jwt_signing_key, algorithm="HS256")
    
    with pytest.raises(AppError) as e:
        decode_and_validate_jwt(t, expected_type="access")
    assert e.value.code == "JWT_EXPIRED"

def test_jwt_invalid_signature():
    t = create_access_token(user_id="u1", roles=["auditor"])
    t_invalid = t[:-5] + "aaaaa"
    with pytest.raises(AppError) as e:
        decode_and_validate_jwt(t_invalid, expected_type="access")
    assert e.value.code == "JWT_INVALID"


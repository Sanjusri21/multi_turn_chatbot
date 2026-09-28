import pytest
from fastapi import HTTPException
from app.services.auth_service import AuthService
from app.schemas.auth_schema import UserSignupRequest, UserLoginRequest
from app.core.security import decode_access_token

def test_user_signup_and_login(test_db):
    auth_service = AuthService(test_db)

    # 1. Signup
    signup_req = UserSignupRequest(
        name="Sanju",
        email="sanju.test@example.com",
        password="SecurePassword123!"
    )
    token_resp = auth_service.signup(signup_req)
    assert token_resp.access_token is not None
    assert token_resp.user.name == "Sanju"
    assert token_resp.user.email == "sanju.test@example.com"

    payload = decode_access_token(token_resp.access_token)
    assert payload["sub"] == token_resp.user.id

    # 2. Duplicate signup should raise 400
    with pytest.raises(HTTPException) as exc:
        auth_service.signup(signup_req)
    assert exc.value.status_code == 400

    # 3. Successful login
    login_resp = auth_service.login(UserLoginRequest(
        email="sanju.test@example.com",
        password="SecurePassword123!"
    ))
    assert login_resp.access_token is not None
    assert login_resp.user.id == token_resp.user.id

    # 4. Wrong password login should raise 401
    with pytest.raises(HTTPException) as exc:
        auth_service.login(UserLoginRequest(
            email="sanju.test@example.com",
            password="WrongPassword999!"
        ))
    assert exc.value.status_code == 401

def test_password_change(test_db, test_user):
    auth_service = AuthService(test_db)

    # Wrong current password fails
    with pytest.raises(HTTPException):
        auth_service.change_password(test_user.id, "WrongCurrent!", "NewPassword456!")

    # Correct current password succeeds
    success = auth_service.change_password(test_user.id, "Password123!", "NewPassword456!")
    assert success is True

    # Login with new password
    login_resp = auth_service.login(UserLoginRequest(
        email=test_user.email,
        password="NewPassword456!"
    ))
    assert login_resp.user.id == test_user.id

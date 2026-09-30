import pytest
from fastapi import HTTPException
from app.services.auth_service import AuthService
from app.schemas.auth_schema import UserSignupRequest, UserLoginRequest
from app.core.security import decode_access_token
from app.models.user import User

def test_user_signup_and_login(test_db):
    auth_service = AuthService(test_db)

    # 1. Signup - New users must default to PENDING status
    signup_req = UserSignupRequest(
        name="Sanju",
        email="sanju.test@example.com",
        password="SecurePassword123!"
    )
    token_resp = auth_service.signup(signup_req)
    assert token_resp.access_token is not None
    assert token_resp.user.name == "Sanju"
    assert token_resp.user.email == "sanju.test@example.com"
    assert token_resp.user.account_status == "PENDING"
    assert token_resp.user.role == "USER"

    payload = decode_access_token(token_resp.access_token)
    assert payload["sub"] == token_resp.user.id

    # 2. Duplicate signup should raise 400
    with pytest.raises(HTTPException) as exc:
        auth_service.signup(signup_req)
    assert exc.value.status_code == 400

    # 3. Login while PENDING must be blocked with 403 Forbidden
    with pytest.raises(HTTPException) as exc:
        auth_service.login(UserLoginRequest(
            email="sanju.test@example.com",
            password="SecurePassword123!"
        ))
    assert exc.value.status_code == 403
    assert "pending approval" in exc.value.detail.lower()

    # 4. Once APPROVED by an admin, login must succeed
    db_user = test_db.query(User).filter(User.id == token_resp.user.id).first()
    db_user.account_status = "APPROVED"
    test_db.commit()

    login_resp = auth_service.login(UserLoginRequest(
        email="sanju.test@example.com",
        password="SecurePassword123!"
    ))
    assert login_resp.access_token is not None
    assert login_resp.user.id == token_resp.user.id
    assert login_resp.user.account_status == "APPROVED"

    # 5. Wrong password login should raise 401
    with pytest.raises(HTTPException) as exc:
        auth_service.login(UserLoginRequest(
            email="sanju.test@example.com",
            password="WrongPassword999!"
        ))
    assert exc.value.status_code == 401

    # 6. REJECTED status must be blocked with 403
    db_user.account_status = "REJECTED"
    test_db.commit()
    with pytest.raises(HTTPException) as exc:
        auth_service.login(UserLoginRequest(
            email="sanju.test@example.com",
            password="SecurePassword123!"
        ))
    assert exc.value.status_code == 403
    assert "rejected" in exc.value.detail.lower()

    # 7. SUSPENDED status must be blocked with 403
    db_user.account_status = "SUSPENDED"
    test_db.commit()
    with pytest.raises(HTTPException) as exc:
        auth_service.login(UserLoginRequest(
            email="sanju.test@example.com",
            password="SecurePassword123!"
        ))
    assert exc.value.status_code == 403
    assert "suspended" in exc.value.detail.lower()

    # 8. ADMIN role can log in regardless of status
    db_user.role = "ADMIN"
    test_db.commit()
    admin_login_resp = auth_service.login(UserLoginRequest(
        email="sanju.test@example.com",
        password="SecurePassword123!"
    ))
    assert admin_login_resp.access_token is not None
    assert admin_login_resp.user.role == "ADMIN"

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

import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db
from app.core.security import create_access_token
from app.models.user import User
from app.services.auth_service import AuthService
from app.schemas.auth_schema import UserSignupRequest

@pytest.fixture
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def test_admin_authorization_restrictions(client, test_db, test_user, admin_user):
    # Unauthenticated request to /api/admin/users -> 401
    res_unauth = client.get("/api/admin/users")
    assert res_unauth.status_code == 401

    # Standard APPROVED user -> 403 Forbidden
    user_token = create_access_token({"sub": test_user.id, "email": test_user.email})
    res_user = client.get("/api/admin/users", headers={"Authorization": f"Bearer {user_token}"})
    assert res_user.status_code == 403
    assert "admin access required" in res_user.json()["detail"].lower()

    # ADMIN user -> 200 OK
    admin_token = create_access_token({"sub": admin_user.id, "email": admin_user.email})
    res_admin = client.get("/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 200
    data = res_admin.json()
    assert isinstance(data, list)
    assert len(data) >= 2

def test_admin_approval_lifecycle(client, test_db, admin_user):
    admin_token = create_access_token({"sub": admin_user.id, "email": admin_user.email})
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create a new user (defaults to PENDING)
    auth_service = AuthService(test_db)
    new_user = auth_service.signup(UserSignupRequest(
        name="Candidate User",
        email="candidate@example.com",
        password="CandidatePassword123!"
    )).user
    assert new_user.account_status == "PENDING"

    # 2. Verify new user appears in /api/admin/users/pending
    res_pending = client.get("/api/admin/users/pending", headers=admin_headers)
    assert res_pending.status_code == 200
    pending_ids = [u["id"] for u in res_pending.json()]
    assert new_user.id in pending_ids

    # 3. Approve the user
    res_approve = client.post(f"/api/admin/users/{new_user.id}/approve", headers=admin_headers)
    assert res_approve.status_code == 200
    assert res_approve.json()["account_status"] == "APPROVED"
    assert res_approve.json()["approved_by"] == admin_user.id
    assert res_approve.json()["approved_at"] is not None

    # 4. Suspend the user
    res_suspend = client.post(f"/api/admin/users/{new_user.id}/suspend", headers=admin_headers)
    assert res_suspend.status_code == 200
    assert res_suspend.json()["account_status"] == "SUSPENDED"

    # 5. Restore the user
    res_restore = client.post(f"/api/admin/users/{new_user.id}/restore", headers=admin_headers)
    assert res_restore.status_code == 200
    assert res_restore.json()["account_status"] == "APPROVED"

    # 6. Reject the user
    res_reject = client.post(f"/api/admin/users/{new_user.id}/reject", headers=admin_headers)
    assert res_reject.status_code == 200
    assert res_reject.json()["account_status"] == "REJECTED"

    # 7. Admin cannot reject/suspend themselves
    res_self_reject = client.post(f"/api/admin/users/{admin_user.id}/reject", headers=admin_headers)
    assert res_self_reject.status_code == 400

    res_self_suspend = client.post(f"/api/admin/users/{admin_user.id}/suspend", headers=admin_headers)
    assert res_self_suspend.status_code == 400

def test_chat_protection_by_status(client, test_db, test_user):
    auth_service = AuthService(test_db)
    target_user = auth_service.signup(UserSignupRequest(
        name="Protected Tester",
        email="protected@example.com",
        password="Password123!"
    )).user

    token = create_access_token({"sub": target_user.id, "email": target_user.email})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. PENDING -> 403 Forbidden
    res_pending = client.post("/api/chat", json={"message": "Hello"}, headers=headers)
    assert res_pending.status_code == 403
    assert "pending approval" in res_pending.json()["detail"].lower()

    # Streaming also blocked for PENDING -> 403
    res_stream_pending = client.post("/api/chat/stream", json={"message": "Hello"}, headers=headers)
    assert res_stream_pending.status_code == 403

    # Conversations also blocked -> 403
    res_conv_pending = client.get("/api/conversations", headers=headers)
    assert res_conv_pending.status_code == 403

    # Memories also blocked -> 403
    res_mem_pending = client.get("/api/memories", headers=headers)
    assert res_mem_pending.status_code == 403

    # 2. REJECTED -> 403 Forbidden
    db_u = test_db.query(User).filter(User.id == target_user.id).first()
    db_u.account_status = "REJECTED"
    test_db.commit()

    res_rej = client.post("/api/chat", json={"message": "Hello"}, headers=headers)
    assert res_rej.status_code == 403
    assert "rejected" in res_rej.json()["detail"].lower()

    # 3. SUSPENDED -> 403 Forbidden
    db_u.account_status = "SUSPENDED"
    test_db.commit()

    res_susp = client.post("/api/chat", json={"message": "Hello"}, headers=headers)
    assert res_susp.status_code == 403
    assert "suspended" in res_susp.json()["detail"].lower()

    # 4. APPROVED -> 200 OK
    db_u.account_status = "APPROVED"
    test_db.commit()

    res_appr = client.post("/api/chat", json={"message": "Hello"}, headers=headers)
    assert res_appr.status_code == 200

    # Streaming works for APPROVED
    res_stream_appr = client.post("/api/chat/stream", json={"message": "Hello"}, headers=headers)
    assert res_stream_appr.status_code == 200
    assert "text/event-stream" in res_stream_appr.headers.get("content-type", "")

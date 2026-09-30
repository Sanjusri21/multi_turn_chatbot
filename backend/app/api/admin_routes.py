# USE: Import FastAPI APIRouter, query/path parameters, and HTTP dependency mechanisms.
# WHY: Declares admin API routes with dependency injection for database sessions and administrator authorization.
# HOW: APIRouter groups endpoints under '/admin' prefix with OpenAPI tags; Depends handles dependency injection.
from fastapi import APIRouter, Depends, HTTPException, Query, status

# USE: Import SQLAlchemy Session and List typing annotations.
# WHY: Types database session parameters and response collections for static verification.
# HOW: Session represents active DB connection; List hints array responses.
from sqlalchemy.orm import Session
from typing import List, Optional

# USE: Import database session dependency provider.
# WHY: Injects open SQLAlchemy session into route handlers.
# HOW: FastAPI dependency injection calls get_db generator.
from app.core.database import get_db

# USE: Import security dependency verifying that caller is an authenticated administrator.
# WHY: Protects all admin routes so only users with role="ADMIN" can execute user approvals or status changes.
# HOW: Decodes JWT, verifies user exists, and checks current_user.role == 'ADMIN'.
from app.core.security import get_current_admin_user

# USE: Import User ORM model and UserRepository for user persistence operations.
# WHY: Queries and updates user status records in the database.
# HOW: UserRepository methods handle queries and status commits.
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import UserResponse

# USE: Create APIRouter instance for administrator endpoints.
# WHY: Mounts all admin user approval and management routes under the /admin subpath.
# HOW: Prefixed with /admin; registered onto main FastAPI application.
router = APIRouter(prefix="/admin", tags=["Admin Management"])

# USE: Endpoint retrieving all registered users, with optional filter by account_status.
# WHY: Populates the Admin Dashboard tabs (Approved, Rejected, Suspended, All users).
# HOW: Validates caller is ADMIN, queries UserRepository.get_all(status), and serializes into List[UserResponse].
@router.get("/users", response_model=List[UserResponse])
def get_all_users(
    status: Optional[str] = Query(None, description="Filter users by account_status (PENDING, APPROVED, REJECTED, SUSPENDED)"),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    repo = UserRepository(db)
    users = repo.get_all(status=status)
    return [UserResponse.model_validate(u) for u in users]

# USE: Dedicated endpoint retrieving only users awaiting administrator review.
# WHY: Powers the 'Pending Requests' review queue on the Admin Dashboard.
# HOW: Queries UserRepository.get_pending() for accounts with account_status == 'PENDING'.
@router.get("/users/pending", response_model=List[UserResponse])
def get_pending_users(
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    repo = UserRepository(db)
    users = repo.get_pending()
    return [UserResponse.model_validate(u) for u in users]

# USE: Endpoint to approve a pending or suspended user account.
# WHY: Transitions account_status to APPROVED so the user can log in and access Zara chat and memory features.
# HOW: Updates user.account_status to APPROVED, sets approved_at timestamp, and records admin's user ID.
@router.post("/users/{user_id}/approve", response_model=UserResponse)
def approve_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    repo = UserRepository(db)
    user = repo.update_status(user_id=user_id, status="APPROVED", approved_by=current_admin.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    return UserResponse.model_validate(user)

# USE: Endpoint to reject a user registration request.
# WHY: Declines access for inappropriate or unauthorized signup requests.
# HOW: Sets user.account_status to REJECTED; blocks user from logging into Zara.
@router.post("/users/{user_id}/reject", response_model=UserResponse)
def reject_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot reject their own account."
        )
    repo = UserRepository(db)
    user = repo.update_status(user_id=user_id, status="REJECTED")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    return UserResponse.model_validate(user)

# USE: Endpoint to suspend an active user's account.
# WHY: Immediately revokes Zara chat access if a user violates rules or policies.
# HOW: Sets user.account_status to SUSPENDED; subsequent API calls from the user yield 403 Forbidden.
@router.post("/users/{user_id}/suspend", response_model=UserResponse)
def suspend_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot suspend their own account."
        )
    repo = UserRepository(db)
    user = repo.update_status(user_id=user_id, status="SUSPENDED")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    return UserResponse.model_validate(user)

# USE: Endpoint to restore a suspended or rejected user back to APPROVED status.
# WHY: Allows administrators to re-enable access after temporary suspension or mistaken rejection.
# HOW: Sets user.account_status to APPROVED with updated approved_at and approved_by.
@router.post("/users/{user_id}/restore", response_model=UserResponse)
def restore_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    repo = UserRepository(db)
    user = repo.update_status(user_id=user_id, status="APPROVED", approved_by=current_admin.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    return UserResponse.model_validate(user)

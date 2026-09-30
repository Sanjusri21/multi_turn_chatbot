"""
Admin Promotion Utility for MemoryBot / Zara.

Safely promotes an existing user account to ADMIN role and APPROVED status
without modifying passwords, touching secrets, or altering other accounts.
"""

import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Ensure backend directory is in Python path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Import all models to ensure SQLAlchemy mappers are properly registered
import app.models.user
import app.models.user_settings
import app.models.conversation
import app.models.message
import app.models.memory
import app.models.message_attachment
import app.models.message_feedback
import app.models.web_search_log

from app.core.database import SessionLocal
from app.models.user import User


def list_users(db):
    """Print all existing users with their current status."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    if not users:
        print("\nNo users found in the database.")
        return

    print("\nExisting Users in Database:")
    print("-" * 75)
    print(f"{'Email':<32} {'Name':<16} {'Role':<10} {'Status':<12}")
    print("-" * 75)
    for u in users:
        print(f"{u.email:<32} {(u.name or ''):<16} {u.role:<10} {u.account_status:<12}")
    print("-" * 75)


def promote_user_to_admin(email: str) -> bool:
    """
    Promote a specific user to ADMIN with APPROVED status.
    Modifies only the designated user account.
    """
    target_email = email.strip().lower()
    if not target_email:
        print("Error: Email cannot be empty.")
        return False

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == target_email).first()
        if not user:
            print(f"\n[ERROR] No user found with email: '{target_email}'")
            list_users(db)
            print("\nPlease ensure the user has signed up first before promoting.")
            return False

        # Apply promotion
        previous_role = user.role
        previous_status = user.account_status

        user.role = "ADMIN"
        user.account_status = "APPROVED"
        user.approved_at = datetime.now(timezone.utc)
        user.approved_by = "CLI_PROMOTION"

        db.commit()
        db.refresh(user)

        print("\n==================================================")
        print(" [SUCCESS] User Promoted to Administrator")
        print("==================================================")
        print(f" User ID:        {user.id}")
        print(f" Name:           {user.name}")
        print(f" Email:          {user.email}")
        print(f" Role:           {previous_role} -> {user.role}")
        print(f" Account Status: {previous_status} -> {user.account_status}")
        print(f" Approved At:    {user.approved_at}")
        print("==================================================")
        print("The user can now log in normally and access the Admin Dashboard (/admin).\n")
        return True

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Database transaction failed: {e}")
        return False
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Promote an existing user to ADMIN role and APPROVED status in MemoryBot/Zara."
    )
    parser.add_argument(
        "email",
        nargs="?",
        default=None,
        help="Email address of the user to promote to ADMIN."
    )
    parser.add_argument(
        "--email",
        dest="flag_email",
        default=None,
        help="Email address of the user to promote (flag format)."
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all registered users and their current statuses."
    )

    args = parser.parse_args()
    target_email = args.flag_email or args.email

    db = SessionLocal()
    try:
        if args.list or not target_email:
            list_users(db)
            if not target_email:
                print("\nUsage:")
                print("  python promote_admin.py <user_email>")
                print("  Example: python promote_admin.py user@example.com\n")
            return
    finally:
        db.close()

    if target_email:
        promote_user_to_admin(target_email)


if __name__ == "__main__":
    main()

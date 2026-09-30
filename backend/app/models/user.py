# USE: Import Python's built-in universally unique identifier (UUID) generation library.
# WHY: Generates collision-resistant 128-bit UUID strings used as primary keys for user records.
# HOW: uuid.uuid4() generates cryptographically random version 4 UUIDs converted to 36-character strings.
import uuid

# USE: Import datetime and timezone classes for date and timestamp arithmetic.
# WHY: Needed to generate timezone-aware UTC timestamps for user creation and modification fields.
# HOW: datetime.now(timezone.utc) captures the current system timestamp in UTC.
from datetime import datetime, timezone

# USE: Import core SQLAlchemy column types and descriptor primitives.
# WHY: Defines relational schema structures (columns, string limits, datetimes) in the database table.
# HOW: Column, String, and DateTime map Python attributes directly to SQL table column definitions.
from sqlalchemy import Column, String, DateTime

# USE: Import ORM relationship descriptor from SQLAlchemy ORM.
# WHY: Establishes bidirectional relationships and cascade lifecycle rules with child entities (conversations, memories, settings).
# HOW: relationship() configures SQLAlchemy's unit of work to automatically load or cascade delete related child rows.
from sqlalchemy.orm import relationship

# USE: Import the shared declarative base class from core database configuration.
# WHY: Registers this class with SQLAlchemy's metadata catalog so it can be mapped to an SQL table.
# HOW: Base maintains the registry of mapped classes and database metadata used by create_all().
from app.core.database import Base

# USE: Helper function returning current timestamp in UTC.
# WHY: Serves as a dynamic callable default for datetime column timestamps to avoid stale module-import-time timestamps.
# HOW: Invokes datetime.now(timezone.utc) each time a record is inserted or updated.
def utc_now():
    # USE: Return current timezone-aware UTC datetime instance.
    # WHY: Guarantees standardized UTC timestamps without local timezone skew.
    # HOW: Calls datetime.now passing timezone.utc.
    return datetime.now(timezone.utc)

# USE: SQLAlchemy ORM model class representing the 'users' database table.
# WHY: Models registered user accounts, credential storage, timestamps, and relational links.
# HOW: Inherits from Base, defining SQL columns as class attributes.
class User(Base):
    # USE: Specify the exact relational SQL table name.
    # WHY: Directs SQLAlchemy to create and query the table named "users" in the database.
    # HOW: __tablename__ attribute is inspected by SQLAlchemy metadata.
    __tablename__ = "users"

    # USE: Primary key column storing a 36-character UUID string.
    # WHY: Unique identifier for each user account avoiding sequential ID enumeration vulnerabilities.
    # HOW: String(36) column marked primary_key=True with default lambda generating uuid.uuid4().
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # USE: Column storing the user's human-readable display name.
    # WHY: Personalizes the chat experience and greets the user in the UI.
    # HOW: String(100) column with nullable=False enforcing required name on registration.
    name = Column(String(100), nullable=False)
    # USE: Column storing the user's unique login email address.
    # WHY: Acts as the primary user identification credential for authentication and lookups.
    # HOW: String(150) with unique=True preventing duplicate accounts and index=True for fast B-tree lookups.
    email = Column(String(150), unique=True, index=True, nullable=False)
    # USE: Column storing the salted and hashed password string (salt$hash).
    # WHY: Securely stores credentials so plaintext passwords are never saved.
    # HOW: String(255) column storing PBKDF2 hexadecimal digests.
    hashed_password = Column(String(255), nullable=False)
    # USE: Column storing the role of the user ('USER' or 'ADMIN').
    # WHY: Enforces role-based access control so only designated administrators can access the admin dashboard and approval APIs.
    # HOW: String(20) column defaulting to 'USER' on registration; only elevated accounts hold 'ADMIN'.
    role = Column(String(20), default="USER", nullable=False)
    # USE: Column tracking the account approval status ('PENDING', 'APPROVED', 'REJECTED', 'SUSPENDED').
    # WHY: Protects Zara by ensuring new registrations cannot access chat or memory features until approved by an admin.
    # HOW: String(20) column defaulting to 'PENDING'; updated by admin endpoints to 'APPROVED', 'REJECTED', or 'SUSPENDED'.
    account_status = Column(String(20), default="PENDING", nullable=False)
    # USE: Column recording the timestamp when the user account was approved.
    # WHY: Provides an audit trail of when the user was granted access.
    # HOW: DateTime column populated with utc_now() when approved, nullable=True for pending users.
    approved_at = Column(DateTime, nullable=True, default=None)
    # USE: Column recording the user ID of the administrator who approved this account.
    # WHY: Provides accountability and traceability for user approvals.
    # HOW: String(36) storing the admin's UUID string, nullable=True until approved.
    approved_by = Column(String(36), nullable=True, default=None)
    # USE: Timestamp column recording when the user registered.
    # WHY: Audit tracking and account creation history.
    # HOW: DateTime column populated with utc_now function on initial insert.
    created_at = Column(DateTime, default=utc_now, nullable=False)
    # USE: Timestamp column tracking the last account update.
    # WHY: Audit tracking for password changes, profile edits, and activity tracking.
    # HOW: DateTime column with onupdate=utc_now automatically refreshed by SQLAlchemy on changes.
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # USE: ORM relationship linking user to all their conversation sessions.
    # WHY: Enables navigation from user.conversations and deletes conversation history if the user is deleted.
    # HOW: Links to "Conversation" model, back-populates to user, cascades deletes to prevent orphaned threads.
    conversations = relationship(
        # USE: Target model name string.
        # WHY: String reference avoids circular import issues before Conversation is declared.
        # HOW: Resolved by SQLAlchemy at mapper configuration time.
        "Conversation",
        # USE: Reverse relationship attribute name on the Conversation model.
        # WHY: Allows bidirectional access (conversation.user and user.conversations).
        # HOW: Synchronizes state across both sides of the relationship.
        back_populates="user",
        # USE: Cascade deletion rule for child conversation records.
        # WHY: Deleting a user must clean up all their conversation threads automatically.
        # HOW: "all, delete-orphan" removes associated conversations when the parent User is deleted.
        cascade="all, delete-orphan"
    )

    # USE: ORM relationship linking user to their long-term memory facts.
    # WHY: Enables accessing user.memories and ensures memories are purged if user account is deleted.
    # HOW: Links to "Memory" model, back-populates to user, ordered alphabetically by category.
    memories = relationship(
        # USE: Target model name string for Memory entity.
        # WHY: String identifier resolves cleanly in declarative mapper.
        # HOW: Binds to Memory class definition.
        "Memory",
        # USE: Reverse relationship attribute name on Memory model.
        # WHY: Enables memory.user access.
        # HOW: Keeps relationship synchronization active.
        back_populates="user",
        # USE: Cascade deletion behavior for memories.
        # WHY: Removes orphan memory facts when user account is deleted.
        # HOW: "all, delete-orphan" cascades deletion.
        cascade="all, delete-orphan",
        # USE: Default ordering clause for retrieved memories.
        # WHY: Groups memories cleanly by category (e.g. preferences, facts) when loaded.
        # HOW: Generates SQL ORDER BY memory.category ASC.
        order_by="Memory.category.asc()"
    )

    # USE: One-to-one ORM relationship linking user to their personalized settings.
    # WHY: Connects user directly to their UserSettings record (theme, custom instructions, provider preference).
    # HOW: uselist=False instructs SQLAlchemy that this relationship returns a single instance, not a collection.
    settings = relationship(
        # USE: Target model name string for UserSettings entity.
        # WHY: Identifies the related settings table model.
        # HOW: Binds to UserSettings class.
        "UserSettings",
        # USE: Reverse relationship attribute name on UserSettings model.
        # WHY: Enables settings.user navigation.
        # HOW: Maps reciprocal property.
        back_populates="user",
        # USE: Restrict relationship collection to a scalar single instance.
        # WHY: Each user possesses exactly one settings profile.
        # HOW: Returns UserSettings instance directly instead of a list.
        uselist=False,
        # USE: Cascade deletion policy for user settings.
        # WHY: Removes setting row when parent user is removed.
        # HOW: Deletes associated UserSettings row automatically.
        cascade="all, delete-orphan"
    )
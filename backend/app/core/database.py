from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import Generator

from app.core.config import settings


# SQLite needs this for multi-threaded FastAPI access.
# PostgreSQL does not.
connect_args = (
    {"check_same_thread": False}
    if "sqlite" in settings.RESOLVED_DATABASE_URL
    else {}
)


engine = create_engine(
    settings.RESOLVED_DATABASE_URL,
    connect_args=connect_args,
    echo=False
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


Base = declarative_base()


def get_db() -> Generator:
    """Provide a database session for each request."""
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables and run SQLite-only migrations."""

    # Import ALL models before SQLAlchemy configures relationships.
    import app.models.user
    import app.models.user_settings
    import app.models.conversation
    import app.models.message
    import app.models.memory
    import app.models.message_attachment
    import app.models.message_feedback
    import app.models.web_search_log

    # Create tables for both SQLite and PostgreSQL.
    Base.metadata.create_all(bind=engine)


    # ---------------------------------------------------------
    # SQLite-only migrations
    # ---------------------------------------------------------
    if "sqlite" in settings.RESOLVED_DATABASE_URL:

        try:
            with engine.connect() as conn:

                # conversations.keywords
                result = conn.exec_driver_sql(
                    "PRAGMA table_info(conversations)"
                )
                conversation_columns = [
                    row[1] for row in result.fetchall()
                ]

                if (
                    "keywords" not in conversation_columns
                    and "id" in conversation_columns
                ):
                    conn.exec_driver_sql(
                        "ALTER TABLE conversations "
                        "ADD COLUMN keywords TEXT"
                    )
                    conn.commit()


                # memories columns
                result = conn.exec_driver_sql(
                    "PRAGMA table_info(memories)"
                )

                memory_columns = [
                    row[1] for row in result.fetchall()
                ]

                if (
                    "conversation_id" not in memory_columns
                    and "id" in memory_columns
                ):
                    conn.exec_driver_sql(
                        "ALTER TABLE memories "
                        "ADD COLUMN conversation_id VARCHAR(36)"
                    )

                if (
                    "source_conversation_id" not in memory_columns
                    and "id" in memory_columns
                ):
                    conn.exec_driver_sql(
                        "ALTER TABLE memories "
                        "ADD COLUMN source_conversation_id VARCHAR(36)"
                    )

                if (
                    "memory_text" not in memory_columns
                    and "id" in memory_columns
                ):
                    conn.exec_driver_sql(
                        "ALTER TABLE memories "
                        "ADD COLUMN memory_text TEXT"
                    )

                if (
                    "memory_type" not in memory_columns
                    and "id" in memory_columns
                ):
                    conn.exec_driver_sql(
                        "ALTER TABLE memories "
                        "ADD COLUMN memory_type VARCHAR(50) "
                        "DEFAULT 'other'"
                    )

                if (
                    "importance" not in memory_columns
                    and "id" in memory_columns
                ):
                    conn.exec_driver_sql(
                        "ALTER TABLE memories "
                        "ADD COLUMN importance VARCHAR(20) "
                        "DEFAULT 'normal'"
                    )

                conn.commit()


                # messages columns
                result = conn.exec_driver_sql(
                    "PRAGMA table_info(messages)"
                )

                message_columns = [
                    row[1] for row in result.fetchall()
                ]

                if (
                    "user_id" not in message_columns
                    and "id" in message_columns
                ):
                    conn.exec_driver_sql(
                        "ALTER TABLE messages "
                        "ADD COLUMN user_id VARCHAR(36)"
                    )

                if (
                    "language" not in message_columns
                    and "id" in message_columns
                ):
                    conn.exec_driver_sql(
                        "ALTER TABLE messages "
                        "ADD COLUMN language VARCHAR(10) "
                        "DEFAULT 'en'"
                    )

                if (
                    "sources" not in message_columns
                    and "id" in message_columns
                ):
                    conn.exec_driver_sql(
                        "ALTER TABLE messages "
                        "ADD COLUMN sources TEXT"
                    )

                conn.commit()


                # Indexes
                conn.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS "
                    "ix_memories_conversation_id "
                    "ON memories (conversation_id)"
                )

                conn.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS "
                    "ix_memories_source_conversation_id "
                    "ON memories (source_conversation_id)"
                )

                conn.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS "
                    "ix_conversations_user_id "
                    "ON conversations (user_id)"
                )

                conn.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS "
                    "ix_messages_conversation_id "
                    "ON messages (conversation_id)"
                )

                conn.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS "
                    "ix_messages_user_id "
                    "ON messages (user_id)"
                )

                conn.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS "
                    "ix_message_attachments_message_id "
                    "ON message_attachments (message_id)"
                )

                conn.commit()

        except Exception as exc:
            print(
                f"SQLite migration warning: {exc}",
                flush=True
            )


    # ---------------------------------------------------------
    # Optional local demo user
    # ---------------------------------------------------------
    if settings.DEMO_USER_ENABLED:

        from app.models.user import User
        from app.models.user_settings import UserSettings
        from app.core.security import hash_password

        db = SessionLocal()

        try:
            demo_user = (
                db.query(User)
                .filter(
                    User.email == "sanju@example.com"
                )
                .first()
            )

            if not demo_user:

                demo_user = User(
                    name="Sanju",
                    email="sanju@example.com",
                    hashed_password=hash_password(
                        "Password123!"
                    )
                )

                db.add(demo_user)
                db.commit()
                db.refresh(demo_user)

                user_settings = UserSettings(
                    user_id=demo_user.id
                )

                db.add(user_settings)
                db.commit()

        finally:
            db.close()
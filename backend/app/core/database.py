from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import Generator

from app.core.config import settings


# SQLite needs this option for FastAPI's threaded request handling.
connect_args = (
    {"check_same_thread": False}
    if "sqlite" in settings.RESOLVED_DATABASE_URL
    else {}
)


engine = create_engine(
    settings.RESOLVED_DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _add_column_if_missing(
    conn,
    inspector,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    """
    Add a column only when it does not already exist.

    This is intentionally used for PostgreSQL production databases
    because SQLAlchemy create_all() does not alter existing tables.
    """
    columns = {
        column["name"]
        for column in inspector.get_columns(table_name)
    }

    if column_name not in columns:
        print(
            f"[DB MIGRATION] Adding {table_name}.{column_name}",
            flush=True,
        )

        conn.execute(
            text(
                f'ALTER TABLE "{table_name}" '
                f'ADD COLUMN "{column_name}" {column_definition}'
            )
        )


def _create_indexes(conn, inspector) -> None:
    """
    Create important indexes when they do not already exist.
    """

    existing_indexes = {}

    for table_name in inspector.get_table_names():
        try:
            existing_indexes[table_name] = {
                index["name"]
                for index in inspector.get_indexes(table_name)
            }
        except Exception:
            existing_indexes[table_name] = set()

    indexes = [
        (
            "users",
            "ix_users_email",
            'CREATE INDEX IF NOT EXISTS "ix_users_email" '
            'ON "users" ("email")',
        ),
        (
            "conversations",
            "ix_conversations_user_id",
            'CREATE INDEX IF NOT EXISTS "ix_conversations_user_id" '
            'ON "conversations" ("user_id")',
        ),
        (
            "messages",
            "ix_messages_conversation_id",
            'CREATE INDEX IF NOT EXISTS "ix_messages_conversation_id" '
            'ON "messages" ("conversation_id")',
        ),
        (
            "messages",
            "ix_messages_user_id",
            'CREATE INDEX IF NOT EXISTS "ix_messages_user_id" '
            'ON "messages" ("user_id")',
        ),
        (
            "memories",
            "ix_memories_user_id",
            'CREATE INDEX IF NOT EXISTS "ix_memories_user_id" '
            'ON "memories" ("user_id")',
        ),
        (
            "memories",
            "ix_memories_conversation_id",
            'CREATE INDEX IF NOT EXISTS "ix_memories_conversation_id" '
            'ON "memories" ("conversation_id")',
        ),
        (
            "memories",
            "ix_memories_source_conversation_id",
            'CREATE INDEX IF NOT EXISTS "ix_memories_source_conversation_id" '
            'ON "memories" ("source_conversation_id")',
        ),
        (
            "memories",
            "ix_memories_category",
            'CREATE INDEX IF NOT EXISTS "ix_memories_category" '
            'ON "memories" ("category")',
        ),
        (
            "message_attachments",
            "ix_message_attachments_message_id",
            'CREATE INDEX IF NOT EXISTS "ix_message_attachments_message_id" '
            'ON "message_attachments" ("message_id")',
        ),
        (
            "message_feedback",
            "ix_message_feedback_message_id",
            'CREATE INDEX IF NOT EXISTS "ix_message_feedback_message_id" '
            'ON "message_feedback" ("message_id")',
        ),
        (
            "message_feedback",
            "ix_message_feedback_user_id",
            'CREATE INDEX IF NOT EXISTS "ix_message_feedback_user_id" '
            'ON "message_feedback" ("user_id")',
        ),
        (
            "message_feedback",
            "ix_message_feedback_conversation_id",
            'CREATE INDEX IF NOT EXISTS "ix_message_feedback_conversation_id" '
            'ON "message_feedback" ("conversation_id")',
        ),
        (
            "web_search_logs",
            "ix_web_search_logs_user_id",
            'CREATE INDEX IF NOT EXISTS "ix_web_search_logs_user_id" '
            'ON "web_search_logs" ("user_id")',
        ),
        (
            "web_search_logs",
            "ix_web_search_logs_conversation_id",
            'CREATE INDEX IF NOT EXISTS "ix_web_search_logs_conversation_id" '
            'ON "web_search_logs" ("conversation_id")',
        ),
    ]

    tables = set(inspector.get_table_names())

    for table_name, index_name, sql in indexes:
        if table_name not in tables:
            continue

        if index_name not in existing_indexes.get(table_name, set()):
            try:
                conn.execute(text(sql))
            except Exception as exc:
                print(
                    f"[DB MIGRATION] Index warning "
                    f"{table_name}.{index_name}: {exc}",
                    flush=True,
                )


def _run_schema_migrations() -> None:
    """
    Bring an existing database schema up to date.

    Important:
    Base.metadata.create_all() only creates missing tables.
    It does NOT add columns to tables that already exist.

    This function handles the incremental columns introduced
    after the original MemoryBot database was created.
    """

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    print(
        f"[DB] Existing tables before migration: "
        f"{sorted(tables)}",
        flush=True,
    )

    # ---------------------------------------------------------
    # SQLite migrations
    # ---------------------------------------------------------
    if "sqlite" in settings.RESOLVED_DATABASE_URL:
        with engine.begin() as conn:
            inspector = inspect(conn)
            tables = set(inspector.get_table_names())

            if "conversations" in tables:
                _add_column_if_missing(
                    conn,
                    inspector,
                    "conversations",
                    "keywords",
                    "TEXT",
                )

            if "memories" in tables:
                for column_name, definition in [
                    ("conversation_id", "VARCHAR(36)"),
                    ("source_conversation_id", "VARCHAR(36)"),
                    ("memory_text", "TEXT"),
                    ("memory_type", "VARCHAR(50)"),
                    ("importance", "VARCHAR(20)"),
                ]:
                    inspector = inspect(conn)
                    _add_column_if_missing(
                        conn,
                        inspector,
                        "memories",
                        column_name,
                        definition,
                    )

            if "messages" in tables:
                for column_name, definition in [
                    ("user_id", "VARCHAR(36)"),
                    ("language", "VARCHAR(10)"),
                    ("sources", "TEXT"),
                ]:
                    inspector = inspect(conn)
                    _add_column_if_missing(
                        conn,
                        inspector,
                        "messages",
                        column_name,
                        definition,
                    )

        return

    # ---------------------------------------------------------
    # PostgreSQL / production migrations
    # ---------------------------------------------------------
    with engine.begin() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())

        # Existing conversations table
        if "conversations" in tables:
            inspector = inspect(conn)

            _add_column_if_missing(
                conn,
                inspector,
                "conversations",
                "keywords",
                "TEXT",
            )

        # Existing messages table
        if "messages" in tables:
            inspector = inspect(conn)

            _add_column_if_missing(
                conn,
                inspector,
                "messages",
                "user_id",
                "VARCHAR(36)",
            )

            inspector = inspect(conn)

            _add_column_if_missing(
                conn,
                inspector,
                "messages",
                "language",
                "VARCHAR(10)",
            )

            inspector = inspect(conn)

            _add_column_if_missing(
                conn,
                inspector,
                "messages",
                "sources",
                "TEXT",
            )

        # Existing memories table
        if "memories" in tables:
            for column_name, definition in [
                ("conversation_id", "VARCHAR(36)"),
                ("source_conversation_id", "VARCHAR(36)"),
                ("memory_text", "TEXT"),
                ("memory_type", "VARCHAR(50)"),
                ("importance", "VARCHAR(20)"),
            ]:
                inspector = inspect(conn)

                _add_column_if_missing(
                    conn,
                    inspector,
                    "memories",
                    column_name,
                    definition,
                )

        # Refresh table information after column migrations.
        inspector = inspect(conn)

        # Create indexes after columns exist.
        _create_indexes(conn, inspector)


def init_db() -> None:
    """
    Initialize all MemoryBot database models and run safe
    incremental migrations.
    """

    # Import every model before create_all().
    # This ensures SQLAlchemy knows about every table.
    import app.models.user
    import app.models.user_settings
    import app.models.conversation
    import app.models.message
    import app.models.memory
    import app.models.message_attachment
    import app.models.message_feedback
    import app.models.web_search_log

    print(
        "[DB] Creating missing tables...",
        flush=True,
    )

    Base.metadata.create_all(bind=engine)

    print(
        "[DB] Running schema migrations...",
        flush=True,
    )

    _run_schema_migrations()

    print(
        "[DB] Database initialization complete.",
        flush=True,
    )

    # ---------------------------------------------------------
    # Demo user for local development
    # ---------------------------------------------------------
    if settings.DEMO_USER_ENABLED:
        from app.models.user import User
        from app.models.user_settings import UserSettings
        from app.core.security import hash_password

        db = SessionLocal()

        try:
            demo_user = (
                db.query(User)
                .filter(User.email == "sanju@example.com")
                .first()
            )

            if not demo_user:
                demo_user = User(
                    name="Sanju",
                    email="sanju@example.com",
                    hashed_password=hash_password("Password123!"),
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
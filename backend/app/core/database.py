from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import Generator
from app.core.config import settings

# SQLite connection args for multi-threaded FastAPI access
connect_args = {"check_same_thread": False} if "sqlite" in settings.RESOLVED_DATABASE_URL else {}

engine = create_engine(
    settings.RESOLVED_DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db() -> Generator:
    """Dependency providing a transactional database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    """Initializes tables in the SQLite database, migrates schemas, and seeds default demo user."""
    import app.models.user
    import app.models.user_settings
    import app.models.conversation
    import app.models.message
    import app.models.memory
    import app.models.message_attachment
    import app.models.message_feedback
    Base.metadata.create_all(bind=engine)

    # Migrate columns and indexes if existing DB
    try:
        with engine.connect() as conn:
            # conversations.keywords
            res = conn.exec_driver_sql("PRAGMA table_info(conversations)")
            col_names = [row[1] for row in res.fetchall()]
            if "keywords" not in col_names and "id" in col_names:
                conn.exec_driver_sql("ALTER TABLE conversations ADD COLUMN keywords TEXT")
                conn.commit()

            # memories columns
            res2 = conn.exec_driver_sql("PRAGMA table_info(memories)")
            col_names2 = [row[1] for row in res2.fetchall()]
            if "conversation_id" not in col_names2 and "id" in col_names2:
                conn.exec_driver_sql("ALTER TABLE memories ADD COLUMN conversation_id VARCHAR(36)")
            if "source_conversation_id" not in col_names2 and "id" in col_names2:
                conn.exec_driver_sql("ALTER TABLE memories ADD COLUMN source_conversation_id VARCHAR(36)")
            if "memory_text" not in col_names2 and "id" in col_names2:
                conn.exec_driver_sql("ALTER TABLE memories ADD COLUMN memory_text TEXT")
            if "memory_type" not in col_names2 and "id" in col_names2:
                conn.exec_driver_sql("ALTER TABLE memories ADD COLUMN memory_type VARCHAR(50) DEFAULT 'other'")
            if "importance" not in col_names2 and "id" in col_names2:
                conn.exec_driver_sql("ALTER TABLE memories ADD COLUMN importance VARCHAR(20) DEFAULT 'normal'")
            conn.commit()

            # messages columns
            res3 = conn.exec_driver_sql("PRAGMA table_info(messages)")
            col_names3 = [row[1] for row in res3.fetchall()]
            if "user_id" not in col_names3 and "id" in col_names3:
                conn.exec_driver_sql("ALTER TABLE messages ADD COLUMN user_id VARCHAR(36)")
            if "language" not in col_names3 and "id" in col_names3:
                conn.exec_driver_sql("ALTER TABLE messages ADD COLUMN language VARCHAR(10) DEFAULT 'en'")
            conn.commit()

            # Ensure indexes exist
            conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_memories_conversation_id ON memories (conversation_id)")
            conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_memories_source_conversation_id ON memories (source_conversation_id)")
            conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_conversations_user_id ON conversations (user_id)")
            conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_messages_conversation_id ON messages (conversation_id)")
            conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_messages_user_id ON messages (user_id)")
            conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_message_attachments_message_id ON message_attachments (message_id)")
            conn.commit()
    except Exception:
        pass

    # Seed default demo student account if not present
    from app.models.user import User
    from app.models.user_settings import UserSettings
    from app.core.security import hash_password

    db = SessionLocal()
    try:
        demo_user = db.query(User).filter(User.email == "sanju@example.com").first()
        if not demo_user:
            demo_user = User(
                name="Sanju",
                email="sanju@example.com",
                hashed_password=hash_password("Password123!")
            )
            db.add(demo_user)
            db.commit()
            db.refresh(demo_user)

            settings = UserSettings(user_id=demo_user.id)
            db.add(settings)
            db.commit()
    finally:
        db.close()

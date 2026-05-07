from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Using 'postgres' service name for Docker, fallback to localhost for local dev
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/docusync")

# We add pool_pre_ping to handle the database being "ready" but not yet accepting queries
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
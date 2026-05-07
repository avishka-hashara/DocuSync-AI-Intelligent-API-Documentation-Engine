from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# This URL matches the exact credentials we set in docker-compose.yml
DATABASE_URL = "postgresql://user:password@127.0.0.1:5433/docusync"
# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# This is the base class all our models will inherit from
Base = declarative_base()

# Dependency to get the DB session in our FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
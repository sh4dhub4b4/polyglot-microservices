from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# We will use SQLite for local rapid dev, easily swapped to PostgreSQL via env vars
DATABASE_URL = "sqlite:///./platform_dev.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
import logging

# Heroku DATABASE_URL workaround: SQLAlchemy requires 'postgresql://' instead of 'postgres://'
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not SQLALCHEMY_DATABASE_URL:
    # Fallback to local SQLite for development
    from pathlib import Path
    BASE_DIR = Path(__file__).resolve().parents[1]
    DB_PATH = BASE_DIR / "emergency_hub.db"
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    # Postgres engine
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    # Import models here to ensure they are registered with Base
    from app.models.schema import Hotline, EmergencyReport, User
    Base.metadata.create_all(bind=engine)
    seed_db()

def seed_db():
    from app.models.schema import Hotline, User
    from app.data.hotlines import HOTLINES
    db = SessionLocal()
    try:
        if db.query(Hotline).count() == 0:
            logging.info("Seeding database with initial hotlines...")
            for h_data in HOTLINES:
                hotline = Hotline(
                    name=h_data["name"],
                    type=h_data["type"],
                    lat=h_data["lat"],
                    lon=h_data["lon"],
                    contact=h_data["contact"]
                )
                db.add(hotline)
            db.commit()

        if db.query(User).count() == 0:
            logging.info("Seeding database with demo users...")
            demo_users = [
                User(
                    email="caller@demo.local",
                    password_hash="demo-caller",
                    role="caller"
                ),
                User(
                    email="admin@demo.local",
                    password_hash="demo-admin",
                    role="admin"
                )
            ]
            db.add_all(demo_users)
            db.commit()
    except Exception as e:
        logging.error(f"Error seeding database: {e}")
    finally:
        db.close()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import logging

SQLALCHEMY_DATABASE_URL = "sqlite:///./emergency_hub.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
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

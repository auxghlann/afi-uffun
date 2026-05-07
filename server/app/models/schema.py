from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
import datetime
from app.database import Base

class Hotline(Base):
    __tablename__ = "hotlines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    type = Column(String, index=True) # e.g. Police, Fire, Medical, Rescue
    lat = Column(Float)
    lon = Column(Float)
    contact = Column(String)

class EmergencyReport(Base):
    __tablename__ = "emergency_reports"

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(String, unique=True, index=True)
    status = Column(String, index=True)
    emergency_types = Column(String) # Comma-separated string
    severity = Column(String)
    people_affected = Column(String)
    summary = Column(String)
    caller_lat = Column(Float)
    caller_lon = Column(Float)
    routed_hotlines = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="caller")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

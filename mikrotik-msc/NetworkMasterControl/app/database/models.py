from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, ForeignKey, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import os
from datetime import datetime
from dotenv import load_dotenv

# Load biến môi trường
load_dotenv()

Base = declarative_base()
engine = create_engine(os.getenv('DATABASE_URL'))

class Device(Base):
    __tablename__ = 'devices'

    id = Column(Integer, primary_key=True)
    hostname = Column(String(100))
    ip_address = Column(String(15), unique=True)
    model = Column(String(50))
    ros_version = Column(String(20))
    last_seen = Column(DateTime, default=datetime.utcnow)
    config_backup = Column(String(1000))
    config_version = Column(String(20))
    status = Column(String(20))

    # Relationships
    interfaces = relationship("Interface", back_populates="device")
    traffic_logs = relationship("TrafficLog", back_populates="device")

class Interface(Base):
    __tablename__ = 'interfaces'

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id'))
    name = Column(String(50))
    type = Column(String(20))
    mac_address = Column(String(17))
    enabled = Column(Boolean, default=True)

    # Relationships
    device = relationship("Device", back_populates="interfaces")
    traffic_logs = relationship("TrafficLog", back_populates="interface")

class TrafficLog(Base):
    __tablename__ = 'traffic_logs'

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id'))
    interface_id = Column(Integer, ForeignKey('interfaces.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    tx_bytes = Column(Float)
    rx_bytes = Column(Float)
    tx_packets = Column(Integer)
    rx_packets = Column(Integer)
    tx_rate = Column(Float)  # KB/s
    rx_rate = Column(Float)  # KB/s

    # Relationships
    device = relationship("Device", back_populates="traffic_logs")
    interface = relationship("Interface", back_populates="traffic_logs")

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
    email = Column(String(100), unique=True)
    hashed_password = Column(String(100))
    role = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

    # Relationships
    tenant_id = Column(Integer, ForeignKey('tenants.id'))
    tenant = relationship("Tenant", back_populates="users")

class Tenant(Base):
    __tablename__ = 'tenants'

    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    subdomain = Column(String(50), unique=True)
    settings = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="tenant")

class Alert(Base):
    __tablename__ = 'alerts'

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id'))
    type = Column(String(50))  # traffic, security, system
    severity = Column(String(20))  # info, warning, critical
    message = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(Integer, ForeignKey('users.id'))
    acknowledged_at = Column(DateTime)
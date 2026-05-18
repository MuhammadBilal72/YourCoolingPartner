from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./yourcoolingpartner.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# ==========================================
# Table: users
# ==========================================
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    mobile_number = Column(String, unique=True, index=True)
    role = Column(String)  # 'user' or 'technician'
    hashed_password = Column(String)

    jobs = relationship("Job", back_populates="user")
    bookings_as_user = relationship("Booking", back_populates="user", foreign_keys="Booking.user_id")
    bookings_as_tech = relationship("Booking", back_populates="technician", foreign_keys="Booking.technician_id")
    bids = relationship("Bid", back_populates="technician")

# ==========================================
# Table: jobs
# ==========================================
class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    city = Column(String)
    town = Column(String)
    status = Column(String, default="pending")  # 'pending', 'active', 'completed'
    date = Column(String)
    time = Column(String)

    user = relationship("User", back_populates="jobs")
    bids = relationship("Bid", back_populates="job")

# ==========================================
# Table: bids
# ==========================================
class Bid(Base):
    __tablename__ = "bids"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    technician_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)

    job = relationship("Job", back_populates="bids")
    technician = relationship("User", back_populates="bids")

# ==========================================
# Table: bookings
# ==========================================
class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    technician_id = Column(Integer, ForeignKey("users.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(String)
    time = Column(String)
    amount = Column(Float)

    user = relationship("User", back_populates="bookings_as_user", foreign_keys=[user_id])
    technician = relationship("User", back_populates="bookings_as_tech", foreign_keys=[technician_id])

# Create all tables
Base.metadata.create_all(bind=engine)

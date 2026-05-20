from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Boolean
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
    location = Column(String, nullable=True)
    address = Column(String, nullable=True)

    def __repr__(self):
        return (
            f"User(id={self.id}, name='{self.name}', "
            f"mobile='{self.mobile_number}', role='{self.role}', "
            f"location='{self.location}', address='{self.address}')"
        )

    jobs = relationship("Job", back_populates="user")
    bookings_as_user = relationship("Booking", back_populates="user", foreign_keys="Booking.user_id")
    bookings_as_tech = relationship("Booking", back_populates="technician", foreign_keys="Booking.technician_id")
    bids = relationship("Bid", back_populates="technician")
    notifications = relationship("Notification", back_populates="receiver")

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
    job_id = Column(Integer, ForeignKey("jobs.id"))
    technician_id = Column(Integer, ForeignKey("users.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(String)
    time = Column(String)
    amount = Column(Float)

    user = relationship("User", back_populates="bookings_as_user", foreign_keys=[user_id])
    technician = relationship("User", back_populates="bookings_as_tech", foreign_keys=[technician_id])

# ==========================================
# Table: conversations
# ==========================================
class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(String)

    messages = relationship("Message", back_populates="conversation")

# ==========================================
# Table: messages
# ==========================================
class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    sender = Column(String)  # 'user' or 'agent'
    content = Column(String)
    timestamp = Column(String)

    conversation = relationship("Conversation", back_populates="messages")

# ==========================================
# Table: notifications
# ==========================================
class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    receiver_id = Column(Integer, ForeignKey("users.id"))
    content = Column(String)
    is_read = Column(Boolean, default=False)
    created_at = Column(String)

    receiver = relationship("User", back_populates="notifications")

# Create all tables
Base.metadata.create_all(bind=engine)

from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from typing import Optional
from jose import JWTError, jwt
from datetime import datetime, timedelta
import re
import uvicorn

from db import SessionLocal, User, Job, Bid, Booking, Conversation, Message
from auth import (
    verify_password, get_password_hash, create_access_token,
    SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
)
from agent import graph

app = FastAPI(title="YourCoolingPartner API", version="2.0.0")

# ==========================================
# Database Dependency
# ==========================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# Pydantic Schemas
# ==========================================
class LoginRequest(BaseModel):
    mobile_number: str
    password: str

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile(cls, v):
        if not re.match(r"^03\d{9}$", v):
            raise ValueError("Invalid mobile number. Must be 11 digits starting with 03 (e.g., 03001234567)")
        return v

class ChatRequest(BaseModel):
    message: str

class JobCreate(BaseModel):
    city: str
    town: str
    date: str
    time: str

class BidSubmit(BaseModel):
    job_id: int
    amount: float

# ==========================================
# Auth Dependency
# ==========================================
def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token. Send 'Authorization: Bearer <token>'")
    token = authorization.split(" ")[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        mobile_number: str = payload.get("sub")
        if mobile_number is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token verification failed")

    user = db.query(User).filter(User.mobile_number == mobile_number).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ==========================================
# POST /auth/login
# ==========================================
@app.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.mobile_number == req.mobile_number).first()

    if not db_user:
        raise HTTPException(status_code=401, detail="Mobile number not registered")

    if not verify_password(req.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect password")

    access_token = create_access_token(
        data={"sub": db_user.mobile_number, "role": db_user.role, "id": db_user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": db_user.id,
            "name": db_user.name,
            "mobile_number": db_user.mobile_number,
            "role": db_user.role,
            "location": getattr(db_user, "location", None),
            "address": getattr(db_user, "address", None)
        }
    }

# ==========================================
# POST /api/chat — AI Agent (Persistent Chat)
# ==========================================
@app.post("/api/chat")
def chat_with_agent(chat: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.id

    # Find or create conversation
    conversation = db.query(Conversation).filter(Conversation.user_id == user_id).first()
    if not conversation:
        conversation = Conversation(user_id=user_id, created_at=datetime.now().isoformat())
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # Save user message
    user_msg = Message(
        conversation_id=conversation.id,
        sender="user",
        content=chat.message,
        timestamp=datetime.now().isoformat()
    )
    db.add(user_msg)
    db.commit()

    # Load full conversation history from DB
    messages = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(Message.timestamp).all()

    history = [{"role": m.sender, "content": m.content} for m in messages]

    # Build agent state
    current_state = {
        "user_id": user_id,
        "conversation_id": conversation.id,
        "user_input": chat.message,
        "conversation_history": history,
        "action": None,
        "extracted_intent": None,
        "extracted_city": None,
        "extracted_town": None,
        "schedule_date": None,
        "schedule_time": None,
        "technician_name": None,
        "raw_businesses": [],
        "bot_response": None
    }

    # Run the agent
    result = graph.invoke(current_state)

    # Save bot response to DB
    bot_response = result.get("bot_response", "Kuch samajh nahi aaya.")
    bot_msg = Message(
        conversation_id=conversation.id,
        sender="agent",
        content=bot_response,
        timestamp=datetime.now().isoformat()
    )
    db.add(bot_msg)
    db.commit()

    raw_businesses = result.get("raw_businesses") or []
    found_technicians = []
    
    if raw_businesses:
        phones = []
        for b in raw_businesses:
            phone = str(b.get("nationalPhoneNumber", "")).strip()
            if phone:
                phones.append(phone)
                
        if phones:
            techs = db.query(User).filter(User.role == "technician", User.mobile_number.in_(phones)).all()
            found_technicians = [
                {
                    "id": t.id, 
                    "name": t.name, 
                    "mobile_number": t.mobile_number, 
                    "location": getattr(t, "location", None), 
                    "address": getattr(t, "address", None)
                }
                for t in techs
            ]

    return {
        "response": bot_response,
        "action": result.get("action", "clarify"),
        "found_technicians": found_technicians,
        "bookings": result.get("my_bookings", [])
    }

# ==========================================
# GET /api/chat/history — Load chat on app open
# ==========================================
@app.get("/api/chat/history")
def get_chat_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter(Conversation.user_id == current_user.id).first()
    if not conversation:
        return {"conversation_id": None, "messages": []}

    messages = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(Message.timestamp).all()

    return {
        "conversation_id": conversation.id,
        "messages": [
            {
                "id": m.id,
                "sender": m.sender,
                "content": m.content,
                "timestamp": m.timestamp
            }
            for m in messages
        ]
    }

# ==========================================
# POST /api/jobs — Create a job manually
# ==========================================
@app.post("/api/jobs")
def create_job(job: JobCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_job = Job(
        user_id=current_user.id,
        city=job.city,
        town=job.town,
        status="pending",
        date=job.date,
        time=job.time
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return {"message": "Job created", "job_id": new_job.id}

# ==========================================
# GET /api/jobs — Fetch jobs
# ==========================================
@app.get("/api/jobs")
def get_jobs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == "technician":
        pending_jobs = db.query(Job).filter(Job.status == "pending").all()
        my_bookings = db.query(Booking).filter(Booking.technician_id == current_user.id).all()
        booked_job_ids = [b.job_id for b in my_bookings if b.job_id]
        booked_jobs = db.query(Job).filter(Job.id.in_(booked_job_ids)).all()
        jobs = pending_jobs + booked_jobs
    else:
        jobs = db.query(Job).filter(Job.user_id == current_user.id).all()

    result = []
    for j in jobs:
        my_bid = None
        if current_user.role == "technician":
            bid = db.query(Bid).filter(Bid.job_id == j.id, Bid.technician_id == current_user.id).first()
            if bid:
                my_bid = bid.amount

        result.append({
            "id": j.id,
            "user_id": j.user_id,
            "city": j.city,
            "town": j.town,
            "status": j.status,
            "date": j.date,
            "time": j.time,
            "my_bid": my_bid
        })

    return result

# ==========================================
# POST /api/bids — Technician submits a bid
# ==========================================
@app.post("/api/bids")
def submit_bid(bid: BidSubmit, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "technician":
        raise HTTPException(status_code=403, detail="Only technicians can submit bids")

    job = db.query(Job).filter(Job.id == bid.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing_bid = db.query(Bid).filter(Bid.job_id == bid.job_id, Bid.technician_id == current_user.id).first()
    if existing_bid:
        raise HTTPException(status_code=400, detail="You have already submitted a bid for this job")

    new_bid = Bid(job_id=bid.job_id, technician_id=current_user.id, amount=bid.amount)
    db.add(new_bid)
    db.commit()
    db.refresh(new_bid)
    return {"message": "Bid submitted", "bid_id": new_bid.id}

# ==========================================
# GET /api/jobs/{id}/bids — View bids on a job
# ==========================================
@app.get("/api/jobs/{job_id}/bids")
def get_bids_for_job(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    bids = db.query(Bid).filter(Bid.job_id == job_id).all()
    return [
        {
            "id": b.id,
            "technician_id": b.technician_id,
            "technician_name": b.technician.name if b.technician else f"Technician #{b.technician_id}",
            "amount": b.amount
        }
        for b in bids
    ]

# ==========================================
# Run the server
# ==========================================
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from typing import Optional
from jose import JWTError, jwt
from datetime import timedelta
import re
import uvicorn

from db import SessionLocal, User, Job, Bid, Booking
from auth import (
    verify_password, get_password_hash, create_access_token,
    SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
)
from agent import graph

app = FastAPI(title="YourCoolingPartner API", version="1.0.0")

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
# In-Memory Chat Sessions (Multi-Turn)
# ==========================================
# Maps user_id -> { conversation_history, extracted_intent, extracted_city, extracted_town }
chat_sessions = {}

# ==========================================
# Pydantic Request/Response Schemas
# ==========================================
class LoginRequest(BaseModel):
    mobile_number: str
    password: str

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile(cls, v):
        # Pakistani mobile format: 03XXXXXXXXX (11 digits)
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
# Auth Dependency: Extract user from JWT
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
# Auto-creates account if mobile number doesn't exist
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
            "role": db_user.role
        }
    }

# ==========================================
# POST /api/chat — AI Agent Interaction
# ==========================================
@app.post("/api/chat")
def chat_with_agent(chat: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.id
    user_text = chat.message

    # Initialize session if first message
    if user_id not in chat_sessions:
        chat_sessions[user_id] = {
            "conversation_history": [],
            "extracted_intent": None,
            "extracted_city": None,
            "extracted_town": None
        }

    session = chat_sessions[user_id]
    session["conversation_history"].append({"role": "user", "content": user_text})

    # Build LangGraph state from session
    current_state = {
        "user_input": user_text,
        "conversation_history": session["conversation_history"].copy(),
        "extracted_intent": session["extracted_intent"],
        "extracted_city": session["extracted_city"],
        "extracted_town": session["extracted_town"],
        "is_clarification_needed": False,
        "bot_response": None,
        "raw_businesses": [],
        "final_ranked_response": None
    }

    # Run the LangGraph agent
    result = graph.invoke(current_state)

    if result.get("is_clarification_needed"):
        bot_msg = result.get("bot_response", "")
        session["conversation_history"].append({"role": "bot", "content": bot_msg})
        session["extracted_intent"] = result.get("extracted_intent") or session["extracted_intent"]
        session["extracted_city"] = result.get("extracted_city") or session["extracted_city"]
        session["extracted_town"] = result.get("extracted_town") or session["extracted_town"]
        return {"response": bot_msg, "status": "clarifying"}
    else:
        final_output = result.get("final_ranked_response", "No results found.")

        # Auto-create a Job entry in the database
        new_job = Job(
            user_id=user_id,
            city=result.get("extracted_city"),
            town=result.get("extracted_town"),
            status="pending",
            date="Pending",
            time="ASAP"
        )
        db.add(new_job)
        db.commit()
        db.refresh(new_job)

        # Reset chat session for fresh conversation
        chat_sessions[user_id] = {
            "conversation_history": [],
            "extracted_intent": None,
            "extracted_city": None,
            "extracted_town": None
        }

        return {
            "response": final_output,
            "status": "completed",
            "job_id": new_job.id
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
# GET /api/jobs — Fetch jobs (Technicians see pending jobs)
# ==========================================
@app.get("/api/jobs")
def get_jobs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == "technician":
        jobs = db.query(Job).filter(Job.status == "pending").all()
    else:
        jobs = db.query(Job).filter(Job.user_id == current_user.id).all()

    return [
        {
            "id": j.id,
            "user_id": j.user_id,
            "city": j.city,
            "town": j.town,
            "status": j.status,
            "date": j.date,
            "time": j.time
        }
        for j in jobs
    ]

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
            "amount": b.amount
        }
        for b in bids
    ]

# ==========================================
# Run the server
# ==========================================
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

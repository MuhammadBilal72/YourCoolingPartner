from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from typing import Optional
from jose import JWTError, jwt
from datetime import datetime, timedelta
import re
import uvicorn

from db import SessionLocal, User, Job, Bid, Booking, Conversation, Message, Notification
from auth import (
    verify_password, get_password_hash, create_access_token,
    SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
)
from agent import graph
from agent.log_viewer import get_recent_traces, is_configured as langsmith_configured

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
# LangSmith Agent Logs — JSON API
# ==========================================
@app.get("/api/agent/logs")
def get_agent_logs(limit: int = 20):
    """Return recent agent execution traces from LangSmith."""
    traces = get_recent_traces(limit=min(limit, 100))
    return {
        "configured": langsmith_configured(),
        "project": "YourCoolingPartner",
        "count": len(traces),
        "traces": traces,
    }


# ==========================================
# LangSmith Agent Logs — HTML Dashboard
# ==========================================
AGENT_LOGS_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agent Logs — YourCoolingPartner</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0f172a; color: #e2e8f0; padding: 24px;
  }
  .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
  .header h1 { font-size: 24px; font-weight: 700; }
  .header h1 span { color: #38bdf8; }
  .badge {
    padding: 4px 12px; border-radius: 999px; font-size: 12px; font-weight: 600;
  }
  .badge.on { background: #166534; color: #86efac; }
  .badge.off { background: #7f1d1d; color: #fca5a5; }
  .stats { display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }
  .stat-card {
    background: #1e293b; border-radius: 12px; padding: 16px 20px; flex: 1; min-width: 140px;
  }
  .stat-card .label { font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }
  .stat-card .value { font-size: 28px; font-weight: 700; margin-top: 4px; }
  .trace {
    background: #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 16px;
    border-left: 4px solid #334155;
  }
  .trace.success { border-left-color: #22c55e; }
  .trace.error { border-left-color: #ef4444; }
  .trace-header { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px; }
  .trace-title { font-size: 16px; font-weight: 600; }
  .trace-meta { font-size: 12px; color: #94a3b8; margin-top: 4px; }
  .trace-status {
    padding: 2px 10px; border-radius: 999px; font-size: 11px; font-weight: 600;
  }
  .trace-status.ok { background: #166534; color: #86efac; }
  .trace-status.err { background: #7f1d1d; color: #fca5a5; }
  .children { margin-top: 12px; margin-left: 16px; border-left: 2px solid #334155; padding-left: 16px; }
  .child-node {
    background: #0f172a; border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;
    display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;
  }
  .child-node .name { font-weight: 500; font-size: 14px; }
  .child-node .type {
    font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 600;
  }
  .type-llm { background: #1e3a5f; color: #93c5fd; }
  .type-chain { background: #3b1f5e; color: #d8b4fe; }
  .type-tool { background: #1e3a2f; color: #86efac; }
  .loading { text-align: center; padding: 48px; color: #64748b; }
  .empty { text-align: center; padding: 48px; color: #64748b; }
  .empty h3 { font-size: 18px; margin-bottom: 8px; }
  .empty p { font-size: 14px; }
  .empty code { background: #1e293b; padding: 2px 6px; border-radius: 4px; font-size: 13px; }
  .error-text { color: #fca5a5; font-size: 13px; margin-top: 4px; }
  .msg-toggle {
    background: none; border: 1px solid #334155; color: #94a3b8; cursor: pointer;
    font-size: 12px; padding: 2px 8px; border-radius: 4px; margin-left: 8px;
  }
  .msg-toggle:hover { background: #334155; }
  .msg-content {
    display: none; margin-top: 8px; padding: 12px; background: #0f172a;
    border-radius: 8px; font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 12px; white-space: pre-wrap; overflow-x: auto; max-height: 300px; overflow-y: auto;
  }
  .msg-content.open { display: block; }
  .refresh-btn {
    background: #38bdf8; color: #0f172a; border: none; padding: 8px 16px;
    border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 14px;
  }
  .refresh-btn:hover { background: #7dd3fc; }
  .config-notice {
    background: #1e293b; border-radius: 12px; padding: 32px; text-align: center; margin-top: 16px;
  }
  .config-notice h3 { font-size: 18px; margin-bottom: 8px; color: #fbbf24; }
  .config-notice p { font-size: 14px; color: #94a3b8; margin-bottom: 12px; }
  .config-notice code { background: #0f172a; padding: 2px 6px; border-radius: 4px; }
</style>
</head>
<body>
  <div class="header">
    <h1>❄️ Agent <span>Logs</span></h1>
    <button class="refresh-btn" onclick="fetchTraces()">⟳ Refresh</button>
  </div>
  <div id="stats" class="stats"></div>
  <div id="traces"></div>

<script>
async function fetchTraces() {
  document.getElementById('traces').innerHTML = '<div class="loading">⏳ Loading traces...</div>';
  try {
    const res = await fetch('/api/agent/logs?limit=20');
    const data = await res.json();
    renderDashboard(data);
  } catch (e) {
    document.getElementById('traces').innerHTML =
      '<div class="empty"><h3>❌ Failed to fetch logs</h3><p>' + e.message + '</p></div>';
  }
}

function renderDashboard(data) {
  renderStats(data);
  const container = document.getElementById('traces');

  if (!data.configured) {
    container.innerHTML = `
      <div class="config-notice">
        <h3>⚠️ LangSmith Not Configured</h3>
        <p>Add your LangSmith API key to <code>.env</code> to enable agent tracing.</p>
        <p><code>LANGCHAIN_API_KEY="lsv2_pt_..."</code></p>
      </div>`;
    return;
  }

  if (data.count === 0) {
    container.innerHTML = `
      <div class="empty">
        <h3>📭 No traces yet</h3>
        <p>Send a message to <code>POST /api/chat</code> to generate agent traces.</p>
      </div>`;
    return;
  }

  let html = '';
  for (const trace of data.traces) {
    html += renderTrace(trace);
  }
  container.innerHTML = html;
}

function renderStats(data) {
  document.getElementById('stats').innerHTML = `
    <div class="stat-card">
      <div class="label">Status</div>
      <div class="value"><span class="badge ${data.configured ? 'on' : 'off'}">${data.configured ? 'Connected' : 'Off'}</span></div>
    </div>
    <div class="stat-card">
      <div class="label">Traces</div>
      <div class="value">${data.count}</div>
    </div>
    <div class="stat-card">
      <div class="label">Project</div>
      <div class="value" style="font-size:16px;margin-top:8px;">${data.project}</div>
    </div>`;
}

function renderTrace(trace) {
  const hasError = !!trace.error;
  const cls = hasError ? 'error' : 'success';
  const statusCls = hasError ? 'err' : 'ok';
  const statusText = hasError ? 'Error' : (trace.status || 'Success');
  const dur = trace.duration_ms != null ? (trace.duration_ms / 1000).toFixed(2) + 's' : '—';
  const time = trace.start_time ? new Date(trace.start_time).toLocaleString() : '—';
  const tokens = trace.total_tokens != null ? trace.total_tokens + ' tokens' : '';

  let html = `
    <div class="trace ${cls}">
      <div class="trace-header">
        <div>
          <div class="trace-title">🧠 ${escapeHtml(trace.name)}</div>
          <div class="trace-meta">${time} · ${dur} ${tokens ? '· ' + tokens : ''}</div>
        </div>
        <div>
          <span class="trace-status ${statusCls}">${statusText}</span>
          <button class="msg-toggle" onclick="toggleMsg('inputs-${trace.id}')">📥 Input</button>
          <button class="msg-toggle" onclick="toggleMsg('outputs-${trace.id}')">📤 Output</button>
        </div>
      </div>
      <div id="inputs-${trace.id}" class="msg-content">${escapeHtml(JSON.stringify(trace.inputs, null, 2))}</div>
      <div id="outputs-${trace.id}" class="msg-content">${escapeHtml(JSON.stringify(trace.outputs, null, 2))}</div>`;

  if (hasError) {
    html += `<div class="error-text">❌ ${escapeHtml(trace.error)}</div>`;
  }

  if (trace.children && trace.children.length > 0) {
    html += '<div class="children">';
    for (const child of trace.children) {
      html += renderChild(child);
    }
    html += '</div>';
  }

  html += '</div>';
  return html;
}

function renderChild(child) {
  const typeCls = 'type-' + (child.run_type || 'chain');
  const dur = child.duration_ms != null ? (child.duration_ms / 1000).toFixed(2) + 's' : '';
  const tokens = child.total_tokens != null ? child.total_tokens + ' tok' : '';

  let html = `
    <div class="child-node">
      <div>
        <span class="name">${escapeHtml(child.name)}</span>
        <span class="type ${typeCls}">${child.run_type || '?'}</span>
        <button class="msg-toggle" onclick="toggleMsg('ci-${child.id}')">📥</button>
        <button class="msg-toggle" onclick="toggleMsg('co-${child.id}')">📤</button>
      </div>
      <div style="font-size:12px;color:#94a3b8;">${dur} ${tokens ? '· ' + tokens : ''}</div>
    </div>
    <div id="ci-${child.id}" class="msg-content">${escapeHtml(JSON.stringify(child.inputs, null, 2))}</div>
    <div id="co-${child.id}" class="msg-content">${escapeHtml(JSON.stringify(child.outputs, null, 2))}</div>`;

  if (child.error) {
    html += `<div class="error-text">❌ ${escapeHtml(child.error)}</div>`;
  }

  if (child.children && child.children.length > 0) {
    for (const gc of child.children) {
      html += '<div style="margin-left:16px;">' + renderChild(gc) + '</div>';
    }
  }

  return html;
}

function toggleMsg(id) {
  const el = document.getElementById(id);
  if (el) el.classList.toggle('open');
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, function(m) {
    if (m === '&') return '&amp;'; if (m === '<') return '&lt;';
    if (m === '>') return '&gt;'; if (m === '"') return '&quot;';
    return '&#39;';
  });
}

fetchTraces();
</script>
</body>
</html>
"""


@app.get("/agent/logs/ui", response_class=HTMLResponse)
def agent_logs_ui():
    """Render the LangSmith agent traces dashboard."""
    return AGENT_LOGS_HTML


# ==========================================
# Run the server
# ==========================================
# ==========================================
# GET /api/notifications
# ==========================================
@app.get("/api/notifications")
def get_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notifs = db.query(Notification).filter(Notification.receiver_id == current_user.id).order_by(Notification.id.desc()).all()
    return [
        {
            "id": n.id,
            "content": n.content,
            "is_read": n.is_read,
            "created_at": n.created_at
        }
        for n in notifs
    ]

# ==========================================
# POST /api/notifications/{id}/read
# ==========================================
@app.post("/api/notifications/{notif_id}/read")
def read_notification(notif_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notif = db.query(Notification).filter(Notification.id == notif_id, Notification.receiver_id == current_user.id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notif.is_read = True
    db.commit()
    return {"message": "Notification marked as read"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

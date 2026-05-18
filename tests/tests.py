"""
Local API Tests for YourCoolingPartner
======================================
Tests all endpoints without needing external APIs.
The AI agent (/api/chat) is mocked to avoid burning Groq/Google credits.

Usage:
    python tests.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from db.database import Base, engine, SessionLocal

# ==========================================
# Setup: Use a fresh test database
# ==========================================
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

from main import app

client = TestClient(app)

PASSED = 0
FAILED = 0

def log_result(test_name, passed, detail=""):
    global PASSED, FAILED
    if passed:
        PASSED += 1
        print(f"   ✅ PASS: {test_name}")
    else:
        FAILED += 1
        print(f"   ❌ FAIL: {test_name} — {detail}")

# ==========================================
# 1. AUTH TESTS
# ==========================================
print("\n" + "=" * 55)
print("  🔐 Testing Authentication (/auth/login)")
print("=" * 55)

# Test 1.1: First login auto-registers user
resp = client.post("/auth/login", json={
    "mobile_number": "03001111111",
    "password": "test123",
    "name": "Test User",
    "role": "user"
})
log_result(
    "Auto-register new user on first login",
    resp.status_code == 200 and "access_token" in resp.json(),
    f"Status: {resp.status_code}, Body: {resp.json()}"
)
user_token = resp.json().get("access_token", "")

# Test 1.2: Login again with correct password
resp = client.post("/auth/login", json={
    "mobile_number": "03001111111",
    "password": "test123"
})
log_result(
    "Login with correct password",
    resp.status_code == 200 and "access_token" in resp.json(),
    f"Status: {resp.status_code}"
)

# Test 1.3: Login with wrong password
resp = client.post("/auth/login", json={
    "mobile_number": "03001111111",
    "password": "wrongpassword"
})
log_result(
    "Reject wrong password (401)",
    resp.status_code == 401,
    f"Status: {resp.status_code}"
)

# Test 1.4: Register a technician
resp = client.post("/auth/login", json={
    "mobile_number": "03002222222",
    "password": "tech123",
    "name": "Test Technician",
    "role": "technician"
})
log_result(
    "Auto-register technician",
    resp.status_code == 200 and resp.json()["user"]["role"] == "technician",
    f"Status: {resp.status_code}"
)
tech_token = resp.json().get("access_token", "")

# Test 1.5: Access without token
resp = client.get("/api/jobs")
log_result(
    "Reject request without token (401)",
    resp.status_code == 401,
    f"Status: {resp.status_code}"
)

# Test 1.6: Access with invalid token
resp = client.get("/api/jobs", headers={"Authorization": "Bearer invalidtoken123"})
log_result(
    "Reject request with invalid token (401)",
    resp.status_code == 401,
    f"Status: {resp.status_code}"
)

# ==========================================
# 2. JOBS TESTS
# ==========================================
print("\n" + "=" * 55)
print("  📋 Testing Jobs (/api/jobs)")
print("=" * 55)

# Test 2.1: Create a job as a user
resp = client.post("/api/jobs",
    json={"city": "Lahore", "town": "Johar Town", "date": "2026-05-20", "time": "10:00 AM"},
    headers={"Authorization": f"Bearer {user_token}"}
)
log_result(
    "Create a job (POST /api/jobs)",
    resp.status_code == 200 and "job_id" in resp.json(),
    f"Status: {resp.status_code}, Body: {resp.json()}"
)
job_id = resp.json().get("job_id")

# Test 2.2: Create another job
resp = client.post("/api/jobs",
    json={"city": "Karachi", "town": "DHA Phase 6", "date": "2026-05-21", "time": "02:00 PM"},
    headers={"Authorization": f"Bearer {user_token}"}
)
log_result(
    "Create a second job",
    resp.status_code == 200,
    f"Status: {resp.status_code}"
)

# Test 2.3: User sees only their own jobs
resp = client.get("/api/jobs", headers={"Authorization": f"Bearer {user_token}"})
log_result(
    "User sees their own jobs (GET /api/jobs)",
    resp.status_code == 200 and len(resp.json()) == 2,
    f"Status: {resp.status_code}, Count: {len(resp.json())}"
)

# Test 2.4: Technician sees pending jobs
resp = client.get("/api/jobs", headers={"Authorization": f"Bearer {tech_token}"})
log_result(
    "Technician sees all pending jobs",
    resp.status_code == 200 and len(resp.json()) == 2,
    f"Status: {resp.status_code}, Count: {len(resp.json())}"
)

# ==========================================
# 3. BIDS TESTS
# ==========================================
print("\n" + "=" * 55)
print("  💰 Testing Bids (/api/bids)")
print("=" * 55)

# Test 3.1: Technician submits a bid
resp = client.post("/api/bids",
    json={"job_id": job_id, "amount": 3500.0},
    headers={"Authorization": f"Bearer {tech_token}"}
)
log_result(
    "Technician submits bid (POST /api/bids)",
    resp.status_code == 200 and "bid_id" in resp.json(),
    f"Status: {resp.status_code}, Body: {resp.json()}"
)
bid_id = resp.json().get("bid_id")

# Test 3.2: User cannot submit a bid
resp = client.post("/api/bids",
    json={"job_id": job_id, "amount": 2000.0},
    headers={"Authorization": f"Bearer {user_token}"}
)
log_result(
    "User cannot submit bid (403)",
    resp.status_code == 403,
    f"Status: {resp.status_code}"
)

# Test 3.3: Bid on non-existent job
resp = client.post("/api/bids",
    json={"job_id": 9999, "amount": 1000.0},
    headers={"Authorization": f"Bearer {tech_token}"}
)
log_result(
    "Bid on non-existent job (404)",
    resp.status_code == 404,
    f"Status: {resp.status_code}"
)

# Test 3.4: View bids on a job
resp = client.get(f"/api/jobs/{job_id}/bids", headers={"Authorization": f"Bearer {user_token}"})
log_result(
    "View bids on a job (GET /api/jobs/{id}/bids)",
    resp.status_code == 200 and len(resp.json()) == 1,
    f"Status: {resp.status_code}, Count: {len(resp.json())}"
)

# Test 3.5: View bids on non-existent job
resp = client.get("/api/jobs/9999/bids", headers={"Authorization": f"Bearer {user_token}"})
log_result(
    "View bids on non-existent job (404)",
    resp.status_code == 404,
    f"Status: {resp.status_code}"
)

# ==========================================
# 4. BOOKINGS TESTS
# ==========================================
print("\n" + "=" * 55)
print("  📅 Testing Bookings (/api/bookings)")
print("=" * 55)

# Test 4.1: User accepts a bid and creates booking
resp = client.post("/api/bookings",
    json={"bid_id": bid_id},
    headers={"Authorization": f"Bearer {user_token}"}
)
log_result(
    "User accepts bid → booking created (POST /api/bookings)",
    resp.status_code == 200 and "booking_id" in resp.json(),
    f"Status: {resp.status_code}, Body: {resp.json()}"
)

# Test 4.2: Verify job status changed to 'active'
resp = client.get("/api/jobs", headers={"Authorization": f"Bearer {user_token}"})
jobs = resp.json()
booked_job = next((j for j in jobs if j["id"] == job_id), None)
log_result(
    "Job status updated to 'active' after booking",
    booked_job is not None and booked_job["status"] == "active",
    f"Status: {booked_job['status'] if booked_job else 'job not found'}"
)

# Test 4.3: Accept non-existent bid
resp = client.post("/api/bookings",
    json={"bid_id": 9999},
    headers={"Authorization": f"Bearer {user_token}"}
)
log_result(
    "Accept non-existent bid (404)",
    resp.status_code == 404,
    f"Status: {resp.status_code}"
)

# Test 4.4: Technician cannot accept a bid (not the job owner)
# First, create a new bid for the technician to try to accept
resp2 = client.post("/api/bookings",
    json={"bid_id": bid_id},
    headers={"Authorization": f"Bearer {tech_token}"}
)
log_result(
    "Technician cannot accept bid on someone else's job (403)",
    resp2.status_code == 403,
    f"Status: {resp2.status_code}"
)

# ==========================================
# 5. CHAT TESTS (Mocked AI Agent)
# ==========================================
print("\n" + "=" * 55)
print("  🤖 Testing AI Chat (/api/chat) — Mocked Agent")
print("=" * 55)

# Mock the agent graph to avoid calling Groq/Google APIs
mock_clarify_result = {
    "is_clarification_needed": True,
    "bot_response": "Aap kis shehar mein service chahte hain?",
    "extracted_intent": "AC Repair",
    "extracted_city": None,
    "extracted_town": None,
    "user_input": "",
    "conversation_history": [],
    "raw_businesses": [],
    "final_ranked_response": None
}

mock_complete_result = {
    "is_clarification_needed": False,
    "bot_response": None,
    "extracted_intent": "AC Repair",
    "extracted_city": "Lahore",
    "extracted_town": "Johar Town",
    "user_input": "",
    "conversation_history": [],
    "raw_businesses": [{"displayName": {"text": "Test AC"}, "rating": 4.5}],
    "final_ranked_response": "Yeh lijiye top AC repair wale:\n1. Test AC - Rating 4.5"
}

# Test 5.1: Chat returns clarification
with patch("main.graph") as mock_graph:
    mock_graph.invoke.return_value = mock_clarify_result
    resp = client.post("/api/chat",
        json={"message": "Mujhy AC repair chaiye"},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    log_result(
        "Chat: Agent asks for clarification",
        resp.status_code == 200 and resp.json()["status"] == "clarifying",
        f"Status: {resp.status_code}, Body: {resp.json()}"
    )

# Test 5.2: Chat returns completed results
with patch("main.graph") as mock_graph:
    mock_graph.invoke.return_value = mock_complete_result
    resp = client.post("/api/chat",
        json={"message": "AC Repair Johar Town Lahore"},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    log_result(
        "Chat: Agent returns ranked results + auto-creates job",
        resp.status_code == 200 and resp.json()["status"] == "completed" and "job_id" in resp.json(),
        f"Status: {resp.status_code}, Body: {resp.json()}"
    )

# Test 5.3: Chat without auth
resp = client.post("/api/chat", json={"message": "test"})
log_result(
    "Chat: Reject unauthenticated request (401)",
    resp.status_code == 401,
    f"Status: {resp.status_code}"
)

# ==========================================
# SUMMARY
# ==========================================
print("\n" + "=" * 55)
total = PASSED + FAILED
print(f"  🏁 Test Results: {PASSED}/{total} passed")
if FAILED == 0:
    print("  🎉 All tests passed!")
else:
    print(f"  ⚠️  {FAILED} test(s) failed.")
print("=" * 55 + "\n")

sys.exit(0 if FAILED == 0 else 1)

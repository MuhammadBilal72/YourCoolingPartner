# YourCoolingPartner — V2 Agentic Architecture Implementation Plan

This document outlines the full restructured architecture with a **Brain Agent router**, persistent **chat history**, and an end-to-end conversational booking flow.

---

## 1. New Database Tables

### Table: `conversations`
| Column | Type | Notes |
| :--- | :--- | :--- |
| `id` | Integer | Primary Key |
| `user_id` | Integer | FK → `users.id` |
| `created_at` | String | Timestamp |

> Each user has **one active conversation** at a time.

### Table: `messages`
| Column | Type | Notes |
| :--- | :--- | :--- |
| `id` | Integer | Primary Key |
| `conversation_id` | Integer | FK → `conversations.id` |
| `sender` | String | `"user"` or `"agent"` |
| `content` | Text | Message text (user msg, agent response, technician list, etc.) |
| `timestamp` | String | For ordering |

> The `content` field stores everything as text — plain user messages, formatted technician lists, booking confirmations, etc.

### Existing Tables (No Changes)
- `users` — unchanged
- `jobs` — unchanged
- `bids` — unchanged
- `bookings` — unchanged

---

## 2. Updated Agent Architecture

### Current (V1) — Linear Flow
```
Intent Parser → Google Maps → Ranking → END
```
Can only search for technicians. No scheduling, no booking, no bid handling.

### New (V2) — Brain Router Architecture
```
                     ┌──────────────────┐
     User Message ──►│   Brain Agent    │  (Groq LLM)
                     │  Reads history   │
                     │  Decides action  │
                     └────────┬─────────┘
                              │
              ┌───────┬───────┼────────┬──────────┐
              ▼       ▼       ▼        ▼          ▼
          Search   Create   Show    Create     Clarify
          Maps +   Job      Bids   Booking   (ask info)
          Ranking
```

### Brain Agent Decision Format

The Brain Agent receives the full conversation history + user's latest message and returns a structured JSON decision:

```json
{ "action": "clarify", "message": "Kis shehar mein service chahiye?" }
```
```json
{ "action": "search_technicians", "intent": "AC Repair", "city": "Lahore", "town": "Johar Town" }
```
```json
{ "action": "create_job", "date": "2026-05-21", "time": "10:00 AM" }
```
```json
{ "action": "show_bids" }
```
```json
{ "action": "create_booking", "technician_name": "Bilal AC Wala" }
```

---

## 3. Updated AgentState

```python
class AgentState(TypedDict):
    # IDs passed from main.py
    user_id: int
    conversation_id: int

    # Current input
    user_input: str
    conversation_history: List[Dict[str, str]]

    # Brain decision
    action: str  # "clarify", "search_technicians", "create_job", "show_bids", "create_booking"

    # Search fields
    extracted_intent: Optional[str]
    extracted_city: Optional[str]
    extracted_town: Optional[str]

    # Results
    raw_businesses: List[Dict[str, Any]]

    # Final response to send back to user
    bot_response: Optional[str]
```

---

## 4. LangGraph Node Definitions

### Node 1: `brain_agent` (Entry Point)
- **Model**: Groq Llama 3.3 70B
- **Input**: Full conversation history + latest user message
- **Output**: Sets `action` field in state
- **Prompt**: Given the conversation, decide what the user wants and return a JSON action.

### Node 2: `search_technicians`
- **Triggered when**: `action == "search_technicians"`
- **Logic**:
  1. Calls Google Maps API with `intent`, `city`, `town`
  2. Ranks results using Groq LLM
  3. Saves agent message (with technician list) to `messages` table
  4. Returns formatted response
- **Cost saving**: Check `messages` table first — if same search was done <24hrs ago, reuse cached results

### Node 3: `create_job`
- **Triggered when**: `action == "create_job"`
- **Logic**:
  1. Extracts date/time from brain's decision
  2. Gets user's latest search context (intent, city, town) from conversation history
  3. Inserts a new row in `jobs` table with `status: "pending"`
  4. Saves confirmation message to `messages` table
  5. Returns: "Job create ho gaya! Technicians se bids ka intezaar karein."

### Node 4: `show_bids`
- **Triggered when**: `action == "show_bids"`
- **Logic**:
  1. Queries user's latest pending job from `jobs` table
  2. Fetches all bids from `bids` table for that job
  3. Formats bid list with technician name + amount
  4. Saves to `messages` table
  5. Returns formatted bid list

### Node 5: `create_booking`
- **Triggered when**: `action == "create_booking"`
- **Logic**:
  1. Gets `technician_name` from brain's decision
  2. Finds matching bid (fuzzy match on technician name)
  3. Creates entry in `bookings` table
  4. Updates job `status` → `"active"`
  5. Saves confirmation to `messages` table
  6. Returns: "Booking confirm! Bilal AC Wala aapke paas aayenge."

### Node 6: `clarify`
- **Triggered when**: `action == "clarify"`
- **Logic**: Simply returns the brain's clarification message. Saves to `messages` table.

---

## 5. Updated Graph Routing

```python
workflow = StateGraph(AgentState)

# Nodes
workflow.add_node("brain", brain_agent_node)
workflow.add_node("search_technicians", search_technicians_node)
workflow.add_node("create_job", create_job_node)
workflow.add_node("show_bids", show_bids_node)
workflow.add_node("create_booking", create_booking_node)
workflow.add_node("clarify", clarify_node)

# Entry point
workflow.set_entry_point("brain")

# Brain routes to the correct node
workflow.add_conditional_edges(
    "brain",
    route_by_action,
    {
        "search_technicians": "search_technicians",
        "create_job": "create_job",
        "show_bids": "show_bids",
        "create_booking": "create_booking",
        "clarify": "clarify"
    }
)

# All action nodes go to END after executing
workflow.add_edge("search_technicians", END)
workflow.add_edge("create_job", END)
workflow.add_edge("show_bids", END)
workflow.add_edge("create_booking", END)
workflow.add_edge("clarify", END)

graph = workflow.compile()
```

---

## 6. Updated API Endpoints

### Changed Endpoints

#### `POST /api/chat`
- Now saves every user message and agent response to the `messages` table
- Loads conversation history from DB (not in-memory dict)
- Passes `user_id` + `conversation_id` to agent

#### `GET /api/chat/history`
- New endpoint
- Returns all messages for the user's active conversation
- Android app calls this on startup to load chat bubbles

### Unchanged Endpoints
- `POST /auth/login` — no changes
- `GET /api/jobs` — technicians see pending jobs
- `POST /api/bids` — technicians submit bids
- `GET /api/jobs/{id}/bids` — view bids on a job

---

## 7. Full User Flow (End-to-End)

```
USER: "Mujhy Johar Town Lahore ma AC repair chaiye"
  → Brain: action = "search_technicians"
  → Maps API fetches 20 businesses
  → Ranking LLM picks top 10
  → AGENT: "Yeh hain aapke top technicians: 1. Cool Master..."
  → Saved to messages table

USER: "Kal subah 10 baje book karna hai"
  → Brain: action = "create_job", date = "kal", time = "10:00 AM"
  → Job created in DB (status: pending)
  → AGENT: "Job create ho gaya! Bids ka intezaar karein."
  → Saved to messages table

--- Technician opens app, sees job, places bid ---

USER: "Koi bids aayi hain?"
  → Brain: action = "show_bids"
  → Fetches bids from DB
  → AGENT: "2 bids hain: 1. Bilal Rs.1200  2. Kamran Rs.1500"
  → Saved to messages table

USER: "Bilal ko book karo"
  → Brain: action = "create_booking", technician = "Bilal"
  → Booking created, job status → active
  → AGENT: "Booking confirm! Bilal kal 10 baje aayenge. ✅"
  → Saved to messages table
```

---

## 8. File Changes Summary

| File | Change |
| :--- | :--- |
| `db/database.py` | Add `Conversation` and `Message` models |
| `agent/agent.py` | Full rewrite — Brain Agent + 5 action nodes |
| `main.py` | Update `/api/chat` to use DB for history, add `GET /api/chat/history` |
| `db/seeds.py` | Add sample conversations and messages |

---

## 9. Implementation Order

1. **Add new DB models** (`Conversation`, `Message`) to `db/database.py`
2. **Rewrite agent** with Brain Agent + action nodes in `agent/agent.py`
3. **Update main.py** — persistent chat, new history endpoint
4. **Update seeds** — add sample conversations
5. **Test** — run full flow end-to-end

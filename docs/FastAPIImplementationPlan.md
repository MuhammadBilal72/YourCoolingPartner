# FastAPI Implementation Plan: YourCoolingPartner Backend

This document outlines the architecture and implementation steps for converting the LangGraph agent workflow into a robust FastAPI backend for your Android application.

## 1. Tech Stack
- **Framework**: FastAPI (High performance, async, auto-generates Swagger documentation).
- **Database**: SQLite (Perfect for hackathons, fast and simple).
- **ORM**: SQLAlchemy or SQLModel (For easy database interactions).
- **Authentication**: Basic Mobile Number + Password. (Returns a session or JWT).
- **AI Core**: The existing `agent.py` LangGraph workflow.

---

## 2. Database Schema (SQLite)

We will create four primary tables to manage users, jobs, bids, and bookings.

### Table: `users`
| Column | Type | Notes |
| :--- | :--- | :--- |
| `id` | Integer | Primary Key |
| `name` | String | |
| `mobile_number`| String | Unique (Used for login) |
| `role` | String | `user` or `technician` |
| `hashed_password`| String | Securely hashed password |

### Table: `jobs`
| Column | Type | Notes |
| :--- | :--- | :--- |
| `id` | Integer | Primary Key |
| `user_id` | Integer | Foreign Key -> `users.id` |
| `city` | String | (Populated by the AI Agent) |
| `town` | String | (Populated by the AI Agent) |
| `status` | String | `pending`, `active`, `completed` |
| `date` | String | |
| `time` | String | |

### Table: `bids`
| Column | Type | Notes |
| :--- | :--- | :--- |
| `id` | Integer | Primary Key |
| `job_id` | Integer | Foreign Key -> `jobs.id` |
| `technician_id`| Integer | Foreign Key -> `users.id` |
| `amount` | Float | The price the technician is offering |

### Table: `bookings`
| Column | Type | Notes |
| :--- | :--- | :--- |
| `id` | Integer | Primary Key |
| `technician_id`| Integer | Foreign Key -> `users.id` |
| `user_id` | Integer | Foreign Key -> `users.id` |
| `date` | String | |
| `time` | String | |
| `amount` | Float | Final agreed amount |

---

## 3. Core API Endpoints

The Android app will communicate with these REST endpoints:

### Authentication Endpoints
- **`POST /auth/login`**: Accepts mobile number and password. If the mobile number does not exist, it automatically creates a new account (No separate sign-up required). Returns an authentication token for the session.

### AI Agent Chat Endpoint
- **`POST /api/chat`**
  - **Input**: `{"message": "Mujhy Johar town ma AC repair chaiye"}`
  - **Logic**: Calls your LangGraph `graph.invoke()`. 
  - **State Management**: The FastAPI backend will need to store the `conversation_history`, `extracted_intent`, etc., in a temporary cache (mapped to the user's ID) so the conversation can be multi-turn over the API.
  - **Output**: Returns the bot's response string.

### Business Logic Endpoints
- **`POST /api/jobs`**: Create a new job ticket.
- **`GET /api/jobs`**: Fetch jobs in a specific city/town (used by Technicians to find work).
- **`POST /api/bids`**: Technicians submit a bid on a job.
- **`GET /api/jobs/{id}/bids`**: Users can view all bids on their job.
- **`POST /api/bookings`**: User accepts a bid and locks in a booking.

---

## 4. Integration Strategy: Connecting the AI to the DB

Right now, **Agent 2** searches Google Maps. In the new system, we can upgrade this:
1. When the AI finishes extracting "AC Repair", "Lahore", "Johar Town", instead of just searching Google Maps, the FastAPI backend automatically creates a **Job entry** in the `jobs` table.
2. Local technicians (registered in the DB) get notified and can place **Bids**.
3. **Agent 3** can then rank the *actual* bids coming from real local technicians in the SQLite database, falling back to Google Maps businesses only if no local technicians are available.

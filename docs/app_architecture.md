# YourCoolingPartner — Android App Architecture

This document defines the screen layout, navigation, and API integration for both **User** and **Technician** roles in the Android app.

---

## 1. App Entry Point

```
App Opens
    │
    ▼
┌──────────────┐
│  Login Screen│
│              │
│  Mobile: [__]│
│  Password:[_]│
│  [  Login  ] │
└──────┬───────┘
       │
       ▼
  POST /auth/login
       │
       ├── role = "user"        → User App
       └── role = "technician"  → Technician App
```

Both roles share the **same login screen**. The API returns the user's `role` in the response, and the app routes to the correct interface.

---

## 2. User App Screens

### Screen Flow

```
Login → Chat Screen (Main)
              │
              ├── Polls for bids (when job is pending)
              └── Shows full conversation history
```

### Screen: Chat Interface (Main Screen)

This is the **only screen** the user needs. Everything happens through chat.

```
┌─────────────────────────────────┐
│  ❄️ YourCoolingPartner          │
│─────────────────────────────────│
│                                 │
│  🤖 Assalam-o-Alaikum! Kya     │
│     service chahiye?            │
│                                 │
│  👤 Mujhy Johar Town Lahore    │
│     ma AC repair chaiye         │
│                                 │
│  🤖 🔍 Searching...            │
│  🤖 🗺️ Finding technicians... │
│  🤖 🏆 Ranking results...      │
│                                 │
│  🤖 Yeh hain aapke top         │
│     technicians:                │
│     1. Cool Master — ⭐ 4.8     │
│     2. Bilal AC Wala — ⭐ 4.5   │
│     Kab schedule karna chahte   │
│     hain?                       │
│                                 │
│  👤 Kal subah 10 baje           │
│                                 │
│  🤖 ✅ Job post ho gaya!        │
│     Bids ka intezaar karein.    │
│                                 │
│  🤖 🔔 2 bids aayi hain:       │
│     1. Bilal — Rs.1200          │
│     2. Kamran — Rs.1800         │
│     Kisko book karein?          │
│                                 │
│  👤 Bilal ko book karo          │
│                                 │
│  🤖 ✅ Booking confirm!         │
│     Bilal kal 10 baje aayenge.  │
│                                 │
│─────────────────────────────────│
│  [  Type a message...     ] [➤] │
└─────────────────────────────────┘
```

### User Chat — API Integration

| Action | API Call | When |
| :--- | :--- | :--- |
| App opens | `GET /api/chat/history` | Load saved chat bubbles from DB |
| User sends message | `POST /api/chat` | Every time user taps Send |
| Show loading states | Client-side animation | While waiting for API response |
| Poll for bids | `GET /api/jobs` → find pending → `GET /api/jobs/{id}/bids` | Every 10 seconds when a job is pending |
| Check if polling needed | `GET /api/jobs` | On app open — if any job has `status: "pending"`, start polling |

### User Chat — Polling Logic

```
App Opens
    │
    ├── GET /api/chat/history → Load chat bubbles
    │
    ├── GET /api/jobs → Any job with status "pending"?
    │       │
    │       ├── YES → Start polling GET /api/jobs/{id}/bids every 10s
    │       │         │
    │       │         ├── New bids found?
    │       │         │     └── YES → Show as new agent bubble:
    │       │         │              "🔔 2 bids aayi hain: ..."
    │       │         │
    │       │         └── No new bids → Continue polling
    │       │
    │       └── NO  → Show normal chat input
```

### User Chat — Loading Animation (Client-Side)

When `POST /api/chat` is called, show these timed bubbles while waiting:

```
0ms    → Show: "🔍 Understanding your requirement..."
800ms  → Show: "🗺️ Finding nearest technicians..."
1600ms → Show: "🏆 Ranking best matches..."
~3s    → API returns → Replace loading bubbles with actual response
```

These are **purely UI animations**. No backend changes needed.

---

## 3. Technician App Screens

### Screen Flow

```
Login → Home Screen
           │
           ├── View Jobs → Job List → Job Detail → Place Bid
           │
           └── My Bookings → Booking List
```

### Screen: Home (After Login)

```
┌─────────────────────────────────┐
│  ❄️ YourCoolingPartner          │
│  Welcome, Bilal AC Wala         │
│─────────────────────────────────│
│                                 │
│  ┌─────────────────────────┐   │
│  │  📋 View Available Jobs  │   │
│  │  See pending jobs near   │   │
│  │  you and place bids      │   │
│  └─────────────────────────┘   │
│                                 │
│  ┌─────────────────────────┐   │
│  │  📅 My Bookings          │   │
│  │  Jobs you've been        │   │
│  │  booked for              │   │
│  └─────────────────────────┘   │
│                                 │
└─────────────────────────────────┘
```

### Screen: View Jobs (Job List)

```
┌─────────────────────────────────┐
│  ← Available Jobs               │
│─────────────────────────────────│
│                                 │
│  ┌─────────────────────────┐   │
│  │ 📍 Johar Town, Lahore    │   │
│  │ 📅 2026-05-20 | 10:00 AM │   │
│  │ Status: 🟡 Pending       │   │
│  │                [View →]  │   │
│  └─────────────────────────┘   │
│                                 │
│  ┌─────────────────────────┐   │
│  │ 📍 DHA Phase 5, Karachi  │   │
│  │ 📅 2026-05-22 | 11:00 AM │   │
│  │ Status: 🟡 Pending       │   │
│  │                [View →]  │   │
│  └─────────────────────────┘   │
│                                 │
└─────────────────────────────────┘
```

**API**: `GET /api/jobs` (returns all pending jobs for technicians)

### Screen: Job Detail + Place Bid

```
┌─────────────────────────────────┐
│  ← Job #1                       │
│─────────────────────────────────│
│                                 │
│  📍 Location: Johar Town,      │
│               Lahore            │
│  📅 Date: 2026-05-20            │
│  ⏰ Time: 10:00 AM              │
│  📌 Status: Pending             │
│                                 │
│─────────────────────────────────│
│                                 │
│  💰 Your Labour Charge (Rs):    │
│  ┌─────────────────────────┐   │
│  │  1500                    │   │
│  └─────────────────────────┘   │
│                                 │
│  ⚠️ Parts replacement charges   │
│     will be discussed with the  │
│     customer separately.        │
│                                 │
│  ┌─────────────────────────┐   │
│  │     [ Submit Bid ]       │   │
│  └─────────────────────────┘   │
│                                 │
└─────────────────────────────────┘
```

**API**: `POST /api/bids` with `{ "job_id": 1, "amount": 1500 }`

### Screen: My Bookings

```
┌─────────────────────────────────┐
│  ← My Bookings                  │
│─────────────────────────────────│
│                                 │
│  ┌─────────────────────────┐   │
│  │ 👤 Customer: Ahmed Khan   │   │
│  │ 📍 Johar Town, Lahore    │   │
│  │ 📅 2026-05-20 | 10:00 AM │   │
│  │ 💰 Labour: Rs.1500       │   │
│  │ Status: 🟢 Active        │   │
│  └─────────────────────────┘   │
│                                 │
│  (No more bookings)             │
│                                 │
└─────────────────────────────────┘
```

**API**: `GET /api/jobs` (returns jobs where technician has an active booking)

> **Note**: Currently `GET /api/jobs` returns pending jobs for technicians. A future improvement would be to add a query parameter like `?status=active` or a dedicated `GET /api/bookings` endpoint to fetch the technician's confirmed bookings.

---

## 4. API → Screen Mapping

| Screen | API Endpoint | Method |
| :--- | :--- | :--- |
| Login | `/auth/login` | POST |
| User Chat — Load history | `/api/chat/history` | GET |
| User Chat — Send message | `/api/chat` | POST |
| User Chat — Check for pending job | `/api/jobs` | GET |
| User Chat — Poll for bids | `/api/jobs/{id}/bids` | GET |
| Technician — View Jobs | `/api/jobs` | GET |
| Technician — Place Bid | `/api/bids` | POST |
| Technician — My Bookings | `/api/jobs` | GET |

---

## 5. Tech Stack (Android)

| Component | Recommended |
| :--- | :--- |
| Language | Kotlin |
| UI | Jetpack Compose |
| HTTP Client | Retrofit + OkHttp |
| JSON Parsing | Gson or Moshi |
| Token Storage | SharedPreferences (encrypted) |
| Navigation | Jetpack Navigation |
| Polling | Coroutines with `delay()` loop |

---

## 6. Navigation Summary

```
┌──────────────────────────────────────────────────┐
│                   LOGIN SCREEN                    │
│              (shared by both roles)               │
└─────────────────────┬────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
┌─────────────────┐    ┌──────────────────┐
│   USER APP       │    │  TECHNICIAN APP   │
│                 │    │                  │
│  Chat Screen    │    │  Home Screen     │
│  (single page)  │    │    │             │
│                 │    │    ├── View Jobs  │
│  Everything     │    │    │   └── Bid   │
│  happens here   │    │    │             │
│                 │    │    └── Bookings  │
└─────────────────┘    └──────────────────┘
```

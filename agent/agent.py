import os
import json
import requests
from datetime import datetime, timedelta, timezone
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 1. State Definition
# ==========================================
class AgentState(TypedDict):
    user_id: int
    conversation_id: int
    user_input: str
    conversation_history: List[Dict[str, str]]

    # Brain decision
    action: Optional[str]

    # Search fields
    extracted_intent: Optional[str]
    extracted_city: Optional[str]
    extracted_town: Optional[str]

    # Scheduling
    schedule_date: Optional[str]
    schedule_time: Optional[str]

    # Booking
    technician_name: Optional[str]

    # Results
    raw_businesses: List[Dict[str, Any]]
    my_bookings: Optional[List[Dict[str, Any]]]

    # Final response to user
    bot_response: Optional[str]

# ==========================================
# 2. Node Definitions
# ==========================================

def brain_agent_node(state: AgentState) -> AgentState:
    """Brain Agent: Analyzes conversation and decides what action to take."""

    print("\n🧠 [Brain Agent] Analyzing user message...")
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

    history_text = ""
    for msg in state["conversation_history"]:
        role = msg["role"].upper()
        history_text += f"{role}: {msg['content']}\n"

    prompt = f"""You are the brain of YourCoolingPartner, an AI assistant that helps users find and book AC/plumbing technicians in Pakistan.
Users speak in proper Urdu script, Roman Urdu, or English.

CONVERSATION HISTORY:
{history_text}

LATEST MESSAGE: "{state['user_input']}"

Decide what action to take. Available actions:
1. "clarify" — User hasn't provided enough info. Ask for missing details.
2. "search_technicians" — User wants to find technicians. Requires intent (service type), city, and town.
3. "create_job" — User wants to schedule a job. They must have already searched. Now providing date/time.
4. "show_bids" — User wants to see bids on their posted job.
5. "create_booking" — User wants to book a specific technician by name.

6. "show_bookings" — User wants to see their past or active bookings (e.g. "Show me my bookings" or "Mujhy meri bookings dikhao").

Rules:
- CRITICAL: Interpret the user's LATEST MESSAGE as a direct answer to the most recent AGENT message in the CONVERSATION HISTORY. Do not lose the context of what you just asked them.
- If service type, city, AND town are not all known from the conversation → "clarify"
- If all three are known and no search done yet → "search_technicians"
- If user mentions date/time after seeing results → "create_job"
- If user asks about bids → "show_bids"
- If user names a technician to book → "create_booking"
- If user asks to see their bookings → "show_bookings"

Return STRICT JSON only:
{{
    "action": "string",
    "intent": "service type or null",
    "city": "city or null",
    "town": "town/area or null",
    "date": "date or null",
    "time": "time or null",
    "technician_name": "name or null",
    "message": "Your helpful response asking the user for missing details (only for clarify action, else null). CRITICAL: Identify the language of the user's LATEST MESSAGE. You MUST write this message in that EXACT SAME language (e.g., if they wrote in English, you MUST reply in English. If Roman Urdu, reply in Roman Urdu). DO NOT copy their message."
}}"""

    response = llm.invoke([HumanMessage(content=prompt)])

    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()

        decision = json.loads(content)
        action = decision.get("action", "clarify")
        print(f"   🎯 Decision: {action}")

        return {
            **state,
            "action": action,
            "extracted_intent": decision.get("intent") or state.get("extracted_intent"),
            "extracted_city": decision.get("city") or state.get("extracted_city"),
            "extracted_town": decision.get("town") or state.get("extracted_town"),
            "schedule_date": decision.get("date"),
            "schedule_time": decision.get("time"),
            "technician_name": decision.get("technician_name"),
            "bot_response": decision.get("message"),
        }
    except Exception as e:
        print(f"   ❌ Brain error: {e}")
        return {
            **state,
            "action": "clarify",
            "bot_response": "Mujhy samajh nahi aayi, kya aap dobara bata sakte hain?"
        }


def search_technicians_node(state: AgentState) -> AgentState:
    """Searches Google Maps and ranks results."""

    intent = state["extracted_intent"]
    city = state["extracted_city"]
    town = state["extracted_town"]

    # --- Google Maps Search ---
    print(f"\n🗺️  [Search Agent] Searching for '{intent}' in {town}, {city}...")

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    businesses = []

    if not api_key:
        print("   ⚠️  No API key — using simulated data")
        businesses = [
            {"displayName": {"text": f"Simulated {intent} Expert 1"}, "rating": 4.8, "formattedAddress": f"Main Market {town}, {city}", "nationalPhoneNumber": "03001234567"},
            {"displayName": {"text": f"Simulated {intent} Pro 2"}, "rating": 4.2, "formattedAddress": f"Street 2, {town}, {city}", "nationalPhoneNumber": "03211234567"},
        ]
    else:
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.rating,places.formattedAddress,places.nationalPhoneNumber",
        }
        payload = {"textQuery": f"{intent} in {town}, {city}", "pageSize": 20}

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            businesses = response.json().get("places", [])
            print(f"   📍 Found {len(businesses)} businesses")
        except Exception as e:
            print(f"   ❌ Maps error: {e}")

    if not businesses:
        return {**state, "raw_businesses": [], "bot_response": "Maaf karna, us ilaqay mein koi service providers nahi milay."}

    # --- Ranking ---
    print(f"\n🏆 [Ranking Agent] Ranking top technicians...")
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

    rank_prompt = f"""You have businesses for {intent} in {town}, {city}.
Rank the top 10 by rating. 

IMPORTANT: Write your entire response in the EXACT language and script used in the user's latest message: "{state['user_input']}"
- If they used proper Urdu script (e.g., معاف کیجیے), reply in proper Urdu script.
- If they used Roman Urdu (e.g., Mujhy AC repair krwana), reply in Roman Urdu.
- If they used English (e.g., I want to book), reply in English.

Businesses: {json.dumps(businesses, indent=2)}

Format:
- Polite greeting
- Numbered list: Name, Address, Rating, Phone (Separate each technician using \\n so they appear on 1 row each)
- End with: "When do you want to schedule this? Please provide day and time." (translated into the matching language)
"""

    rank_response = llm.invoke([HumanMessage(content=rank_prompt)])
    print("   ✅ Ranked and formatted!")

    return {**state, "raw_businesses": businesses, "bot_response": rank_response.content.strip()}


def format_date_time(natural_date: str, natural_time: str) -> tuple[str, str]:
    pk_time = datetime.now(timezone.utc) + timedelta(hours=5)
    current_time_str = pk_time.strftime("%A, %Y-%m-%d %I:%M %p")

    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    prompt = f"""The current date and time in Pakistan is: {current_time_str}.
The user requested a service for Date: "{natural_date}" and Time: "{natural_time}".

Convert the user's requested date and time into standard format.
If it's relative like 'kal' (tomorrow) or 'parso', calculate the exact date based on the current date provided above.
If the user didn't provide a specific time, use "ASAP".

Return STRICT JSON only:
{{
    "formatted_date": "YYYY-MM-DD",
    "formatted_time": "HH:MM AM/PM"
}}"""
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
        
        data = json.loads(content)
        return data.get("formatted_date", natural_date), data.get("formatted_time", natural_time)
    except:
        return natural_date, natural_time

def create_job_node(state: AgentState) -> AgentState:
    """Creates a job in the database."""
    from db.database import SessionLocal, Job

    print("\n📋 [Job Agent] Creating job posting...")
    db = SessionLocal()

    natural_date = state.get("schedule_date") or "Pending"
    natural_time = state.get("schedule_time") or "ASAP"
    formatted_date, formatted_time = format_date_time(natural_date, natural_time)

    try:
        job = Job(
            user_id=state["user_id"],
            city=state.get("extracted_city", ""),
            town=state.get("extracted_town", ""),
            status="pending",
            date=formatted_date,
            time=formatted_time,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        print(f"   ✅ Job #{job.id} created!")

        date_text = formatted_date
        time_text = formatted_time

        return {
            **state,
            "bot_response": (
                f"✅ Aapka job post ho gaya hai! (Job #{job.id})\n"
                f"📍 {state.get('extracted_town', '')}, {state.get('extracted_city', '')}\n"
                f"📅 {date_text} {time_text}\n\n"
                f"Technicians se bids ka intezaar karein. Jab bids aayein to 'bids dikhao' likh dein."
            ),
        }
    finally:
        db.close()


def show_bids_node(state: AgentState) -> AgentState:
    """Shows bids on user's pending job."""
    from db.database import SessionLocal, Job, Bid, User

    print("\n💰 [Bids Agent] Fetching bids...")
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.user_id == state["user_id"], Job.status == "pending").order_by(Job.id.desc()).first()

        if not job:
            return {**state, "bot_response": "Aapka koi pending job nahi hai. Pehle technician search karein aur job create karein."}

        bids = db.query(Bid).filter(Bid.job_id == job.id).all()

        if not bids:
            return {**state, "bot_response": f"Job #{job.id} par abhi tak koi bid nahi aayi. Thora intezaar karein."}

        bid_lines = []
        for i, bid in enumerate(bids, 1):
            tech = db.query(User).filter(User.id == bid.technician_id).first()
            tech_name = tech.name if tech else f"Technician #{bid.technician_id}"
            bid_lines.append(f"{i}. {tech_name} — Labour: Rs.{bid.amount}")

        bid_text = "\n".join(bid_lines)
        print(f"   ✅ Found {len(bids)} bids")

        return {
            **state,
            "bot_response": f"🔔 Job #{job.id} par {len(bids)} bids hain:\n\n{bid_text}\n\nKisko book karna chahte hain? Naam likh dein.",
        }
    finally:
        db.close()


def create_booking_node(state: AgentState) -> AgentState:
    """Creates a booking with the specified technician."""
    from db.database import SessionLocal, Job, Bid, Booking, User

    print("\n📅 [Booking Agent] Creating booking...")
    tech_name = state.get("technician_name", "")

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.user_id == state["user_id"], Job.status == "pending").order_by(Job.id.desc()).first()

        if not job:
            return {**state, "bot_response": "Koi pending job nahi mili. Pehle job create karein."}

        bids = db.query(Bid).filter(Bid.job_id == job.id).all()

        matched_bid = None
        matched_tech = None
        for bid in bids:
            tech = db.query(User).filter(User.id == bid.technician_id).first()
            if tech and tech_name.lower() in tech.name.lower():
                matched_bid = bid
                matched_tech = tech
                break

        if not matched_bid:
            return {**state, "bot_response": f"'{tech_name}' naam ka koi bidder nahi mila. 'bids dikhao' likh kar dobara dekhein."}

        booking = Booking(
            job_id=job.id,
            technician_id=matched_bid.technician_id,
            user_id=state["user_id"],
            date=job.date,
            time=job.time,
            amount=matched_bid.amount,
        )
        db.add(booking)
        job.status = "active"
        db.commit()
        db.refresh(booking)

        print(f"   ✅ Booking #{booking.id} confirmed!")

        return {
            **state,
            "bot_response": (
                f"✅ Booking confirm ho gayi hai!\n\n"
                f"👤 Technician: {matched_tech.name}\n"
                f"💰 Labour: Rs.{matched_bid.amount}\n"
                f"📅 {job.date} {job.time}\n"
                f"📍 {job.town}, {job.city}\n\n"
                f"Parts replacement charges alag se lagein ge. Shukriya!"
            ),
        }
    finally:
        db.close()


def show_bookings_node(state: AgentState) -> AgentState:
    """Shows the user all of their bookings. (This tool queries the db and finds all bookings of the user from bookings table where user_id is logged in user_id)."""
    from db.database import SessionLocal, Booking, User
    
    print("\n📅 [Bookings Agent] Fetching user bookings...")
    db = SessionLocal()
    try:
        bookings = db.query(Booking).filter(Booking.user_id == state["user_id"]).all()
        
        if not bookings:
            return {**state, "bot_response": "Aapki koi bookings nahi hain.", "my_bookings": []}
            
        booking_list = []
        response_lines = ["Aapki Bookings:\n"]
        
        for b in bookings:
            tech = db.query(User).filter(User.id == b.technician_id).first()
            tech_name = tech.name if tech else "Unknown"
            
            booking_list.append({
                "id": b.id,
                "name": tech_name,
                "date": b.date
            })
            response_lines.append(f"• ID: {b.id} | Technician: {tech_name} | Date: {b.date}")
            
        return {
            **state,
            "bot_response": "\n".join(response_lines),
            "my_bookings": booking_list
        }
    finally:
        db.close()

def clarify_node(state: AgentState) -> AgentState:
    """Returns clarification message from brain."""
    print(f"\n💬 [Clarify] Asking user for more info...")
    return state

def format_response_node(state: AgentState) -> AgentState:
    """Translates hardcoded bot_responses into the user's language."""
    print("\n🌐 [Language Agent] Matching user language...")
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    
    prompt = f"""You are a translation agent.
Your task is to translate the SYSTEM MESSAGE into the same language used in the USER MESSAGE.

USER MESSAGE (for language reference only):
"{state['user_input']}"

SYSTEM MESSAGE TO TRANSLATE:
"{state.get('bot_response', '')}"

INSTRUCTIONS:
1. Identify the language/script of the USER MESSAGE (e.g., English, Roman Urdu, or proper Urdu script).
2. Translate the SYSTEM MESSAGE into that exact language/script.
3. DO NOT answer the user message.
4. DO NOT copy or repeat the user message.
5. Keep all bullet points, numbers, IDs, and formatting exactly intact.

Return STRICT JSON ONLY, containing no other text, explanation, or conversational filler:
{{
    "translated_message": "your translated text here"
}}"""
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        data = json.loads(content)
        translated = data.get("translated_message")
        if translated:
            return {**state, "bot_response": translated}
        return state
    except Exception as e:
        return state


# ==========================================
# 3. Routing and Graph Compilation
# ==========================================

def route_by_action(state: AgentState):
    action = state.get("action", "clarify")
    if action in ["search_technicians", "create_job", "show_bids", "create_booking", "show_bookings"]:
        return action
    return "clarify"


workflow = StateGraph(AgentState)

# Nodes
workflow.add_node("brain", brain_agent_node)
workflow.add_node("search_technicians", search_technicians_node)
workflow.add_node("create_job", create_job_node)
workflow.add_node("show_bids", show_bids_node)
workflow.add_node("create_booking", create_booking_node)
workflow.add_node("show_bookings", show_bookings_node)
workflow.add_node("clarify", clarify_node)
workflow.add_node("format_response", format_response_node)

# Entry point
workflow.set_entry_point("brain")

# Brain routes conditionally
workflow.add_conditional_edges(
    "brain",
    route_by_action,
    {
        "search_technicians": "search_technicians",
        "create_job": "create_job",
        "show_bids": "show_bids",
        "create_booking": "create_booking",
        "show_bookings": "show_bookings",
        "clarify": "clarify",
    },
)

workflow.add_edge("search_technicians", END)
workflow.add_edge("clarify", END)

workflow.add_edge("create_job", "format_response")
workflow.add_edge("show_bids", "format_response")
workflow.add_edge("create_booking", "format_response")
workflow.add_edge("show_bookings", "format_response")

workflow.add_edge("format_response", END)

# Compile
graph = workflow.compile()

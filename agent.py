import os
import json
import requests
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 1. State Definition
# ==========================================
class AgentState(TypedDict):
    user_input: str
    conversation_history: List[Dict[str, str]]  # Tracks full conversation for context
    extracted_intent: Optional[str]
    extracted_city: Optional[str]
    extracted_town: Optional[str]
    is_clarification_needed: bool
    bot_response: Optional[str]
    raw_businesses: List[Dict[str, Any]]
    final_ranked_response: Optional[str]

# ==========================================
# 2. Nodes Definition
# ==========================================

def intent_parsing_node(state: AgentState) -> AgentState:
    """Agent 1: Parses intent, city, and town using full conversation history.
    Merges newly extracted fields with previously extracted ones so info accumulates."""
    
    print("\n🔍 [Agent 1] Parsing user query...")
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    
    # Build the full conversation context so the LLM sees every past message
    history_text = ""
    for msg in state["conversation_history"]:
        role = msg["role"].upper()
        history_text += f"{role}: {msg['content']}\n"
    
    # Include any previously extracted info so the LLM can merge/update
    prev_intent = state.get("extracted_intent") or "Not yet known"
    prev_city = state.get("extracted_city") or "Not yet known"
    prev_town = state.get("extracted_town") or "Not yet known"
    
    prompt = f"""You are an assistant parsing user requests for home services in Pakistan.
The user may speak in Roman Urdu, English, or a mix of both.

Here is the FULL conversation so far:
{history_text}

Previously extracted information:
- Intent/Service: {prev_intent}
- City: {prev_city}
- Town/Area: {prev_town}

Your task:
1. Look at the ENTIRE conversation history (not just the last message).
2. Extract or UPDATE the following fields based on ALL messages combined:
   - intent: The service needed (e.g., "AC Repair", "AC Technician", "Plumber"). If previously known and user hasn't changed it, keep the old value.
   - city: The city name. If previously known and user hasn't changed it, keep the old value.
   - town: The town/area/neighborhood. If previously known and user hasn't changed it, keep the old value.
3. If a field was previously "Not yet known" but the user has now provided it in their latest message, extract it.
4. If a field was already known and the user provides a new value, update it.

Respond in STRICT JSON format only, no extra text:
{{
    "intent": "string or null",
    "city": "string or null",
    "town": "string or null"
}}"""

    response = llm.invoke([HumanMessage(content=prompt)])
    
    # Parse JSON from LLM response
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        parsed_data = json.loads(content)
        
        # Merge: keep old values if LLM returns null for something we already had
        new_intent = parsed_data.get("intent") or state.get("extracted_intent")
        new_city = parsed_data.get("city") or state.get("extracted_city")
        new_town = parsed_data.get("town") or state.get("extracted_town")
        
        if not new_intent or not new_city or not new_town:
            # Figure out what's missing and ask specifically
            missing = []
            if not new_intent:
                missing.append("service (e.g., AC Repair, Plumber)")
            if not new_city:
                missing.append("city")
            if not new_town:
                missing.append("town/area")
            
            clarification_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7)
            clarification_prompt = f"""The user wants a home service. We already know:
- Service: {new_intent or 'MISSING'}
- City: {new_city or 'MISSING'}  
- Town: {new_town or 'MISSING'}

The MISSING fields are: {', '.join(missing)}.

Ask the user ONLY for the missing information. Be friendly and speak in Roman Urdu.
Keep it short (1-2 sentences max). Do NOT ask for things we already know."""

            clarification_resp = clarification_llm.invoke([HumanMessage(content=clarification_prompt)])
            
            print(f"   ⚠️  Missing info: {', '.join(missing)}")
            print(f"   💬 Asking user for clarification...")
            return {
                **state,
                "extracted_intent": new_intent,
                "extracted_city": new_city,
                "extracted_town": new_town,
                "is_clarification_needed": True,
                "bot_response": clarification_resp.content.strip()
            }
        else:
            print(f"   ✅ Extracted → Service: {new_intent} | City: {new_city} | Town: {new_town}")
            return {
                **state,
                "extracted_intent": new_intent,
                "extracted_city": new_city,
                "extracted_town": new_town,
                "is_clarification_needed": False,
                "bot_response": None
            }
            
    except Exception as e:
        return {
            **state,
            "is_clarification_needed": True,
            "bot_response": "Mujhy samajh nahi aayi, kya aap detail dobara bata sakte hain? (Kis shehar aur ilaqay mein kya service chaiye?)"
        }

def google_maps_node(state: AgentState) -> AgentState:
    """Agent 2: Uses Google Maps API to fetch nearest businesses."""
    intent = state["extracted_intent"]
    town = state["extracted_town"]
    city = state["extracted_city"]
    
    print(f"\n🗺️  [Agent 2] Searching Google Maps for '{intent}' in {town}, {city}...")
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        print("WARNING: GOOGLE_MAPS_API_KEY not found in environment. Simulating Maps Response to save credits.")
        # Simulation for testing without burning real credits if key is missing
        return {
            **state,
            "raw_businesses": [
                {"displayName": {"text": f"Simulated {intent} Expert 1"}, "rating": 4.8, "formattedAddress": f"Main Market {town}, {city}", "nationalPhoneNumber": "03001234567"},
                {"displayName": {"text": f"Simulated {intent} Pro 2"}, "rating": 4.2, "formattedAddress": f"Street 2, {town}, {city}", "nationalPhoneNumber": "03211234567"}
            ]
        }
        
    # Cost Saving: Places API (New) with Field Masking
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.rating,places.formattedAddress,places.nationalPhoneNumber"
    }
    payload = {
        "textQuery": f"{intent} in {town}, {city}",
        "pageSize": 20
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        places = response.json().get("places", [])
        print(f"   📍 Found {len(places)} businesses nearby.")
        return {**state, "raw_businesses": places}
    except Exception as e:
        print(f"   ❌ Error fetching Maps data: {str(e)}")
        return {**state, "raw_businesses": []}

def ranking_node(state: AgentState) -> AgentState:
    """Agent 3: Uses Groq (Llama 3) to rank and format the output."""
    businesses = state["raw_businesses"]
    
    print(f"\n🏆 [Agent 3] Ranking top technicians from {len(businesses)} results...")
    
    if not businesses:
        print("   ❌ No businesses found to rank.")
        return {
            **state,
            "final_ranked_response": "Maaf karna, us ilaqay mein koi service providers nahi milay."
        }
    
    # Using LLaMA 3.3 70B via Groq (llama3-8b-8192 was decommissioned)
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0) 
    
    prompt = f"""
    You have a list of businesses fetched for a user looking for {state['extracted_intent']} in {state['extracted_town']}, {state['extracted_city']}.
    Rank the top 10 based on rating, and present them in a nicely formatted list in Roman Urdu.
    
    List of businesses (JSON):
    {json.dumps(businesses, indent=2)}
    
    Output format requirements:
    - Start with a polite greeting in Roman Urdu (e.g., "Yeh lijiye, aapke ilaqay ke behtareen options:").
    - Provide the Top 10 list.
    - Each entry must show: Business Name, Location/Address, Rating, and Phone Number.
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    
    print("   ✅ Top 10 ranked and formatted. Delivering results!\n")
    return {
        **state,
        "final_ranked_response": response.content.strip()
    }

# ==========================================
# 3. Routing and Graph Compilation
# ==========================================

def should_continue(state: AgentState):
    if state["is_clarification_needed"]:
        return "end"
    return "continue"

# Initialize graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("intent_parser", intent_parsing_node)
workflow.add_node("google_maps", google_maps_node)
workflow.add_node("ranking", ranking_node)

# Add edges
workflow.set_entry_point("intent_parser")

workflow.add_conditional_edges(
    "intent_parser",
    should_continue,
    {
        "end": END,
        "continue": "google_maps"
    }
)

workflow.add_edge("google_maps", "ranking")
workflow.add_edge("ranking", END)

# Compile graph
graph = workflow.compile()

# ==========================================
# 4. Interactive Usage with Multi-Turn Memory
# ==========================================
if __name__ == "__main__":
    print("=" * 50)
    print("  Welcome to YourCoolingPartner!")
    print("  Aapki cooling needs ka partner.")
    print("  Type 'quit' to exit.")
    print("=" * 50 + "\n")
    
    # Persistent state across turns
    conversation_history = []
    extracted_intent = None
    extracted_city = None
    extracted_town = None
    
    while True:
        try:
            user_text = input("You: ").strip()
            if not user_text:
                continue
            if user_text.lower() in ["quit", "exit"]:
                print("Shukriya! Allah Hafiz!")
                break
            
            # Add user message to conversation history
            conversation_history.append({"role": "user", "content": user_text})
            
            # Build state with accumulated info from previous turns
            current_state = {
                "user_input": user_text,
                "conversation_history": conversation_history.copy(),
                "extracted_intent": extracted_intent,
                "extracted_city": extracted_city,
                "extracted_town": extracted_town,
                "is_clarification_needed": False,
                "bot_response": None,
                "raw_businesses": [],
                "final_ranked_response": None
            }
            
            # Run the graph
            result = graph.invoke(current_state)
            
            if result.get("is_clarification_needed"):
                bot_msg = result.get("bot_response", "")
                print(f"Bot: {bot_msg}\n")
                
                # Save bot response to history
                conversation_history.append({"role": "bot", "content": bot_msg})
                
                # Accumulate extracted fields for next turn
                extracted_intent = result.get("extracted_intent") or extracted_intent
                extracted_city = result.get("extracted_city") or extracted_city
                extracted_town = result.get("extracted_town") or extracted_town
            else:
                final_output = result.get("final_ranked_response", "Koi natija nahi mila.")
                print(f"\nBot:\n{final_output}\n")
                
                # Reset state for a fresh query
                conversation_history = []
                extracted_intent = None
                extracted_city = None
                extracted_town = None
                
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

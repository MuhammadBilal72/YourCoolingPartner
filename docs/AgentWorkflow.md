# YourCoolingPartner: LangGraph Agentic Flow Implementation Plan

This document outlines the architecture and implementation plan for the **YourCoolingPartner** multi-agent system using LangGraph.

## User Review Required

> [!IMPORTANT]
> - **API Costs**: You mentioned having $5 in Google Maps API credits. We will use the **Places API (New)** with field masking. By only requesting specific fields (Name, Rating, Location, Phone Number), we minimize the cost per request and prevent excess billing.
> - **Groq vs. Ollama**: You mentioned "Groq with OLLAMA". Groq hosts LLaMA models in the cloud, while Ollama runs them locally on your machine. I plan to use **Groq's Cloud API with the Llama 3 model** for ranking, as it is blazing fast and requires no local setup. Let me know if you strictly want to run Ollama locally instead!

## Open Questions

> [!WARNING]
> 1. Should the system maintain conversation history for multiple turns (e.g., user asks for AC, then later asks for Plumber in the same chat)? Or is it a stateless 1-shot interaction?
> 2. What language framework are you using? (Python is assumed since it's standard for LangGraph).

## Proposed Architecture

We will build a stateful LangGraph application with three primary agent nodes.

### 1. State Definition (`AgentState`)
A shared dictionary that gets passed between the nodes.
- `user_input`: The raw message from the user.
- `conversation_history`: List of past messages for context.
- `extracted_intent`: The service requested (e.g., "AC Repair").
- `extracted_city`: The city name.
- `extracted_town`: The town/neighborhood.
- `is_clarification_needed`: Boolean flag.
- `bot_response`: The message to send back to the user (e.g., asking for missing info).
- `raw_businesses`: List of 20 businesses fetched from Maps.
- `final_ranked_response`: The formatted top 10 list for the user.

### 2. LangGraph Nodes (Agents)

#### Agent 1: Intent & Parsing Agent (Gemini 2.5 Flash)
- **Role**: Reads `user_input` and extracts `intent`, `city`, and `town`.
- **Validation**: Checks if the intent makes sense and if the city/town are provided and valid. 
- **Logic**:
  - If `city` or `town` is missing, sets `is_clarification_needed = True` and uses Gemini to generate a natural Roman Urdu reprompt (e.g., "Aapko kis shehar aur ilaqay mein AC repair chaiye?").
  - If complete, routes to Agent 2.

#### Agent 2: Google Maps Search Agent (Python Function + Places API)
- **Role**: Uses the `extracted_intent`, `extracted_town`, and `extracted_city` to query the Google Maps API.
- **Cost Saving Measure**: We will use the Google Places API (New) with a Text Search query: `"{intent} in {town}, {city}"`. We will strictly use the `fields` parameter to request ONLY `places.displayName,places.rating,places.formattedAddress,places.nationalPhoneNumber` to ensure minimal billing.
- **Logic**: Fetches up to 20 results and saves them to `raw_businesses` state. Routes to Agent 3.

#### Agent 3: Ranking & Formatting Agent (Groq + Llama 3)
- **Role**: Takes the `raw_businesses` JSON and evaluates them.
- **Logic**: Prompts Llama 3 via Groq to:
  1. Filter out completely irrelevant results.
  2. Rank the remaining based on the highest `rating`.
  3. Keep only the Top 10.
  4. Format the final output cleanly in Roman Urdu/English, presenting: Business Name, Location, Rating, and Mobile Number.
- Saves the final text to `final_ranked_response`.

### 3. Graph Routing Logic
- **Start** -> `Agent 1`
- **Conditional Edge (After Agent 1)**: 
  - If `is_clarification_needed == True` -> **End** (Return bot message to user)
  - If `is_clarification_needed == False` -> `Agent 2`
- `Agent 2` -> `Agent 3`
- `Agent 3` -> **End** (Return Top 10 list)

## Verification Plan

### Automated/Manual Tests
- **Parsing Test**: Send inputs like "Mujhy AC Wala Chaiye G1 Market Lahore ma" and verify state populated correctly without reprompts.
- **Reprompt Test**: Send "Mujhy Plumber chaiye" and verify the system asks for location.
- **API Cost Verification**: Run a dry-run of the Google Maps API payload and verify the `FieldMask` header is correctly applied to prevent excess billing.
- **Ranking Test**: Check if the Groq LLM correctly formats the Top 10 list.

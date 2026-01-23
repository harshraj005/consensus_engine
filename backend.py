import requests
import json
import re
from duckduckgo_search import DDGS

# --- CONFIGURATION ---
OLLAMA_API = "http://localhost:11434/api/generate"

# The Parliament Roster (Model Specialization)
MPS = {
    "researcher": {
        "model": "llama3.1:8b",
        "name": "🕵️ MP Llama (Intelligence Officer)",
        "role": "You are the Intelligence Officer. Your job is to read raw search data and compile a dense, factual briefing. Ignore pop culture references if the user asks a serious technical or ethical question.",
        "temp": 0.2  # Low temp for factual accuracy
    },
    "strategist": {
        "model": "deepseek-r1:14b",
        "name": "🧠 MP DeepSeek (The Strategist)",
        "role": "You are the Strategist. You use deep Chain-of-Thought reasoning to solve complex problems. CRITICAL: Think and Answer in ENGLISH ONLY.",
        "temp": 0.0  # Zero temp for pure logic/math
    },
    "analyst": {
        "model": "gemma2:9b",
        "name": "📐 MP Gemma (The Analyst)",
        "role": "You are the Logic Checker. Critically analyze the Strategist's plan for logical fallacies or errors. Keep the debate in ENGLISH.",
        "temp": 0.2
    },
    "skeptic": {
        "model": "mistral",
        "name": "🛡️ MP Mistral (The Skeptic)",
        "role": "You are the Devil's Advocate. Look for security risks, edge cases, and safety concerns. Be creative in finding flaws.",
        "temp": 0.6  # Higher temp for creative risk finding
    },
    "speaker": {
        "model": "neural-chat",
        "name": "📢 Mr. Speaker",
        "role": "You are the Speaker. Synthesize the entire debate into one final, clear, polite answer. If previous agents used technical jargon, simplify it for the user.",
        "temp": 0.5
    }
}

# --- CORE UTILITIES ---

def unload_model(model_name):
    """The Kill Switch: Forces RAM flush to prevent crashes."""
    try:
        requests.post(OLLAMA_API, json={"model": model_name, "keep_alive": 0})
    except Exception as e:
        print(f"[System] Warning: Could not unload {model_name}: {e}")

def generate_response(agent_key, prompt, context="", stream_handler=None):
    """
    Generic function to call any MP with specific Temperature and Context settings.
    """
    agent = MPS[agent_key]
    
    # Special instructions for DeepSeek to show thoughts
    if agent_key == "strategist":
        prompt += " (Show your thinking process inside <think> tags)"

    full_prompt = f"""
    SYSTEM ROLE: {agent['role']}
    
    === CONTEXT/PREVIOUS FINDINGS ===
    {context}
    =================================
    
    YOUR TASK: {prompt}
    """
    
    # Configure parameters based on the agent's specialization
    options = {
        "num_ctx": 8192 if agent_key == "strategist" else 4096,
        "temperature": agent.get("temp", 0.7)
    }
    
    payload = {
        "model": agent['model'],
        "prompt": full_prompt,
        "stream": True,
        "options": options
    }

    response_text = ""
    
    try:
        with requests.post(OLLAMA_API, json=payload, stream=True) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    try:
                        body = json.loads(line.decode('utf-8'))
                        if "response" in body:
                            chunk = body["response"]
                            response_text += chunk
                            if stream_handler:
                                stream_handler(chunk)
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        return f"[Error] Model generation failed: {str(e)}"
    
    # CRITICAL: Unload model immediately after use to save 16GB RAM
    unload_model(agent['model'])
    return response_text

# --- INTELLIGENCE MODULES ---

def smart_search(query):
    """
    Fetches 8 sources. Includes a Fallback Mechanism to prevent 'No results found'.
    """
    print(f"[Backend] Smart Search initiated for: {query}")
    
    try:
        # ATTEMPT 1: Ask Llama for a "Smart" Keyword
        refine_prompt = f"Convert this user query into a simple DuckDuckGo search keyword. Query: '{query}'. Output ONLY the keywords. Do not explain."
        # We do a quick call. Note: Ensure generate_response is imported or available
        refined_query = generate_response("researcher", refine_prompt).strip()
        
        # Cleanup: Remove quotes or prefixes Llama might add
        refined_query = refined_query.replace('"', '').replace("Search query:", "").strip()
        
        print(f"[Backend] Trying Refined Query: '{refined_query}'")
        results = DDGS().text(refined_query, max_results=8)
        
        # ATTEMPT 2: Fallback (If Llama failed us)
        if not results:
            print(f"[Backend] Smart search yielded 0 results. Retrying with RAW query: '{query}'")
            results = DDGS().text(query, max_results=8)
            
        # Final Check
        if not results:
            return "System Alert: The search engine returned no data. The internet connection might be unstable or the query is too obscure."
            
        # Format the data
        return "\n".join([f"Source {i+1}: {r['title']} - {r['body']}" for i, r in enumerate(results)])

    except Exception as e:
        print(f"[Backend] Critical Error: {e}")
        return f"Error fetching data: {str(e)}"

def generate_briefing(raw_data):
    """
    Uses Llama to compress raw search data into a high-density briefing.
    """
    prompt = "You are an Intelligence Officer. Read these search results. Construct a SINGLE comprehensive briefing note that captures key facts, conflicting viewpoints, and technical details. Ignore irrelevant results."
    return generate_response("researcher", prompt, context=raw_data)

def determine_protocol(user_query):
    # ... previous code ...
    prompt = f"""
    Analyze this user query: "{user_query}"
    
    Determine the complexity. Return ONLY one JSON object:
    
    {{"level": 1, "mode": "CHAT"}} -> For greetings, "Who are you?", identity questions, simple jokes.
    {{"level": 2, "mode": "RESEARCH"}} -> For specific facts, news, "Who is X?", "Price of Y".
    {{"level": 3, "mode": "DEEP_DIVE"}} -> For complex coding, ethical dilemmas, analysis.
    
    Return ONLY the JSON.
    """
    
    # We use Mistral (Skeptic) for routing as it is fast and follows instructions well
    response = generate_response("skeptic", prompt)
    
    # Robust JSON parsing (in case the model adds extra text)
    try:
        # regex to find the json part
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
        else:
            raise ValueError("No JSON found")
    except:
        # Default to Level 3 (Safe Mode) if parsing fails
        print("[Backend] Router failed to parse JSON, defaulting to Deep Dive.")
        return {"level": 3, "mode": "DEEP_DIVE"}
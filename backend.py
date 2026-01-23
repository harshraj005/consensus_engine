import requests
import json
import re
import time
import random
from duckduckgo_search import DDGS

# --- CONFIGURATION ---
OLLAMA_API = "http://localhost:11434/api/generate"

# The Parliament Roster (Model Specialization)
MPS = {
    "researcher": {
        "model": "llama3.1:8b",
        "name": "🕵️ MP Llama (Intelligence Officer)",
        "role": "You are the Intelligence Officer. Your job is to read raw search data and compile a dense, factual briefing. Ignore pop culture references if the user asks a serious technical or ethical question.",
        "temp": 0.2
    },
    "strategist": {
        "model": "deepseek-r1:14b",
        "name": "🧠 MP DeepSeek (The Strategist)",
        "role": "You are the Strategist. You use deep Chain-of-Thought reasoning to solve complex problems. CRITICAL: Think and Answer in ENGLISH ONLY.",
        "temp": 0.0
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
        "temp": 0.6
    },
    "speaker": {
        "model": "neural-chat",
        "name": "📢 Mr. Speaker",
        # RULE: Force code inclusion and simple synthesis
        "role": "You are the Speaker. Your job is to deliver the FINAL ANSWER to the user. \n"
                "RULES:\n"
                "1. If the user asked for CODE/SCRIPT, you MUST copy-paste the Strategist's code into your answer.\n"
                "2. If the user asked for a FACT (e.g. Price), do NOT output code. Just state the answer.\n"
                "3. Synthesize the critiques, but do not delete the solution.",
        "temp": 0.3
    }
}

# --- CORE UTILITIES ---

def unload_model(model_name):
    """The Kill Switch: Forces RAM flush."""
    try:
        requests.post(OLLAMA_API, json={"model": model_name, "keep_alive": 0})
    except:
        pass

def generate_response(agent_key, prompt, context="", stream_handler=None):
    agent = MPS[agent_key]
    
    if agent_key == "strategist":
        prompt += " (Show your thinking process inside <think> tags)"

    full_prompt = f"""
    SYSTEM ROLE: {agent['role']}
    
    === CONTEXT/PREVIOUS FINDINGS ===
    {context}
    =================================
    
    YOUR TASK: {prompt}
    """
    
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
                    except:
                        continue
    except Exception as e:
        return f"[Error] Model generation failed: {str(e)}"
    
    unload_model(agent['model'])
    return response_text

# --- INTELLIGENCE MODULES (THE PATCHED SEARCH) ---

def smart_search(query):
    """
    The DuckDuckGo Patch:
    1. Force 'current' context for prices/news.
    2. Retry loop with delays to bypass Rate Limits (403/202).
    3. Fallback to simple query if complex one fails.
    """
    print(f"[Backend] DuckDuckGo Search for: {query}")
    
    # 1. Context Injection
    # If the user asks for price/news, we force the engine to look at 2025/2026 data
    if any(k in query.lower() for k in ["price", "current", "news", "latest", "today", "cost"]):
        search_query = f"{query} current data 2026"
    else:
        search_query = query

    results = []
    
    # 2. The Retry Loop (Attempts to bypass bot detection)
    # We try 3 times. If it fails, we wait a random amount of seconds.
    for attempt in range(3):
        try:
            # Re-initializing DDGS() every time helps reset the session
            ddgs = DDGS()
            # Fetch results
            results = list(ddgs.text(search_query, max_results=6))
            
            if results:
                break # We got data! Exit loop.
            else:
                # If valid but empty, try the Fallback (Simple Query)
                print(f"[Backend] Attempt {attempt+1} empty. Trying fallback...")
                simple_query = "".join(e for e in query if e.isalnum() or e.isspace())
                results = list(ddgs.text(simple_query, max_results=6))
                if results: break
                
        except Exception as e:
            print(f"[Backend] Search Attempt {attempt+1} failed: {e}")
            time.sleep(random.uniform(1.5, 3.0)) # Random delay helps look like a human
    
    if not results:
        return "SEARCH ERROR: DuckDuckGo is blocking requests. Please wait 10 seconds and try again."

    # Format for the Researcher
    return "\n".join([f"Source {i+1}: {r['title']} - {r['body']}" for i, r in enumerate(results)])

def generate_briefing(raw_data):
    prompt = "You are an Intelligence Officer. Read these search results. Construct a SINGLE comprehensive briefing note. Ignore pop culture."
    return generate_response("researcher", prompt, context=raw_data)

def determine_protocol(user_query):
    """
    Router using Llama for better JSON compliance.
    """
    prompt = f"""
    Analyze the user query: "{user_query}"
    
    Classify it into one of these levels. Return ONLY the JSON object.
    
    {{"level": 1, "mode": "CHAT"}} -> Greetings, "Who are you?", "What is your name?", simple jokes.
    {{"level": 2, "mode": "RESEARCH"}} -> "Price of Bitcoin", "Who is CEO of X?", specific facts, news.
    {{"level": 3, "mode": "DEEP_DIVE"}} -> Coding tasks, "Write a script", "Analyze this", complex problems.
    
    JSON:
    """
    response = generate_response("researcher", prompt)
    
    try:
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        else:
            # Fallback logic
            lower_q = user_query.lower()
            if any(x in lower_q for x in ["who are you", "hi", "hello", "name"]):
                return {"level": 1, "mode": "CHAT"}
            return {"level": 3, "mode": "DEEP_DIVE"}
    except:
        return {"level": 3, "mode": "DEEP_DIVE"}
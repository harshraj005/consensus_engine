import streamlit as st
import backend
import time

st.set_page_config(page_title="Consensus Engine", page_icon="🏛️", layout="wide")

# CSS for better visibility
st.markdown("""
<style>
    .stChatMessage { background-color: #1E1E1E; border: 1px solid #333; }
    div[data-testid="stExpander"] { border: 1px solid #333; }
</style>
""", unsafe_allow_html=True)

class StreamHandler:
    def __init__(self, placeholder):
        self.placeholder = placeholder
        self.text = ""
    def update(self, chunk):
        self.text += chunk
        self.placeholder.markdown(self.text + "▌")
    def finish(self):
        self.placeholder.markdown(self.text)

if "messages" not in st.session_state: st.session_state.messages = []
if "transcript" not in st.session_state: st.session_state.transcript = ""

# --- MAIN LOOP ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Propose a motion..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. MEMORY WIPE (Fixes the AM/PM bug)
    st.session_state.transcript = f"--- NEW MOTION: {prompt} ---\n"

    # 2. ROUTING
    with st.status("🚦 **Router Analyzing...**", expanded=True) as status:
        protocol = backend.determine_protocol(prompt)
        level = protocol.get("level", 3)
        mode = protocol.get("mode", "DEEP_DIVE")
        st.write(f"**Decision:** {mode}")
        status.update(label=f"Protocol: {mode}", state="complete", expanded=False)

    # --- LEVEL 1: CHAT ---
    if level == 1:
        with st.chat_message("assistant"):
            ph = st.empty()
            handler = StreamHandler(ph)
            # Identity Injection
            sys_prompt = f"User said: '{prompt}'. You are the Parliament Speaker. Introduce yourself and your agents (DeepSeek, Llama, Mistral)."
            backend.generate_response("speaker", sys_prompt, stream_handler=handler.update)
            handler.finish()

    # --- LEVEL 2: RESEARCH ---
    elif level == 2:
        with st.status("🕵️ **Researching...**", expanded=True):
            raw = backend.smart_search(prompt)
            briefing = backend.generate_briefing(raw)
            with st.expander("View Briefing"): st.markdown(briefing)
        
        with st.chat_message("assistant"):
            ph = st.empty()
            handler = StreamHandler(ph)
            backend.generate_response("speaker", f"Answer this using the briefing: {briefing}. Query: {prompt}", stream_handler=handler.update)
            handler.finish()

    # --- LEVEL 3: DEEP DIVE (THE CODE FIX) ---
    elif level == 3:
        with st.status("🏛️ **Parliament Session (Iterative Mode)**", expanded=True) as status:
            
            # Step A: Initial Strategy
            st.write("🧠 **Step 1:** Strategist (DeepSeek) Drafting...")
            transcript = st.session_state.transcript
            
            # We don't show the first draft to save UI space, but we save it
            draft = backend.generate_response("strategist", f"Solve: {prompt}", context=transcript)
            transcript += f"Strategist Draft 1: {draft}\n"
            
            # Step B: Critiques
            st.write("⚔️ **Step 2:** Critics Reviewing...")
            critique = backend.generate_response("analyst", "Critique this draft. Find bugs or security risks.", context=transcript)
            transcript += f"Critiques: {critique}\n"
            with st.expander("View Critiques"): st.markdown(critique)

            # Step C: REFINEMENT (The User Request)
            st.write("🔧 **Step 3:** Strategist Fixing Issues...")
            with st.expander("View Fixed Code Logic"):
                ph = st.empty()
                handler = StreamHandler(ph)
                # We ask DeepSeek to fix its own code based on critiques
                final_solution = backend.generate_response(
                    "strategist", 
                    "Review the critiques. Rewrite your solution/code to fix all issues. Output the final correct code.", 
                    context=transcript,
                    stream_handler=handler.update
                )
                handler.finish()
            
            transcript += f"Strategist Final Fix: {final_solution}\n"
            status.update(label="Session Adjourned", state="complete", expanded=False)

        # Step D: Final Output
        with st.chat_message("assistant"):
            st.write("📢 **Official Consensus:**")
            ph = st.empty()
            handler = StreamHandler(ph)
            # Speaker just formats the Final Fix
            backend.generate_response(
                "speaker", 
                "Present the Final Fix from the Strategist. Ensure the CODE BLOCK is included.", 
                context=transcript,
                stream_handler=handler.update
            )
            handler.finish()
import streamlit as st
import backend
import time
import json

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Consensus Engine",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a professional "Dark Mode" Parliament feel
st.markdown("""
<style>
    .stChatMessage {
        background-color: #1E1E1E;
        border: 1px solid #333;
        border-radius: 10px;
    }
    .stStatus {
        border: 1px solid #444;
        background-color: #0E1117;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #333;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONTROL ---
with st.sidebar:
    st.title("🏛️ Consensus Engine")
    st.caption("Local Multi-Agent Parliament")
    st.markdown("---")
    
    # System Monitor
    st.subheader("System Status")
    st.success("✅ Ollama Engine: Active")
    st.info("🧠 16GB RAM Optimized Mode")
    
    st.markdown("---")
    
    # Session Management
    if st.button("🗑️ Clear Session"):
        st.session_state.messages = []
        st.session_state.transcript = ""
        st.rerun()
        
    # Download Transcript
    if "transcript" in st.session_state and len(st.session_state.transcript) > 0:
        st.download_button(
            label="💾 Save Minutes of Meeting",
            data=st.session_state.transcript,
            file_name=f"debate_transcript_{int(time.time())}.txt",
            mime="text/plain"
        )

# --- STATE INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "transcript" not in st.session_state:
    st.session_state.transcript = ""

# --- HELPER CLASS FOR STREAMING ---
class StreamHandler:
    """
    Handles real-time text streaming to the UI.
    Prevents syntax errors by keeping state isolated.
    """
    def __init__(self, placeholder, label=""):
        self.placeholder = placeholder
        self.label = label
        self.full_text = ""
        self.start_time = time.time()

    def update(self, chunk):
        self.full_text += chunk
        # If label is provided, show it (e.g., "**Speaker:** Hello...")
        if self.label:
            self.placeholder.markdown(f"**{self.label}:** {self.full_text}▌")
        else:
            self.placeholder.markdown(self.full_text + "▌")

    def finish(self):
        # Remove the cursor ▌
        if self.label:
            self.placeholder.markdown(f"**{self.label}:** {self.full_text}")
        else:
            self.placeholder.markdown(self.full_text)
        return self.full_text

# --- MAIN CHAT INTERFACE ---

st.title("The Parliament")
st.caption("Dynamic Protocol: Chat (Level 1) | Research (Level 2) | Deep Debate (Level 3)")

# 1. Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 2. Handle User Input
if prompt := st.chat_input("Propose a motion (or ask a question)..."):
    
    # Add User Message to History
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Initialize Transcript for this turn
    st.session_state.transcript = f"--- NEW MOTION: {prompt} ---\n"

    # --- PHASE 1: ROUTING (THE SWITCHBOARD) ---
    with st.status("🚦 **The Router is analyzing your request...**", expanded=True) as status:
        protocol = backend.determine_protocol(prompt)
        level = protocol.get("level", 3) # Default to 3 if fail
        mode = protocol.get("mode", "DEEP_DIVE")
        
        st.write(f"**Decision:** Protocol Level {level} ({mode}) selected.")
        status.update(label=f"Protocol Active: {mode}", state="complete", expanded=True)

    # --- PHASE 2: EXECUTION ---
    
    # >>> LEVEL 1: SIMPLE CHAT <<<
    if level == 1:
        with st.chat_message("assistant"):
            st.write("📢 **Speaker:**")
            ph = st.empty()
            handler = StreamHandler(ph)
            
            # Direct call to Speaker (Fast)
            final_response = backend.generate_response(
                "speaker", 
                prompt, 
                stream_handler=handler.update
            )
            handler.finish()
            
            st.session_state.messages.append({"role": "assistant", "content": final_response})
            st.session_state.transcript += f"Speaker: {final_response}\n"

    # >>> LEVEL 2: RESEARCH & FACT CHECK <<<
    elif level == 2:
        with st.status("🕵️ **Intelligence Gathering in Progress...**", expanded=True) as status:
            # 1. Smart Search
            st.write("🌍 Connecting to DuckDuckGo (Broad Context)...")
            raw_data = backend.smart_search(prompt)
            st.session_state.transcript += f"Raw Data: {raw_data[:200]}...\n"
            
            # 2. Researcher Summarizes
            st.write("📝 MP Llama is compiling the briefing...")
            briefing = backend.generate_briefing(raw_data)
            st.session_state.transcript += f"Briefing: {briefing}\n"
            
            # Show the Briefing in an expander
            with st.expander("View Intelligence Briefing", expanded=False):
                st.markdown(briefing)
                
            status.update(label="Intelligence Gathered", state="complete", expanded=False)

        # 3. Speaker Delivers
        with st.chat_message("assistant"):
            st.write("📢 **Speaker:**")
            ph = st.empty()
            handler = StreamHandler(ph)
            
            final_response = backend.generate_response(
                "speaker", 
                f"Answer the user query based ONLY on this briefing: {briefing}. Query: {prompt}", 
                stream_handler=handler.update
            )
            handler.finish()
            st.session_state.messages.append({"role": "assistant", "content": final_response})

    # >>> LEVEL 3: THE FULL PARLIAMENT (DEEP DIVE) <<<
    elif level == 3:
        # Container to hold the debate steps visually
        with st.status("🏛️ **Parliament in Session**", expanded=True) as status:
            
            # A. Research
            st.write("🌍 **Step 1:** Gathering Evidence...")
            raw_data = backend.smart_search(prompt)
            briefing = backend.generate_briefing(raw_data)
            st.session_state.transcript += f"Briefing: {briefing}\n"
            with st.expander("📄 Evidence Briefing"):
                st.markdown(briefing)

            # B. Strategy (DeepSeek)
            st.write("🧠 **Step 2:** The Strategist (DeepSeek) is thinking...")
            
            # We create a special container for DeepSeek's "Thought Process"
            thought_expander = st.expander("💭 View DeepSeek's Chain-of-Thought", expanded=True)
            with thought_expander:
                ph_thought = st.empty()
                handler_thought = StreamHandler(ph_thought)
                
                # We ask DeepSeek to solve it
                # Note: The <think> tags usually come naturally from R1, or we prompt for them.
                strategy = backend.generate_response(
                    "strategist", 
                    f"Solve this problem based on the briefing: {prompt}", 
                    context=st.session_state.transcript,
                    stream_handler=handler_thought.update
                )
                handler_thought.finish()
            
            st.session_state.transcript += f"Strategist: {strategy}\n"

            # C. Critique (Analyst & Skeptic)
            st.write("⚔️ **Step 3:** The Critics are reviewing...")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**MP Gemma (Logic):**")
                ph_gemma = st.empty()
                h_gemma = StreamHandler(ph_gemma)
                critique_1 = backend.generate_response(
                    "analyst", 
                    "Find logical holes in the Strategist's plan.", 
                    context=st.session_state.transcript,
                    stream_handler=h_gemma.update
                )
                h_gemma.finish()
            
            with col2:
                st.write("**MP Mistral (Security):**")
                ph_mistral = st.empty()
                h_mistral = StreamHandler(ph_mistral)
                critique_2 = backend.generate_response(
                    "skeptic", 
                    "Find security risks or safety concerns.", 
                    context=st.session_state.transcript,
                    stream_handler=h_mistral.update
                )
                h_mistral.finish()
                
            st.session_state.transcript += f"Analyst: {critique_1}\nSkeptic: {critique_2}\n"
            
            status.update(label="Debate Concluded. Speaker is drafting verdict.", state="complete", expanded=False)

        # D. Final Consensus
        with st.chat_message("assistant"):
            st.write("📢 **Official Consensus:**")
            ph = st.empty()
            handler = StreamHandler(ph)
            
            final_response = backend.generate_response(
                "speaker", 
                "Synthesize the debate into a final, comprehensive answer.", 
                context=st.session_state.transcript,
                stream_handler=handler.update
            )
            handler.finish()
            st.session_state.messages.append({"role": "assistant", "content": final_response})
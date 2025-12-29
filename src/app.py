import sys
import os

# Add the project root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import json
import threading
from src import brain, database, watcher, scheduler

# Page Configuration
st.set_page_config(
    page_title="Shadow AI",
    page_icon="🧠",
    layout="wide"
)

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

if "active_sources" not in st.session_state:
    st.session_state.active_sources = set()

if "watcher_running" not in st.session_state:
    # Start the folder watcher in a background thread
    try:
        watcher.start_background_watcher()
        st.session_state.watcher_running = True
        print("[App] Background watcher started.")
    except Exception as e:
        st.error(f"Failed to start watcher: {e}")

if "scheduler_running" not in st.session_state:
    # Start the scheduler
    try:
        scheduler.start_scheduler()
        st.session_state.scheduler_running = True
        print("[App] Scheduler started.")
    except Exception as e:
        st.error(f"Failed to start scheduler: {e}")

def load_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except:
        return {}

config = load_config()

# --- Sidebar ---
with st.sidebar:
    st.header("Knowledge Dashboard")
    
    # Display Stats
    stats = database.get_stats()
    st.metric("Total Memories", stats.get("total_documents", 0))
    
    st.divider()
    
    st.subheader("Live Watchers")
    folders = config.get("watch_folders", [])
    if folders:
        for folder in folders:
            st.markdown(f"🟢 `{folder}`")
    else:
        st.warning("No folders configured in config.json")
    
    st.divider()
    
    st.subheader("System Health")
    if "context_health" in st.session_state and st.session_state.context_health:
        ch = st.session_state.context_health
        usage = f"{ch.get('tokens_used', 0)} / {ch.get('max_ctx', 0)}"
        st.metric("Context Utilization", usage)
    else:
        st.info("No recent context usage.")
    
    st.divider()
    
    # Clear Execution Logs Button
    if st.button("Clear Execution Logs"):
        try:
            open("shadow_execution.log", "w").close()
            st.success("Execution logs cleared!")
        except Exception as e:
            st.error(f"Failed to clear logs: {e}")
            
    st.divider()
    st.info("Shadow is running locally.")

# --- Main Interface ---
st.title("Shadow AI")
st.markdown("*Local-first AI with transparent context routing.*")

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Display Reasoning if available (for assistant messages)
        if message.get("routing_plan"):
            with st.expander("Shadow's Reasoning"):
                st.json(message["routing_plan"])
                if message.get("context_used"):
                    st.markdown("**Context Used:**")
                    st.text(message["context_used"])

# Chat Input
if prompt := st.chat_input("Ask Shadow something..."):
    # 1. Add user message to state and UI
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 2. Add user message to Recursive Memory
    database.add_chat_memory("user", prompt)

    # 3. Generate Response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        final_answer = ""
        final_trail = {}
        
        with st.status("Initializing Shadow...", expanded=True) as status:
            try:
                response_generator = brain.process_query_stream(prompt, config.get("watch_folders", []))
                
                for step_type, data in response_generator:
                    if step_type == "ingestion":
                        status.update(label="📥 Checking Ingestion...", state="running")
                    elif step_type == "routing":
                        status.update(label="🌐 Consulting Web...", state="running")
                    elif step_type == "storage":
                        status.update(label="📂 Accessing Storage...", state="running")
                        # Optional: Show what was found in the status body
                        # st.write(data) 
                    elif step_type == "summary_progress":
                        stage = data.get("stage")
                        seg = data.get("segment")
                        total = data.get("total")
                        if stage == "reading":
                            status.update(label=f"📖 Reading Segment {seg} of {total}...", state="running")
                        else:
                            status.update(label="🧾 Refining Executive Summary...", state="running")
                    elif step_type == "processing":
                        status.update(label="🧠 Processing Answer...", state="running")
                    elif step_type == "complete":
                        status.update(label="✅ Execution Complete!", state="complete", expanded=False)
                        final_answer, final_trail = data
                        
            except Exception as e:
                status.update(label="❌ Error", state="error")
                st.error(f"An error occurred: {e}")
                final_answer = "I encountered an error while processing your request."
        
        message_placeholder.markdown(final_answer)
        
        if final_trail:
            # Update Active Sources (using new structure)
            if "Stage 3: Processing" in final_trail:
                web_results = final_trail["Stage 3: Processing"].get("web_results", [])
                st.session_state.active_sources.update(web_results)
            
            if "Stage 4: Transparency" in final_trail:
                ch = final_trail["Stage 4: Transparency"].get("context_utilization")
                if ch:
                    st.session_state.context_health = ch
                
            with st.expander("🔍 Elaborate Execution Trail", expanded=False):
                # Display Structured Trail
                st.markdown("### 🧩 Execution Trail")
                st.json({k:v for k,v in final_trail.items() if k.startswith("Stage")})
                
                # Display Detailed Sources if available
                if "detailed_sources" in final_trail:
                    st.markdown("### 🌐 Sources & Context")
                    tabs = st.tabs(["Web", "Files", "Chat", "Raw Trail"])
                    
                    with tabs[0]: # Web
                        web_sources = [s for s in final_trail["detailed_sources"] if s["type"] == "web"]
                        if web_sources:
                            for src in web_sources:
                                st.markdown(f"**[{src['title']}]({src['url']})**")
                                st.caption(f"{src['snippet']}")
                                st.divider()
                        else:
                            st.info("No web sources used.")
                            
                    with tabs[1]: # Files
                        file_sources = [s for s in final_trail["detailed_sources"] if s["type"] == "file"]
                        if file_sources:
                            for src in file_sources:
                                st.markdown(f"**📄 {src['title']}** (`{src['path']}`)")
                                st.code(src['snippet'], language="text")
                        else:
                            st.info("No local files used.")

                    with tabs[2]: # Chat
                        chat_sources = [s for s in final_trail["detailed_sources"] if s["type"] == "chat"]
                        if chat_sources:
                            for src in chat_sources:
                                st.markdown(f"**💬 Role: {src['role']}**")
                                st.text(src['snippet'])
                        else:
                            st.info("No chat history used.")
                            
                    with tabs[3]: # Raw
                         st.json(final_trail)
                else:
                    st.json(final_trail)
        
        # Save to Recursive Memory
        if final_answer:
            database.add_chat_memory("assistant", final_answer)

        st.session_state.messages.append({
            "role": "assistant", 
            "content": final_answer,
            "trail": final_trail
        })

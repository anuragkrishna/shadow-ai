import sys
import os

# Add the project root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import json
import threading
from src import brain, database, watcher

# Page Configuration
st.set_page_config(
    page_title="Shadow AI",
    page_icon="🧠",
    layout="wide"
)

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

if "watcher_running" not in st.session_state:
    # Start the folder watcher in a background thread
    # We use a flag to prevent multiple watchers
    try:
        watcher.start_background_watcher()
        st.session_state.watcher_running = True
        print("[App] Background watcher started.")
    except Exception as e:
        st.error(f"Failed to start watcher: {e}")

def load_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except:
        return {}

config = load_config()

# --- Sidebar ---
with st.sidebar:
    st.header("Shadow System Stats")
    
    # Display Stats
    stats = database.get_stats()
    st.metric("Total Memories", stats.get("total_documents", 0))
    
    st.divider()
    
    st.subheader("Monitored Folders")
    folders = config.get("watch_folders", [])
    if folders:
        for folder in folders:
            st.code(folder, language="text")
    else:
        st.warning("No folders configured in config.json")
    
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
        reasoning_placeholder = st.empty()
        
        with st.spinner("Thinking..."):
            # A. Get Routing Plan
            routing_plan = brain.get_routing_plan(prompt)
            
            # Show preliminary reasoning
            with reasoning_placeholder.container():
                with st.expander("Shadow's Reasoning", expanded=True):
                    st.json(routing_plan)
            
            # B. Execute Plan (Retrieve Context)
            context = brain.execute_routing_plan(routing_plan)
            
            # C. Generate Answer
            full_response = brain.generate_answer(prompt, context)
            
            # Display Answer
            message_placeholder.markdown(full_response)
            
            # D. Save to Recursive Memory
            database.add_chat_memory("assistant", full_response)
            
            # E. Update State
            st.session_state.messages.append({
                "role": "assistant", 
                "content": full_response,
                "routing_plan": routing_plan,
                "context_used": context
            })

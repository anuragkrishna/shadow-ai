import json
import time
import datetime
import os
import warnings
from litellm import completion
from src import database, search_tool

# Suppress Pydantic warnings from litellm/internal libs
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

def load_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except:
        return {}

config = load_config()

# Configuration for the model
MODEL_NAME = config.get("llm_model", "ollama/llama3.2")

def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)

def _chunk_by_tokens(text: str, max_tokens: int = 3000) -> list:
    size = max_tokens * 4
    chunks = []
    i = 0
    while i < len(text):
        end = min(i + size, len(text))
        chunks.append(text[i:end])
        i = end
    return chunks

def _summarize_refine(chunks: list) -> tuple:
    summary = ""
    tokens_used = 0
    path = []
    for idx, chunk in enumerate(chunks, start=1):
        if idx == 1:
            sys_prompt = "You are a professional executive summarizer."
            user_prompt = "Summarize the following document segment in an executive tone."
            content = f"{user_prompt}\n\nSegment:\n{chunk}"
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": content}
            ]
        else:
            sys_prompt = "You are a professional executive summarizer."
            user_prompt = "Update this summary based on the new segment below. Maintain an executive tone."
            content = f"Current Summary:\n{summary}\n\nNew Segment:\n{chunk}\n\n{user_prompt}"
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": content}
            ]
        resp = completion(
            model=MODEL_NAME,
            messages=messages,
            api_base="http://localhost:11434",
            temperature=0.1,
            num_predict=1024,
            num_ctx=8192
        )
        summary = resp.choices[0].message.content
        t = _estimate_tokens(content) + _estimate_tokens(summary)
        tokens_used += t
        start_char = (idx - 1) * 3000 * 4
        end_char = start_char + len(chunk)
        path.append({"segment": idx, "start_char": start_char, "end_char": end_char, "tokens_estimate": _estimate_tokens(chunk)})
    return summary, tokens_used, path
def get_routing_plan(user_query: str):
    """
    Analyzes the user query using a local LLM to generate a routing plan.
    Returns a dictionary containing Intent, Reasoning, and Context Available.
    """
    
    system_prompt = """
    You are the "Semantic Router" for a local AI assistant named Shadow.
    Your goal is to analyze the user's request and decide how to process it.
    
    Output STRICTLY valid JSON with the following keys:
    - "intent": One of ["file_search", "web_search", "chat_memory", "general"].
    - "reasoning": A one-sentence explanation of why you chose this intent.
    - "keywords": A list of specific keywords to search for. optimized for a search engine.
    
    Definitions:
    - "file_search": When the user asks about local documents, notes, or specific files known to the system.
    - "web_search": When the user asks for factual information, current events, news, specific entities (people, places), or anything that might change over time.
    - "chat_memory": When the user refers to past conversations or things said previously.
    - "general": ONLY for greetings ("hi"), logic puzzles, or timeless general knowledge that DOES NOT require current data.
    
    Example 1: "Who is the president of USA?"
    Output:
    {
        "intent": "web_search",
        "reasoning": "This is a factual question about a specific entity that may change.",
        "keywords": ["current US President 2025", "who is president of USA now"]
    }

    Example 2: "What did we discuss about the project roadmap yesterday?"
    Output:
    {
        "intent": "chat_memory",
        "reasoning": "The user is referring to a past discussion.",
        "keywords": ["project roadmap", "yesterday"]
    }
    """
    
    try:
        response = completion(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            format="json", # Hint for JSON output if supported by the provider/proxy
            api_base="http://localhost:11434" # Default Ollama port
        )
        
        content = response.choices[0].message.content
        
        # Parse JSON
        try:
            plan = json.loads(content)
            return plan
        except json.JSONDecodeError:
            print(f"[Brain] Failed to parse JSON. Raw output: {content}")
            return {
                "intent": "general",
                "reasoning": "Model failed to output valid JSON, defaulting to general chat.",
                "keywords": []
            }
            
    except Exception as e:
        print(f"[Brain] Error generating routing plan: {e}")
        return {
            "intent": "general",
            "reasoning": f"Error connecting to local model: {e}",
            "keywords": []
        }

def execute_routing_plan(plan: dict, user_query: str):
    """
    Executes the routing plan by retrieving context from ALL sources (Files, Chats, Web).
    Returns a tuple: (context_string, execution_trail_data)
    """
    intent = plan.get("intent")
    keywords = plan.get("keywords", [])
    query_text = " ".join(keywords) if keywords else user_query
    
    context_parts = []
    
    # Trail Data Structure (Stage 2 & 3)
    storage_log = {
        "file_matches": [],
        "chat_matches": []
    }
    processing_log = {
        "intent": intent,
        "reasoning": plan.get("reasoning"),
        "keywords": keywords,
        "web_results": []
    }
    
    detailed_sources = [] # For the elaborate trail UI
    
    # 1. Local Files
    file_results = database.query_memory(query_text=query_text, n_results=3, filters={"source": "file"})
    if file_results and file_results['documents']:
        docs = file_results['documents'][0]
        metas = file_results['metadatas'][0]
        for doc, meta in zip(docs, metas):
            context_parts.append(f"File ({meta.get('filename')}): {doc}")
            
            # Log exact match
            storage_log["file_matches"].append({
                "filename": meta.get('filename'),
                "path": meta.get('path')
            })
            
            detailed_sources.append({
                "type": "file",
                "title": meta.get('filename'),
                "path": meta.get('path'),
                "snippet": doc[:100] + "..."
            })

    # 2. Chat History
    chat_results = database.query_memory(query_text=query_text, n_results=5, filters={"source": "chat_history"})
    if chat_results and chat_results['documents']:
        docs = chat_results['documents'][0]
        metas = chat_results['metadatas'][0]
        
        # Combine and sort by timestamp (Oldest -> Newest so latest is at bottom)
        combined_chats = []
        for doc, meta in zip(docs, metas):
            combined_chats.append({"doc": doc, "meta": meta})
            
        combined_chats.sort(key=lambda x: x["meta"].get("timestamp", ""))
        
        for item in combined_chats:
            doc = item["doc"]
            meta = item["meta"]
            context_parts.append(f"Past Chat ({meta.get('timestamp', 'unknown')}): {doc}")
            
            # Log exact match
            storage_log["chat_matches"].append({
                "role": meta.get('role'),
                "timestamp": meta.get('timestamp')
            })

            detailed_sources.append({
                "type": "chat",
                "role": meta.get('role'),
                "snippet": doc[:100] + "..."
            })

    # 3. Web Search
    web_text, web_source_list = search_tool.search_web(query_text)
    if web_text and "No web results found" not in web_text:
        context_parts.append(f"Web Search Results:\n{web_text}")
        
        # Log web results
        processing_log["web_results"] = [s.get("url") for s in web_source_list]
        
        # Add detailed web sources
        for src in web_source_list:
            detailed_sources.append({
                "type": "web",
                "title": src.get("title"),
                "url": src.get("url"),
                "snippet": src.get("snippet")
            })
    
    full_context = "\n\n".join(context_parts)
    
    trail_data = {
        "Stage 2: Storage": storage_log,
        "Stage 3: Processing": processing_log,
        "Stage 4: Transparency": {
            "grounding_context_preview": full_context[:500] + "..." if full_context else "None",
            "context_size_bytes": len(full_context)
        },
        "detailed_sources": detailed_sources 
    }
    
    return full_context, trail_data

def generate_answer(user_query: str, context: str, temperature: float = 0.7):
    """
    Generates the final answer using the retrieved context.
    """
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    system_prompt = f"""
    You are Shadow, a helpful local AI assistant.
    Today's Date: {current_date}
    
    Use the following context to answer the user's question.
    If the context is empty or irrelevant, use your general knowledge.
    
    IMPORTANT: 
    - You have access to real-time data from web search, local files, and chat history.
    - If context is provided, USE IT. Do NOT say "I have information until [Year]" if the context provides newer data.
    - Trust the Web Search Results over your internal training data for current events.
    - If there is a conflict between the user's implied date and the web results, trust the web results.
    
    CONTEXT:
    {context}
    """
    
    try:
        response = completion(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            api_base="http://localhost:11434",
            temperature=temperature
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating answer: {e}"

def process_query_stream(user_query: str, active_watchers: list):
    """
    Generator that yields status updates and finally the result + trail.
    Yields: (status_message, data)
    """
    start_time = time.time()
    trail = {}
    
    # Load daily sources for logging
    daily_sources = []
    try:
        with open("sources.json", "r") as f:
            daily_sources = json.load(f)
    except:
        pass
    
    # STAGE 1: INGESTION (Perception)
    yield "ingestion", "Checking Ingestion..."
    trail["Stage 1: Ingestion"] = {
        "active_watchers": active_watchers,
        "daily_sources": daily_sources
    }
    
    yield "routing", "Consulting Web..."
    
    plan = get_routing_plan(user_query)
    
    yield "storage", "Accessing Storage..."
    context_text, trail_data = execute_routing_plan(plan, user_query)
    trail.update(trail_data)
    
    deep_summary_mode = "summarize this file" in user_query.lower()
    answer = ""
    if deep_summary_mode:
        file_matches = trail.get("Stage 2: Storage", {}).get("file_matches", [])
        target_path = file_matches[0].get("path") if file_matches else None
        if target_path and os.path.exists(target_path):
            try:
                with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except:
                text = ""
        else:
            text = ""
        chunks = _chunk_by_tokens(text, max_tokens=3000) if text else []
        total_segments = len(chunks)
        if total_segments == 0:
            yield "processing", "Processing Answer..."
            answer = "No readable content found to summarize."
        else:
            for i in range(total_segments):
                yield "summary_progress", {"stage": "reading", "segment": i + 1, "total": total_segments}
                if i > 0:
                    yield "summary_progress", {"stage": "refining", "segment": i + 1, "total": total_segments}
            summary, tokens_used, summary_path = _summarize_refine(chunks)
            trail["Stage 3: Processing"]["summarization_path"] = summary_path
            trail["Stage 3: Processing"]["parameter_activation"] = {"num_predict": 1024, "temperature": 0.1, "num_ctx": 8192}
            trail["Stage 3: Processing"]["refinement_steps"] = max(0, total_segments - 1)
            trail["Stage 4: Transparency"]["context_utilization"] = {"tokens_used": tokens_used, "max_ctx": 8192}
            answer = summary
    else:
        yield "processing", "Processing Answer..."
        answer = generate_answer(user_query, context_text, temperature=0.7)
    
    end_time = time.time()
    
    # Log to file
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "query": user_query,
        "trail": trail,
        "duration": round(end_time - start_time, 2)
    }
    try:
        with open("shadow_execution.log", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"[Brain] Error logging trail: {e}")
        
    yield "complete", (answer, trail)

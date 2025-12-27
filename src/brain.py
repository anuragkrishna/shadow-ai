import json
from litellm import completion
from src import database

# Configuration for the local model
MODEL_NAME = "ollama/llama3.2:3b"

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
    - "keywords": A list of specific keywords or file names to search for.
    
    Definitions:
    - "file_search": When the user asks about local documents, notes, or specific files known to the system.
    - "web_search": When the user asks for current events, news, or information likely found online.
    - "chat_memory": When the user refers to past conversations or things said previously.
    - "general": For greetings, logic puzzles, or general knowledge questions not requiring external data.
    
    Example Input: "What did we discuss about the project roadmap yesterday?"
    Example Output:
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
            # Fallback if model chats instead of outputting JSON
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
            "reasoning": "Error connecting to local model.",
            "keywords": []
        }

def execute_routing_plan(plan: dict):
    """
    Executes the routing plan by retrieving context from the appropriate source.
    Returns a string of retrieved context.
    """
    intent = plan.get("intent")
    keywords = plan.get("keywords", [])
    query_text = " ".join(keywords) if keywords else ""
    
    context_results = []
    
    print(f"[Brain] Executing plan: {intent}")
    
    if intent == "file_search":
        # Query local files in ChromaDB
        results = database.query_memory(
            query_text=query_text,
            n_results=3,
            filters={"source": "file"}
        )
        if results and results['documents']:
            context_results.append(f"Found files: {results['documents'][0]}")
            
    elif intent == "chat_memory":
        # Query chat history in ChromaDB
        results = database.query_memory(
            query_text=query_text,
            n_results=5,
            filters={"source": "chat_history"}
        )
        if results and results['documents']:
            context_results.append(f"Past conversation: {results['documents'][0]}")
            
    elif intent == "web_search":
        # Placeholder for web search integration
        context_results.append("Web search functionality is not yet implemented.")
        
    elif intent == "general":
        # No specific context needed
        pass
        
    return "\n\n".join(context_results)

def generate_answer(user_query: str, context: str):
    """
    Generates the final answer using the retrieved context.
    """
    system_prompt = f"""
    You are Shadow, a helpful local AI assistant.
    Use the following context to answer the user's question.
    If the context is empty or irrelevant, use your general knowledge.
    
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
            api_base="http://localhost:11434"
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating answer: {e}"

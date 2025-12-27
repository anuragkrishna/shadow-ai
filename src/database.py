import chromadb
from chromadb.utils import embedding_functions
import uuid
import os
import datetime

# Initialize ChromaDB Client
# Persist data in a 'chroma_db' folder in the project root
CHROMA_PATH = os.path.join(os.getcwd(), "chroma_db")
client = chromadb.PersistentClient(path=CHROMA_PATH)

# Use a standard embedding function (Sentence Transformers)
# This will automatically download the model if not present
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Get or create collections
# We'll use one collection for simplicity, or separate ones for 'files' and 'chat'
# Merging them allows for unified semantic search, but we can differentiate via metadata.
collection = client.get_or_create_collection(
    name="shadow_memory",
    embedding_function=embedding_func
)

def vectorize_file(file_path: str, content: str):
    """
    Vectorizes a local file and adds it to ChromaDB.
    """
    try:
        # Use file path as ID to allow upserts (updates)
        doc_id = file_path
        
        # Metadata for filtering
        metadata = {
            "source": "file",
            "path": file_path,
            "filename": os.path.basename(file_path),
            "timestamp": datetime.datetime.now().isoformat()
        }

        collection.upsert(
            ids=[doc_id],
            documents=[content],
            metadatas=[metadata]
        )
        print(f"[Database] Vectorized file: {file_path}")
    except Exception as e:
        print(f"[Database] Error vectorizing file {file_path}: {e}")

def add_chat_memory(role: str, content: str):
    """
    Vectorizes a chat message (user or assistant) into ChromaDB.
    """
    try:
        # Generate a unique ID for each message
        msg_id = str(uuid.uuid4())
        
        metadata = {
            "source": "chat_history",
            "role": role,
            "timestamp": datetime.datetime.now().isoformat()
        }

        collection.add(
            ids=[msg_id],
            documents=[content],
            metadatas=[metadata]
        )
        print(f"[Database] Added chat memory: {role}")
    except Exception as e:
        print(f"[Database] Error adding chat memory: {e}")

def query_memory(query_text: str, n_results: int = 5, filters: dict = None):
    """
    Searches the ChromaDB collection for relevant context.
    
    Args:
        query_text: The semantic query.
        n_results: Number of results to return.
        filters: Optional dictionary for metadata filtering (e.g., {"source": "file"}).
    
    Returns:
        List of results with documents and metadata.
    """
    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=filters # ChromaDB 'where' clause for filtering
        )
        return results
    except Exception as e:
        print(f"[Database] Query error: {e}")
        return None

def get_stats():
    """
    Returns statistics about the knowledge base.
    """
    try:
        count = collection.count()
        # Since we can't easily count by metadata without fetching, we'll just return total for now.
        # Or we can do a peek to estimate if needed, but count is fast.
        return {
            "total_documents": count
        }
    except Exception as e:
        return {"error": str(e)}

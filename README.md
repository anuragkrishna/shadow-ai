# Shadow AI

A local-first AI assistant with transparent context routing, designed to integrate multiple knowledge sources (local files, chat history, and web search) into a unified conversational interface.

## ⚠️ Disclaimer

**This project is for educational purposes only.** It is an experimental research project exploring local LLM capabilities, semantic routing, and knowledge integration patterns. The codebase is provided as-is for learning and experimentation.

## 📋 Current Status

**Project Status: Paused**

This project has been paused as of the current date. The development was halted because:

- **Local LLM Performance Limitations**: The performance of local LLMs (tested with Ollama/llama3.2) was not sufficient for the research tasks originally envisioned. The models struggled with complex reasoning, accurate information retrieval, and maintaining context across multiple knowledge sources.

- **Future Potential**: While the current implementation didn't meet the research objectives, the architecture and tool orchestration patterns developed here may be more relevant for:
  - **Tool Orchestration**: The semantic routing system and multi-source context integration could be valuable for orchestrating external tools and APIs
  - **Hybrid AI Systems**: Combining local models with cloud-based models for specific tasks
  - **Knowledge Management**: The vector database integration and file watching mechanisms could be adapted for knowledge management systems

The project may be revisited in the future when local LLM capabilities improve or when focusing on tool orchestration use cases.

## 🎯 Project Overview

Shadow AI is an experimental local-first AI assistant that attempts to intelligently route user queries across multiple knowledge sources:

- **Local Files**: Monitors specified folders and maintains a vector database of document content
- **Chat History**: Stores and retrieves past conversations using semantic search
- **Web Search**: Integrates real-time web search results for current information

The system uses a "semantic router" (a local LLM) to analyze user queries and determine which sources to consult, then synthesizes information from all relevant sources to generate responses.

## 🏗️ Architecture

### Core Components

1. **Brain (`src/brain.py`)**: The central processing unit that:
   - Generates routing plans using a local LLM
   - Executes queries across all knowledge sources
   - Synthesizes context and generates final answers
   - Provides detailed execution trails for transparency

2. **Database (`src/database.py`)**: Vector storage using ChromaDB:
   - Stores embeddings of local files and chat history
   - Enables semantic search across stored content
   - Uses Sentence Transformers (`all-MiniLM-L6-v2`) for embeddings

3. **Search Tool (`src/search_tool.py`)**: Web search integration:
   - Uses DuckDuckGo for search results
   - Scrapes and extracts content from web pages using Trafilatura
   - Filters non-English content

4. **Watcher (`src/watcher.py`)**: File system monitoring:
   - Monitors configured folders for changes
   - Automatically ingests new or modified files into the vector database

5. **Scheduler (`src/scheduler.py`)**: Automated task scheduling:
   - Supports scheduled web scraping and data ingestion

6. **App (`src/app.py`)**: Streamlit web interface:
   - Interactive chat interface
   - Real-time execution trail visualization
   - Knowledge dashboard with statistics
   - Source attribution and transparency features

### Data Flow

```
User Query
    ↓
Semantic Router (Local LLM)
    ↓
Routing Plan (intent, keywords, reasoning)
    ↓
Parallel Context Retrieval:
    ├─→ Local Files (ChromaDB)
    ├─→ Chat History (ChromaDB)
    └─→ Web Search (DuckDuckGo + Scraping)
    ↓
Context Synthesis
    ↓
Answer Generation (Local LLM)
    ↓
Response + Execution Trail
```

## 🚀 Features

- **Multi-Source Knowledge Integration**: Seamlessly combines local files, chat history, and web search
- **Semantic Routing**: Intelligent query analysis to determine optimal knowledge sources
- **Transparent Execution**: Detailed execution trails showing how queries are processed
- **Automatic File Ingestion**: Monitors folders and automatically updates the knowledge base
- **Vector Search**: Fast semantic search across stored documents and conversations
- **Local-First**: Runs entirely on your machine using local LLMs (via Ollama)

## 📦 Setup

### Prerequisites

- Python 3.12+
- [Ollama](https://ollama.ai/) installed and running locally
- A local LLM model (e.g., `llama3.2`) downloaded via Ollama

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd shadow-ai
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure the project:
   - Edit `config.json` to specify:
     - `watch_folders`: Folders to monitor for file changes
     - `llm_model`: Ollama model name (e.g., `ollama/llama3.2`)
     - `embedding_model`: Embedding model for vector search
     - `scrape_schedule`: Optional scheduled scraping configuration

5. Start Ollama (if not already running):
```bash
ollama serve
```

6. Download a model (if not already done):
```bash
ollama pull llama3.2
```

7. Run the application:
```bash
streamlit run src/app.py
```

## 📁 Project Structure

```
shadow-ai/
├── src/
│   ├── app.py           # Streamlit web interface
│   ├── brain.py         # Core processing logic
│   ├── database.py      # ChromaDB vector storage
│   ├── search_tool.py   # Web search integration
│   ├── watcher.py       # File system monitoring
│   └── scheduler.py     # Task scheduling
├── chroma_db/           # ChromaDB persistent storage
├── config.json          # Configuration file
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## 🔧 Configuration

Edit `config.json` to customize:

```json
{
    "watch_folders": ["./your-folder-1", "./your-folder-2"],
    "scrape_schedule": {
        "time": "21:00",
        "sources_file": "sources.json"
    },
    "llm_model": "ollama/llama3.2",
    "embedding_model": "all-MiniLM-L6-v2"
}
```

## 📝 Usage

1. Start the Streamlit app (see Setup above)
2. The app will automatically:
   - Start monitoring configured folders
   - Begin ingesting files into the vector database
3. Ask questions in the chat interface
4. View execution trails to see how queries are processed
5. Check the sidebar for knowledge base statistics

## 🧪 Experimental Nature

This project is experimental and includes several limitations:

- Local LLM performance may vary significantly
- Web scraping may fail on some sites
- Vector search accuracy depends on embedding quality
- No production-ready error handling or security measures
- Performance may be slow with large knowledge bases

## 📄 License

This project is provided for educational purposes. See the disclaimer above.

## 🤝 Contributing

This project is currently paused and not actively maintained. However, if you find it useful for educational purposes or want to experiment with the codebase, feel free to fork and modify as needed.

## 🙏 Acknowledgments

Built using:
- [Ollama](https://ollama.ai/) for local LLM inference
- [ChromaDB](https://www.trychroma.com/) for vector storage
- [Streamlit](https://streamlit.io/) for the web interface
- [LiteLLM](https://github.com/BerriAI/litellm) for LLM abstraction
- [DuckDuckGo Search](https://github.com/deedy5/duckduckgo_search) for web search
- [Trafilatura](https://trafilatura.readthedocs.io/) for web content extraction

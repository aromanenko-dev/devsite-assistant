# DevSite Assistant 🤖

A local, privacy-focused RAG (Retrieval-Augmented Generation) chatbot for your internal developer documentation. Built with ChromaDB, LangChain, and Streamlit.

## Overview

This tool indexes your MDX documentation files and provides an AI-powered Q&A interface that:
- ✅ Runs completely locally with Ollama (optional cloud LLM via OpenAI API)
- ✅ Preserves privacy - your docs never leave your machine
- ✅ Provides source attribution for every answer
- ✅ Maintains conversational context across multiple questions
- ✅ Streams responses in real-time

## Prerequisites

### Required
- **Python 3.8+** (tested with Python 3.11)
- **pip** (Python package manager)
- **Ollama** - For running the local LLM
  ```bash
  brew install ollama  # macOS
  
  # Start Ollama service
  ollama serve
  
  # Pull the required model (in a new terminal)
  ollama pull llama3.1:8b
  ```

### Optional (for cloud LLM instead of Ollama)
- **OpenAI API Key** - For using GPT models
  - Sign up at https://platform.openai.com
  - Create an API key from your dashboard

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/aromanenko-dev/devsite-assistant.git
cd devsite-assistant
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or on Windows:
# .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Start Ollama
Ensure Ollama is running before launching the app:
```bash
# In a separate terminal
ollama serve
```

**Note:** If using OpenAI instead, create a `.env` file with your API key and modify `app.py` to uncomment the OpenAI configuration and comment out Ollama.

## Usage

### Step 1: Add Your Documentation

Place your `.mdx` documentation files in the `./data/` directory:
```bash
cp /path/to/your/docs/*.mdx ./data/
```

**Supported format:** MDX (Markdown with JSX components)

### Step 2: Build the Index

Run the indexing script to process and embed your documentation:
```bash
python build_index.py
```

**Index from a custom directory:**
```bash
python build_index.py --path /path/to/your/docs
```

**What this does:**
- Loads all `.mdx` files from `./data/` (or custom path with `--path`)
- Strips JSX/React components
- Splits content into 800-character chunks
- Creates embeddings using `BAAI/bge-small-en` model
- Stores in local ChromaDB at `./chroma_db/`

**First run:** Downloads the embedding model (~100MB) - this is normal.

⚠️ **Warning:** This script deletes and rebuilds the entire index each time. No incremental updates.

### Step 3: Launch the Chatbot

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

**Ask questions about your documentation:**
- "How do we implement autoscaling?"
- "What are the security best practices?"
- "Tell me about data ownership principles"

### Optional: Explore the Index

To inspect what's been indexed or test semantic search:
```bash
streamlit run explore_chroma.py
```

This debugging tool lets you:
- View all indexed documents
- Test semantic search queries
- Check metadata and chunk content

## Configuration

### Switching Between LLM Providers

**Using Ollama (default - fully local):**
```python
# In app.py (current configuration)
from langchain_ollama import ChatOllama
llm = ChatOllama(model="llama3.1:8b")

# Other Ollama models you can try:
# llm = ChatOllama(model="phi3:mini")     # Faster, smaller
# llm = ChatOllama(model="qwen2.5:0.5b")  # Very fast, minimal
```

**Using OpenAI (cloud - requires API key):**
```python
# In app.py, comment out Ollama and uncomment:
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
# Also create .env with: OPENAI_API_KEY=sk-...
```

### Adjusting Retrieval Parameters

**Number of chunks retrieved per query:**
```python
# In app.py, line 18
retriever = vectorstore.as_retriever(search_kwargs={"k": 8})  # Currently set to 8, increase for more context
```

**Maximum characters per document chunk:**
```python
# In app.py, line 43
def retrieve_context(query, max_tokens_per_doc=3000):  # Currently set to 3000
```

**Chunk size during indexing:**
```python
# In build_index.py
splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
```

### Improving Answer Quality

The system uses a refined prompt that:
- **Enforces grounding** - Answers ONLY using documented information
- **Allows inferences** - Can make reasonable conclusions from context
- **Encourages citations** - Asks model to reference specific documentation
- **Retrieves more context** - 8 chunks × 3000 chars for comprehensive information

**Custom documentation path:**
```bash
# Index documentation from a different directory
python build_index.py --path /path/to/docs

# Use default ./data/ directory
python build_index.py
```

## Project Structure

```
devsite-assistant/
├── app.py                 # Main Streamlit chatbot UI
├── build_index.py         # Documentation indexing script
├── explore_chroma.py      # Database exploration tool
├── requirements.txt       # Python dependencies
├── .env                   # API keys (not in git)
├── data/                  # Your .mdx documentation files
│   └── *.mdx
└── chroma_db/            # Vector database (generated)
    └── ...
```

## How It Works

1. **Indexing Pipeline** (`build_index.py`):
   ```
   MDX files → Clean JSX → Split into chunks → Embed → Store in ChromaDB
   ```

2. **Query Pipeline** (`app.py`):
   ```
   User question → Retrieve 8 chunks (3000 chars each) → Build context → LLM → Streamed answer
   ```

3. **Conversational Memory**:
   - Last 3 exchanges stored in session state
   - Enables follow-up questions: "tell me more", "what about X?"

4. **Inference Statistics** (displayed after each query):
   - Token count and generation speed (tokens/second)
   - Total inference time and time to first token (TTFT)
   - Active model name dynamically shown

## Troubleshooting

### "No module named 'streamlit'"
```bash
source .venv/bin/activate  # Activate virtual environment first
pip install -r requirements.txt
```

### "No collections found in ChromaDB"
```bash
python build_index.py  # Build the index first
```

### "Connection refused" or "Ollama not responding"
- Make sure Ollama is running: `ollama serve`
- Verify the model is installed: `ollama list`
- Pull the model if needed: `ollama pull llama3.1:8b`

### "OpenAI API key not found" (if using OpenAI)
- Create `.env` file with `OPENAI_API_KEY=sk-...`
- Make sure you uncommented the OpenAI imports in `app.py`

### Chat history disappears
- History is stored in browser session only
- Refreshing the page clears conversation
- This is by design - no persistent storage

### Poor answer quality
1. Check what's being retrieved: run `explore_chroma.py`
2. Increase retrieval count in `app.py`: `search_kwargs={"k": 12}` (default is 8)
3. Increase context window: set `max_tokens_per_doc=4000` (default is 3000)
4. View context sent to LLM in terminal output
5. Ensure documentation files are well-structured

## Limitations

- **No incremental indexing** - rebuilds entire database each time
- **No chat persistence** - conversations lost on browser refresh  
- **English only** - embedding model optimized for English
- **Local storage** - ChromaDB is file-based, not distributed
- **MDX-specific** - JSX components are stripped, may affect code examples

## Contributing

When adding features, consider:
- Maintaining the 3-script architecture (index, chat, explore)
- Preserving privacy-first design
- Documenting new configuration options

## License

[Add your license here]

## Support

For issues or questions:
- Check `explore_chroma.py` to verify indexing worked
- Review terminal output from `app.py` for debugging
- Ensure `.mdx` files are valid Markdown format

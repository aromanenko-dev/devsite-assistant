# DevSite Assistant 🤖

A local, privacy-focused AI assistant that intelligently searches across both documentation and source code. Built with ChromaDB, LangChain, Ollama, and Streamlit.

## Overview

This tool indexes your documentation and source code, then uses intelligent routing to answer questions from the most relevant source:

- ✅ **Unified Search** - Ask questions and get answers from docs, code, or both automatically
- ✅ **Intelligent Routing** - Queries are automatically routed to the most relevant source
- ✅ **Runs Completely Locally** - With Ollama (optional cloud LLM via OpenAI API)
- ✅ **Preserves Privacy** - Your docs and code never leave your machine
- ✅ **Source Attribution** - Clearly shows which sources were used (docs vs code)
- ✅ **Maintains Context** - Conversational memory across multiple questions
- ✅ **Streams Responses** - Real-time token-by-token output

## Features

### Multi-Source Intelligence
- **📚 Documentation Search** - Find information in your docs, guides, and wikis
- **💻 Code Search** - Search and understand your source code (Python, JavaScript, Java, Go, Rust, C++, etc.)
- **🧭 Intelligent Routing** - Automatically chooses the best source(s) for each question
- **🔗 Combined Context** - Answers that reference both documentation and code examples

### Developer-Friendly
- **Multiple Paths** - Index docs and code from different locations
- **Format Support** - Works with `.md`, `.mdx`, `.py`, `.js`, `.ts`, `.java`, `.go`, `.rs`, and more
- **Symbolic Links** - Organize multiple repos in a single index
- **Code Context** - Extracts functions, classes, and imports for better understanding

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

Place your documentation files in the `./data/` directory:
```bash
cp /path/to/your/docs/*.mdx ./data/
cp /path/to/your/docs/*.md ./data/
```

**Supported formats:** 
- MDX (Markdown with JSX components)
- MD (Standard Markdown)

**Multiple sources:**
You can also use symbolic links to include documentation from other locations:
```bash
# Link to a local GitHub repo
ln -s /path/to/github/repo/docs ./data/github-docs

# Link to another documentation source
ln -s /path/to/another/repo ./data/other-docs
```

### Step 2: Build the Index

Run the indexing script to process and embed your documentation:
```bash
python build_index.py
```

**Index from a custom directory:**
```bash
python build_index.py --path /path/to/your/docs
```

**Index from multiple directories:**
```bash
python build_index.py --path ./data /path/to/github/repo /path/to/another/repo
```

**What this does:**
- Loads all `.mdx` and `.md` files from specified path(s)
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

## Example Workflows

### Workflow 1: Setup Question (Routes to DOCS)
```
User: "How do I set up the project?"
       ↓
Router: DOCS
       ↓
Retrieves: setup guide, prerequisites
       ↓
Response: Step-by-step instructions from documentation
```

### Workflow 2: Code Question (Routes to CODE)
```
User: "What does the authenticate() function do?"
       ↓
Router: CODE
       ↓
Retrieves: authenticate() implementation and context
       ↓
Response: Shows the function with explanation
```

### Workflow 3: Integration Question (Routes to BOTH)
```
User: "How is authentication implemented in our system?"
       ↓
Router: BOTH
       ↓
Retrieves: Auth architecture (docs) + login function (code)
       ↓
Response: Combines architecture explanation + code examples
```

## Advanced Configuration

### Adjusting Retrieval Parameters

**Documentation retrieval** (in `app.py`):
```python
docs_retriever = docs_vectorstore.as_retriever(search_kwargs={"k": 8})  # Increase for more context
```

**Code retrieval** (in `app.py`):
```python
code_retriever = code_vectorstore.as_retriever(search_kwargs={"k": 5})  # Increase for more code examples
```

**Context window size** (in `build_index.py`):
```python
chunk_size=800  # For docs (increase for longer documentation)
```

**Code chunk size** (in `code_search_agent.py`):
```python
chunk_size=1500  # For code (preserve function context)
```

### Changing LLM Models

**Use Ollama (local):**
```python
# In router_agent.py and app.py
llm = ChatOllama(model="gpt-oss:20b")
# Options: phi3:mini, llama3.1:8b, etc.
```

**Use OpenAI:**
```python
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
# Set OPENAI_API_KEY in .env
```

## Features

### Multi-Source Documentation
- **Local GitHub repos**: Index documentation from local Git repositories
- **Multiple directories**: Combine docs from different sources in one index
- **Markdown support**: Works with both `.md` and `.mdx` files
- **Symbolic links**: Use symlinks to organize sources in `./data/` folder

### Example: Indexing Multiple Sources
```bash
# Create symlinks to organize sources
ln -s ~/github/backend-docs/docs ./data/backend
ln -s ~/github/frontend-docs ./data/frontend

# Index everything together
python build_index.py

# Or specify paths directly
python build_index.py --path ./data ~/github/architecture-docs ~/projects/wiki
```

## Project Structure

```
devsite-assistant/
├── app.py                      # Main unified assistant (docs + code)
├── build_index.py              # Documentation indexing script
├── code_search_agent.py         # Code indexing script
├── router_agent.py             # Query routing logic
├── explore_chroma.py           # ChromaDB explorer tool
├── requirements.txt            # Python dependencies
├── .env                        # API keys (not in git)
├── data/                       # Documentation files
│   ├── *.md
│   └── *.mdx
├── chroma_db/                  # Documentation index
└── chroma_db_code/             # Code search index
```

## How It Works

### Architecture

```
User Question
    ↓
Query Router (router_agent.py)
    ↓
    ├→ DOCS: Search documentation index
    ├→ CODE: Search code index
    └→ BOTH: Search both indexes
    ↓
Retrieve Relevant Context
    ↓
Unified Prompt to LLM
    ↓
Streamed Response with Attribution
```

### Routing Logic

The router analyzes each question and decides:

| Query Type | Route | Example |
|-----------|-------|---------|
| **How do I...** | DOCS | "How do I set up authentication?" |
| **What does X do** | CODE | "What does the login function do?" |
| **How is X implemented** | BOTH | "How is authentication implemented?" |
| **Show me examples** | BOTH | "Show error handling patterns" |
| **Architecture/Design** | DOCS | "What are the design principles?" |

### Processing Pipeline

1. **Documentation Pipeline** (`build_index.py`):
   ```
   .md/.mdx files → Clean JSX → Split chunks (800 chars) → Embed → Store in ChromaDB
   ```

2. **Code Pipeline** (`code_search_agent.py`):
   ```
   Source files → Extract context → Split chunks (1500 chars) → Embed → Store in ChromaDB
   ```

3. **Query Pipeline** (`app.py`):
   ```
   Question → Route → Retrieve (8 docs or 5 code) → Build context → LLM → Stream answer
   ```

## Troubleshooting

### "No indexes found"
```bash
# Build both indexes
python build_index.py --path ./data
python code_search_agent.py --path /path/to/repo
```

### "Connection refused" or "Ollama not responding"
- Make sure Ollama is running: `ollama serve`
- Verify the model is installed: `ollama list`
- Pull the model if needed: `ollama pull gpt-oss:20b`

### "No module named 'streamlit'"
```bash
source .venv/bin/activate  # Activate virtual environment first
pip install -r requirements.txt
```

### Poor answer quality
1. Check what's being retrieved: run `explore_chroma.py`
2. Increase retrieval count: 
   - For docs: `search_kwargs={"k": 12}` (default is 8)
   - For code: `search_kwargs={"k": 8}` (default is 5)
3. Check if query is routing correctly (look for "🧭 Routing to:" message)
4. Increase chunk sizes if content is cut off

### Chat history disappears
- History is stored in browser session only
- Refreshing the page clears conversation
- This is by design - no persistent storage

## Limitations

- **No incremental indexing** - Rebuilds entire databases each time
- **No persistent chat** - Conversations lost on browser refresh  
- **Single language per query** - Embedding model optimized for English
- **Local storage** - ChromaDB is file-based, not distributed
- **JSX stripping** - React components removed from documentation
- **Code extraction** - Context extraction works best for popular languages

## Contributing

When adding features, consider:
- Maintaining the modular architecture (build scripts, router, app)
- Supporting new file types (add to `CODE_EXTENSIONS` in `code_search_agent.py`)
- Preserving privacy-first design
- Documenting new routing rules

## Roadmap

Potential enhancements:
- [ ] Incremental indexing (update without rebuilding)
- [ ] Persistent chat history (SQLite or similar)
- [ ] Web UI for configuration
- [ ] Support for more languages (Rust, Kotlin, Swift, etc.)
- [ ] Multi-language queries
- [ ] Custom routing rules
- [ ] Integration with Git history
- [ ] API endpoint for programmatic access

## License

[Add your license here]

## Support

For issues or questions:
- Check `explore_chroma.py` to verify indexing worked
- Review terminal output from `app.py` for debugging
- Ensure `.mdx` files are valid Markdown format

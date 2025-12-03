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
- **🧭 Intelligent Routing with Fallback** - Automatically chooses the best source(s), with automatic fallback if primary source insufficient
- **✅ Quality-Aware Retrieval** - Checks if results are sufficient and falls back to other sources if needed
- **🔗 Combined Context** - Answers that reference both documentation and code examples
- **🛡️ Anti-Hallucination** - Deterministic LLM (temperature=0) with strict grounding rules and citation enforcement

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
  
  # Pull a recommended model (in a new terminal)
  ollama pull mistral  # Recommended for M2/M3 MacBooks
  # or: ollama pull llama3.1:8b
  # or: ollama pull phi (for fastest/lightest)
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
# From root directory
python src/build_index.py

# Or index from a custom directory:
python src/build_index.py --path /path/to/your/docs

# Index from multiple directories:
python src/build_index.py --path ./data /path/to/github/repo /path/to/another/repo
```

**What this does:**
- Loads all `.mdx` and `.md` files from specified path(s)
- Strips JSX/React components
- Splits content into 800-character chunks
- Creates embeddings using `BAAI/bge-small-en` model
- Stores in local ChromaDB at `./chroma_db/`

**First run:** Downloads the embedding model (~100MB) - this is normal.

⚠️ **Warning:** This script deletes and rebuilds the entire index each time. No incremental updates.

### Step 3: Build Code Index (Optional)

To enable code search across your repositories:

```bash
# Index source code
python src/code_search_agent.py --path /path/to/repo

# Index multiple repositories
python src/code_search_agent.py --path /path/to/repo1 /path/to/repo2
```

**What this does:**
- Loads code files from specified paths (20+ language support)
- **Extracts semantic structure** (functions, classes, methods, constructors)
- **For Java/XML:** Creates comprehensive metadata chunks with:
  - Complete method lists with signatures and return types
  - Constructor information with parameters
  - Inheritance hierarchy (extends/implements)
  - Element structure and attributes
- Splits into 1500-character chunks (2000+ for Java to preserve method context)
- Creates embeddings and stores in `./chroma_db_code/`
- Supports efficient querying for: "What methods does X have?", "Show me constructors"

**First run:** Downloads embedding model if needed.

**Enhanced Code Indexing:**
The indexer creates multiple chunk types for optimal retrieval:
1. **Semantic Summary** - Overview of file structure
2. **Element Metadata** (Java classes, XML elements) - Complete method/element listings
3. **Code Chunks** - Actual source code for implementation details

Example Java class indexing:
```
Java Class: SolacePubSubManager
Constructors (2):
  - SolacePubSubManager(brokerURL)
  - SolacePubSubManager(brokerURL, username, password)
Methods (6):
  - initialize(brokerURL) -> void
  - publish(topic, message) -> void
  - subscribe(topic) -> void
  - disconnect() -> void
  - isConnected() -> boolean
  - getStatus() -> String
```

See [ENHANCED_INDEXER_IMPROVEMENTS.md](./ENHANCED_INDEXER_IMPROVEMENTS.md) for detailed technical documentation.

### Step 4: Launch the Chatbot

```bash
# Default model (gpt-oss:20b)
streamlit run src/app.py

# With Mistral (recommended for M2/M3 - faster & better quality)
streamlit run src/app.py -- --model mistral

# With other models
streamlit run src/app.py -- --model phi          # Fastest
streamlit run src/app.py -- --model llama3.1:8b  # Default quality

# Using environment variable
export DEVSITE_MODEL=mistral
streamlit run src/app.py
```

The app will open in your browser at `http://localhost:8501`

**Ask questions about your documentation:**
- "How do we implement autoscaling?"
- "What are the security best practices?"
- "Tell me about data ownership principles"

### Optional: Explore the Index

To inspect what's been indexed or test semantic search:
```bash
streamlit run src/explore_chroma.py
```

## Example Workflows

### Workflow 1: Setup Question (Routes to DOCS)
```
User: "How do I set up the project?"
       ↓
Router: DOCS
       ↓
Quality Check: SUFFICIENT
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
Quality Check: SUFFICIENT
       ↓
Retrieves: authenticate() implementation and context
       ↓
Response: Shows the function with explanation
```

### Workflow 3: Integration Question with Fallback (Routes BOTH)
```
User: "Explain transaction processing"
       ↓
Router: DOCS (primary)
       ↓
Quality Check: INSUFFICIENT
       ↓
Fallback: Add CODE results
       ↓
Retrieves: Architecture (docs) + TransactionProcessor class (code)
       ↓
Response: Combined explanation with examples
```

## Advanced Configuration

### Model Selection

**Available Models** (in order of quality/speed balance for M2/M3):

| Model | Size | Speed | Quality | Best For | RAM |
|-------|------|-------|---------|----------|-----|
| **mistral** | 7B | ⚡⚡⚡ | ⭐⭐⭐⭐ | **Recommended** | 13GB |
| phi | 2.7B | ⚡⚡⚡⚡ | ⭐⭐⭐ | Speed | 3GB |
| llama3.1:8b | 8B | ⚡⚡⚡ | ⭐⭐⭐ | Balance | 13GB |
| orca-mini | 7B | ⚡⚡⚡ | ⭐⭐⭐⭐ | Reasoning | 13GB |
| gpt-oss:20b | 20B | ⚡⚡ | ⭐⭐⭐⭐ | Quality | 20GB+ |

**Configure via CLI:**
```bash
streamlit run app.py -- --model mistral
```

**Configure via environment variable:**
```bash
export DEVSITE_MODEL=mistral
streamlit run app.py
```

**Pull new models:**
```bash
ollama pull mistral
ollama pull phi
ollama pull llama3.1:8b
ollama list  # See all available models
```

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

### Fallback Routing Strategy

The assistant uses intelligent fallback routing:

1. **Route query** to primary source (DOCS/CODE)
2. **Check quality** of retrieved results with LLM
3. **If insufficient**, automatically fall back to secondary source
4. **Combine results** for comprehensive answer

**Example:**
```
User: "Explain transaction processing"
  ↓
Route: DOCS (architecture question)
  ↓
Retrieve: Documentation about transactions
  ↓
Quality: INSUFFICIENT (missing implementation details)
  ↓
Fallback: Search CODE for transaction processor
  ↓
Final route: DOCS+CODE
  ↓
Answer: Architecture + implementation examples
```

This ensures you always get the best answer by using multiple sources when needed.

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
├── src/                        # Python source code
│   ├── app.py                  # Main unified assistant (docs + code)
│   ├── build_index.py          # Documentation indexing script
│   ├── code_search_agent.py    # Code indexing script
│   ├── router_agent.py         # Query routing logic
│   └── explore_chroma.py       # ChromaDB explorer tool
├── data/                       # Documentation files
│   ├── *.md
│   └── *.mdx
├── chroma_db/                  # Documentation index
├── chroma_db_code/             # Code search index
├── requirements.txt            # Python dependencies
├── .env                        # API keys (not in git)
└── README.md                   # This file
```

## How It Works

### Architecture

```
User Question
    ↓
Query Router (intelligent classification)
    ↓
Primary Retrieval
    ├→ DOCS: Search documentation index
    ├→ CODE: Search code index
    └→ BOTH: Search both indexes
    ↓
Quality Check (LLM evaluates results)
    ↓
    ├→ SUFFICIENT: Use primary results
    └→ INSUFFICIENT: Fallback to secondary source
    ↓
Combine Context (merge from multiple sources if needed)
    ↓
Generate Answer (with temperature=0 for grounding)
    ↓
Streamed Response with Citations & Attribution
```

### Routing Logic

The router analyzes each question and decides:

| Query Type | Primary Route | Fallback | Example |
|-----------|-------|----------|---------|
| **How do I...** | DOCS | CODE | "How do I set up authentication?" |
| **What does X do** | CODE | DOCS | "What does the login function do?" |
| **How is X implemented** | BOTH | - | "How is authentication implemented?" |
| **Show me examples** | CODE | DOCS | "Show error handling patterns" |
| **Architecture/Design** | DOCS | CODE | "What are the design principles?" |

### Anti-Hallucination Measures

1. **Temperature=0** - Deterministic responses (no randomness)
2. **Strict Grounding Prompt** - Enforces citation requirements
3. **Quality Checking** - Validates retrieved context before using
4. **Context Transparency** - Shows what sources were used
5. **Fallback Strategy** - Searches multiple sources if primary is insufficient
6. **Citation Enforcement** - Forces model to cite [filename] for claims

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
python src/build_index.py --path ./data
python src/code_search_agent.py --path /path/to/repo
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
1. Check what's being retrieved: run `streamlit run src/explore_chroma.py`
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
- [ ] Web UI for configuration and model selection
- [ ] Support for more languages (Rust, Kotlin, Swift, etc.)
- [ ] Multi-language queries and documents
- [ ] Custom routing rules via configuration
- [ ] Integration with Git commit history for context
- [ ] API endpoint for programmatic access
- [ ] Hybrid search (vector + keyword)
- [ ] Re-ranking for better retrieval quality

## License

[Add your license here]

## Support

For issues or questions:
- Check `explore_chroma.py` to verify indexing worked
- Review terminal output from `app.py` for debugging
- Ensure `.mdx` files are valid Markdown format

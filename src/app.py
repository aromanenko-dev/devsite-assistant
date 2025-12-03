import streamlit as st
import chromadb
import time
import os
import sys
from langchain_community.vectorstores import Chroma
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

from dotenv import load_dotenv
load_dotenv()

# --- Parse CLI arguments for model selection ---
DEFAULT_MODEL = "gpt-oss:20b"
model_name_config = DEFAULT_MODEL

# Check for --model argument
if "--model" in sys.argv:
    idx = sys.argv.index("--model")
    if idx + 1 < len(sys.argv):
        model_name_config = sys.argv[idx + 1]

# Check for environment variable (takes precedence)
model_name_config = os.getenv("DEVSITE_MODEL", model_name_config)

# --- Initialize both vector stores ---
chroma_client = chromadb.PersistentClient(path="./chroma_db")
chroma_code_client = chromadb.PersistentClient(path="./chroma_db_code")

# Documentation vectorstore
try:
    docs_vectorstore = Chroma(collection_name="devsite_docs", client=chroma_client)
    docs_retriever = docs_vectorstore.as_retriever(search_kwargs={"k": 8})
    docs_available = True
except:
    docs_available = False

# Code vectorstore
try:
    code_vectorstore = Chroma(collection_name="devsite_code", client=chroma_code_client)
    code_retriever = code_vectorstore.as_retriever(search_kwargs={"k": 5})
    code_available = True
except:
    code_available = False

# --- Initialize local LLM ---
llm = ChatOllama(
    model=model_name_config,
    temperature=0,
)
model_name = llm.model

# --- Smart Router with Fallback ---
ROUTER_PROMPT = ChatPromptTemplate.from_template(
    """You are a query router. Analyze the user's question and determine which knowledge sources to search.

Categories:
- DOCS: Setup, configuration, guides, architecture, principles, how-to, installation
- CODE: Implementation, functions, classes, methods, bugs, code patterns, API details
- BOTH: Needs both documentation AND code examples

Respond with ONLY one: DOCS, CODE, or BOTH

Examples:
"How do I set up the project?" -> DOCS
"What does the authenticate() function do?" -> CODE
"How is authentication implemented?" -> BOTH
"What are the design principles?" -> DOCS
"Show me the payment processing logic" -> CODE
"Explain error handling with examples" -> BOTH

User question: {question}

Response (one word only):""")

QUALITY_CHECK_PROMPT = ChatPromptTemplate.from_template(
    """Check if the retrieved context adequately answers the user's question.

User question: {question}

Retrieved context (first 1000 chars):
{context}

Does this context contain enough information to answer the question?

Respond with only: SUFFICIENT or INSUFFICIENT

- SUFFICIENT: Context has relevant information to answer
- INSUFFICIENT: Context is missing or irrelevant

Response (one word only):""")

def route_query(question):
    """Intelligently route query to appropriate sources"""
    prompt = ROUTER_PROMPT.format(question=question)
    response = llm.invoke(prompt).content.strip().upper()
    
    # Ensure valid response
    if "CODE" in response and "BOTH" not in response:
        return "CODE"
    elif "BOTH" in response:
        return "BOTH"
    else:
        return "DOCS"

def check_result_quality(question, context):
    """Check if retrieved context is sufficient to answer the question"""
    if not context or len(context.strip()) < 100:
        return "INSUFFICIENT"
    
    prompt = QUALITY_CHECK_PROMPT.format(question=question, context=context[:1000])
    response = llm.invoke(prompt).content.strip().upper()
    
    return response if response in ["SUFFICIENT", "INSUFFICIENT"] else "INSUFFICIENT"

def get_retrieved_context(docs_list):
    """Convert document list to context string"""
    return "\n\n---\n\n".join(d.page_content[:1000] for d in docs_list)

# --- Streamlit page setup ---
st.set_page_config(page_title="DevSite Assistant", page_icon="🤖")
st.title("🤖 DevSite AI Assistant")
st.caption("Smart search across documentation and code (local + private)")

# --- Show available sources ---
col1, col2 = st.columns(2)
with col1:
    if docs_available:
        st.success("📚 Documentation index ready")
    else:
        st.error("📚 Documentation index missing")
        
with col2:
    if code_available:
        st.success("💻 Code index ready")
    else:
        st.error("💻 Code index missing")

if not docs_available and not code_available:
    st.error("❌ No indexes found. Please run build_index.py and code_search_agent.py first.")
    st.stop()

# --- Initialize chat history ---
if "history" not in st.session_state:
    st.session_state["history"] = []

# --- Display chat history ---
for turn in st.session_state["history"]:
    with st.chat_message("user"):
        st.markdown(turn["user"])
    with st.chat_message("assistant"):
        st.markdown(turn["assistant"]["response"])
        if turn["assistant"].get("sources"):
            source_type = turn["assistant"]["source_type"]
            sources = turn["assistant"]["sources"][:3]
            routing_info = turn["assistant"].get("routing_info", "")
            st.caption(f"📌 Sources ({source_type}): {', '.join(sources)}")
            if routing_info:
                st.caption(f"🔄 {routing_info}")

# --- Chat input ---
user_query = st.chat_input("Ask about documentation or code...")

if user_query:
    # Smart routing with fallback
    with st.spinner("🧭 Analyzing query..."):
        primary_route = route_query(user_query)
    
    st.info(f"🧭 Primary routing: **{primary_route}**")
    
    retrieved_docs = []
    final_route = primary_route
    routing_info = ""
    
    # Search primary source
    with st.spinner("🔍 Searching primary source..."):
        if primary_route in ["DOCS", "BOTH"] and docs_available:
            docs = docs_retriever.invoke(user_query)
            retrieved_docs.extend([(doc, "docs") for doc in docs])
        
        if primary_route in ["CODE", "BOTH"] and code_available:
            code = code_retriever.invoke(user_query)
            retrieved_docs.extend([(doc, "code") for doc in code])
    
    # Check quality and apply fallback if needed
    if retrieved_docs:
        context_sample = get_retrieved_context([doc for doc, _ in retrieved_docs])
        quality = check_result_quality(user_query, context_sample)
        
        if quality == "INSUFFICIENT":
            st.warning(f"⚠️ Primary source ({primary_route}) has limited results. Trying fallback...")
            
            # Fallback logic
            if primary_route == "DOCS" and code_available:
                with st.spinner("🔄 Falling back to CODE..."):
                    code = code_retriever.invoke(user_query)
                    retrieved_docs.extend([(doc, "code") for doc in code])
                final_route = "DOCS+CODE"
                routing_info = "Fallback: Added CODE context"
            
            elif primary_route == "CODE" and docs_available:
                with st.spinner("🔄 Falling back to DOCS..."):
                    docs = docs_retriever.invoke(user_query)
                    retrieved_docs.extend([(doc, "docs") for doc in docs])
                final_route = "CODE+DOCS"
                routing_info = "Fallback: Added DOCS context"
        else:
            routing_info = f"Quality check: {quality}"
    
    if not retrieved_docs:
        st.warning("❌ No relevant information found in any sources.")
        st.stop()
    
    # Build context
    context_parts = []
    
    docs_context = [doc for doc, src_type in retrieved_docs if src_type == "docs"]
    code_context = [doc for doc, src_type in retrieved_docs if src_type == "code"]
    
    if docs_context:
        context_parts.append("## Documentation Context:\n" + 
                           "\n\n---\n\n".join(d.page_content[:2000] for d in docs_context))
    
    if code_context:
        context_parts.append("## Code Context:\n" + 
                           "\n\n---\n\n".join(d.page_content[:2000] for d in code_context))
    
    full_context = "\n\n".join(context_parts)
    
    # Build prompt with strict anti-hallucination guidelines
    prompt = ChatPromptTemplate.from_template(
        """You are a documentation and code assistant. Your knowledge is LIMITED to the provided context below.

{context}

User question: {question}

STRICT RULES:
1. Answer ONLY using information explicitly stated in the context above
2. Include citations: Reference specific files like [auth.py] or [setup.md]
3. If information is missing, say: "I don't see that information in the indexed sources."
4. Distinguish between documentation sources (📖) and code sources (💻)
5. Use direct quotes when possible: "According to setup.md: '...'"
6. Do not make assumptions or inferences beyond what's clearly stated
7. If you're uncertain, acknowledge it explicitly

Answer with citations:"""
    )
    
    formatted_prompt = prompt.format(context=full_context, question=user_query)
    
    # Generate response with streaming
    full_response = ""
    token_count = 0
    start_time = time.time()
    first_token_time = None
    
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            for chunk in llm.stream(formatted_prompt):
                if first_token_time is None:
                    first_token_time = time.time()
                full_response += chunk.content
                token_count += 1
                message_placeholder.markdown(full_response + "▌")
                time.sleep(0.01)
            
            message_placeholder.markdown(full_response)
        except Exception as e:
            st.error(f"❌ Error generating response: {str(e)}")
            st.info("💡 Make sure Ollama is running: `ollama serve`")
            st.stop()
    
    # Add context viewer for transparency
    with st.expander("🔍 View Retrieved Context (verify grounding)"):
        st.caption("This shows what information the AI had access to:")
        
        if docs_context:
            st.markdown("**📖 Documentation:**")
            for i, doc in enumerate(docs_context[:3], 1):
                source = doc.metadata.get("source", "unknown")
                st.markdown(f"**Chunk {i}** from `{source}`:")
                st.code(doc.page_content[:600], language="markdown")
        
        if code_context:
            st.markdown("**💻 Code:**")
            for i, doc in enumerate(code_context[:3], 1):
                source = doc.metadata.get("source", "unknown")
                lang = doc.metadata.get("language", "python")
                st.markdown(f"**Chunk {i}** from `{source}`:")
                st.code(doc.page_content[:600], language=lang)
    
    st.markdown("### 📚 Sources Used")
    docs_sources = set()
    code_sources = set()
    
    for doc, src_type in retrieved_docs:
        source = doc.metadata.get("source", "unknown")
        if src_type == "docs":
            docs_sources.add(source)
        else:
            code_sources.add(source)
    
    if docs_sources:
        st.caption("**📖 Documentation:**")
        for i, src in enumerate(docs_sources, 1):
            st.caption(f"  {i}. `{src}`")
    
    if code_sources:
        st.caption("**💻 Code:**")
        for i, src in enumerate(code_sources, 1):
            st.caption(f"  {i}. `{src}`")
    
    # Statistics
    end_time = time.time()
    total_time = end_time - start_time
    time_to_first_token = first_token_time - start_time if first_token_time else 0
    tokens_per_second = token_count / total_time if total_time > 0 else 0
    
    # Save to history
    st.session_state["history"].append({
        "user": user_query,
        "assistant": {
            "response": full_response,
            "source_type": final_route,
            "sources": list(docs_sources | code_sources),
            "routing_info": routing_info
        }
    })
    
    st.markdown("---")
    st.caption(f"⚙️ Routing: {final_route} | Model: {model_name}")
    if routing_info:
        st.caption(f"🔄 {routing_info}")
    st.caption(f"📊 Tokens: {token_count} | Speed: {tokens_per_second:.1f} t/s | Time: {total_time:.2f}s | TTFT: {time_to_first_token:.2f}s")

st.markdown("---")
st.caption("💡 Smart routing with fallback: Ensures best answer by checking result quality and switching sources if needed!")

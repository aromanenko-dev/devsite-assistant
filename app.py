import streamlit as st
import chromadb
import time
from langchain_community.vectorstores import Chroma
from langchain_ollama import ChatOllama
# from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from router_agent import route_query

from dotenv import load_dotenv
load_dotenv()

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
# Use a smaller model like "phi3:mini" or "qwen2.5:0.5b" for faster responses
# llm = ChatOllama(model="phi3:mini")
# llm = ChatOllama(model="llama3.1:8b")
llm = ChatOllama(model="gpt-oss:20b")
model_name = llm.model

# llm = ChatOpenAI(
#     # model="gpt-4o-mini",   # or "gpt-4o" / "gpt-3.5-turbo"
#     model="gpt-4.1-nano",   
#     temperature=0,
# )

# --- Streamlit page setup ---
st.set_page_config(page_title="DevSite Assistant", page_icon="🤖")
st.title("🤖 DevSite AI Assistant")
st.caption("Unified search across documentation and code (local + private)")

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
            st.caption(f"📌 Sources ({source_type}): " + ", ".join(sources))

# --- Chat input ---
user_query = st.chat_input("Ask about documentation or code...")

if user_query:
    # Route the query
    with st.spinner("Analyzing query..."):
        route = route_query(user_query)
    
    st.info(f"🧭 Routing to: **{route}**")
    
    retrieved_docs = []
    source_type = route
    
    with st.spinner("Searching..."):
        if route in ["DOCS", "BOTH"] and docs_available:
            docs = docs_retriever.invoke(user_query)
            retrieved_docs.extend([(doc, "docs") for doc in docs])
        
        if route in ["CODE", "BOTH"] and code_available:
            code = code_retriever.invoke(user_query)
            retrieved_docs.extend([(doc, "code") for doc in code])
    
    if not retrieved_docs:
        st.warning("No relevant information found.")
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
    
    # Build prompt
    prompt = ChatPromptTemplate.from_template(
        """You are a helpful assistant that answers questions using provided documentation and code.

{context}

User question: {question}

Guidelines:
- Use both documentation and code context when available
- Provide practical examples from the code when relevant
- Cite specific files, functions, or sections
- Be clear about whether you're referencing docs or code
- If something isn't in the provided context, say so clearly

Answer:"""
    )
    
    formatted_prompt = prompt.format(context=full_context, question=user_query)
    
    # Generate response with streaming
    full_response = ""
    token_count = 0
    start_time = time.time()
    first_token_time = None
    
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        for chunk in llm.stream(formatted_prompt):
            if first_token_time is None:
                first_token_time = time.time()
            full_response += chunk.content
            token_count += 1
            message_placeholder.markdown(full_response + "▌")
            time.sleep(0.01)
        
        message_placeholder.markdown(full_response)
    
    # Show sources
    st.markdown("### 📚 Sources")
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
            "source_type": route,
            "sources": list(docs_sources | code_sources)
        }
    })
    
    st.markdown("---")
    st.caption(f"⚙️ Routing: {route} | Model: {model_name}")
    st.caption(f"📊 Tokens: {token_count} | Speed: {tokens_per_second:.1f} t/s | Time: {total_time:.2f}s | TTFT: {time_to_first_token:.2f}s")

st.markdown("---")
st.caption("💡 Ask about documentation, code, or how they work together!")

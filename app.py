import streamlit as st
import chromadb
import time
from langchain_community.vectorstores import Chroma
from langchain_ollama import ChatOllama
# from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from dotenv import load_dotenv
load_dotenv()

# --- Initialize Chroma ---
chroma_client = chromadb.PersistentClient(path="./chroma_db")
vectorstore = Chroma(collection_name="devsite_docs", client=chroma_client)
retriever = vectorstore.as_retriever(search_kwargs={"k": 8})

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
# )``

# --- Streamlit page setup ---
st.set_page_config(page_title="DevSite Assistant", page_icon="🤖")
st.title("🤖 DevSite AI Assistant")
st.caption("Ask anything about your internal developer documentation (local + private).")

# --- Initialize chat history in session ---
if "history" not in st.session_state:
    st.session_state["history"] = []

# --- Chat input ---
user_query = st.chat_input("Ask your question...")

# --- Function: retrieve context from Chroma ---
def retrieve_context(query, max_tokens_per_doc=3000):
    docs = retriever.invoke(query)
    context_text = "\n\n".join(d.page_content[:max_tokens_per_doc] for d in docs)
    sources = [d.metadata.get("source", "unknown") for d in docs]
    return context_text, sources

# --- Function: build a context-aware prompt ---
def build_prompt(context, question, chat_history):
    # Include last few exchanges for conversational context
    history_text = "\n".join(
        [f"User: {turn['user']}\nAssistant: {turn['assistant']}" for turn in chat_history[-3:]]
    )

    prompt_template = ChatPromptTemplate.from_template(
        """You are a helpful assistant for developers.
Your knowledge is LIMITED to the documentation context provided below. Do not use any external knowledge.

<context>
{context}
</context>

<chat_history>
{history}
</chat_history>

User question: {question}

Instructions:
- Answer ONLY using information from the context above
- Quote or reference specific parts of the documentation when possible
- If the context contains related information, provide a complete answer
- You may make reasonable inferences based solely on what's in the context
- If the context doesn't contain relevant information, say: "I don't see information about that in the indexed documentation."
- Do not use any knowledge outside of the provided context
"""
    )
    return prompt_template.format(context=context, question=question, history=history_text)

# --- Display previous chat messages ---
for turn in st.session_state["history"]:
    with st.chat_message("user"):
        st.markdown(turn["user"])
    with st.chat_message("assistant"):
        st.markdown(turn["assistant"])

# --- Handle new user question ---
if user_query:
    with st.chat_message("user"):
        st.markdown(user_query)

    with st.spinner("Retrieving relevant documentation..."):
        context, sources = retrieve_context(user_query)

    prompt = build_prompt(context, user_query, st.session_state["history"])

    # --- Stream the response token by token ---
    full_response = ""
    token_count = 0
    start_time = time.time()
    first_token_time = None
    
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        print("\n\n=== CONTEXT SENT TO LLM ===\n")
        print(context[:2000])
        for chunk in llm.stream(prompt):
            if first_token_time is None:
                first_token_time = time.time()
            full_response += chunk.content
            token_count += 1
            message_placeholder.markdown(full_response + "▌")
            time.sleep(0.02)
        message_placeholder.markdown(full_response)
    
    end_time = time.time()
    total_time = end_time - start_time
    time_to_first_token = first_token_time - start_time if first_token_time else 0
    tokens_per_second = token_count / total_time if total_time > 0 else 0

    # --- Save chat to history ---
    st.session_state["history"].append({
        "user": user_query,
        "assistant": full_response
    })

    # --- Show sources used ---
    st.markdown("### 📚 Sources")
    for i, src in enumerate(sources):
        st.markdown(f"**{i+1}.** `{src}`")

st.markdown("---")
st.caption(f"⚙️ Running locally with Ollama + Chroma + LangChain | Model: {model_name}")
if 'token_count' in locals():
    st.caption(f"📊 Tokens: {token_count} | Speed: {tokens_per_second:.1f} t/s | Time: {total_time:.2f}s | TTFT: {time_to_first_token:.2f}s")

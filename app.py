import streamlit as st
import chromadb
import time
from langchain_community.vectorstores import Chroma
# from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from dotenv import load_dotenv
load_dotenv()

# --- Initialize Chroma ---
chroma_client = chromadb.PersistentClient(path="./chroma_db")
vectorstore = Chroma(collection_name="devsite_docs", client=chroma_client)
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

# --- Initialize local LLM ---
# Use a smaller model like "phi3:mini" or "qwen2.5:0.5b" for faster responses
# llm = ChatOllama(model="smollm2")
# llm = ChatOllama(model="phi3:mini")
# llm = ChatOllama(model="steamdj/llama3.1-cpu-only") 
# llm = ChatOllama(model="qwen2.5:0.5b")
llm = ChatOpenAI(
    # model="gpt-4o-mini",   # or "gpt-4o" / "gpt-3.5-turbo"
    model="gpt-4.1-nano",   
    temperature=0,
)

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
def retrieve_context(query, max_tokens_per_doc=2000):
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
Answer the user's question using ONLY the provided documentation context and prior conversation.

<context>
{context}
</context>

<chat_history>
{history}
</chat_history>

User question: {question}

If the answer isn't in the docs, say "I couldn't find that in the docs."
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
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        print("\n\n=== CONTEXT SENT TO LLM ===\n")
        print(context[:2000])
        for chunk in llm.stream(prompt):
            full_response += chunk.content
            message_placeholder.markdown(full_response + "▌")
            time.sleep(0.02)
        message_placeholder.markdown(full_response)

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
st.caption("⚙️ Running locally with Ollama + Chroma + LangChain")

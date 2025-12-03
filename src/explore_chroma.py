import streamlit as st
import chromadb

# --- Connect to local Chroma database ---
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# --- Sidebar: show available collections ---
collections = chroma_client.list_collections()
collection_names = [c.name for c in collections]

if not collections:
    st.warning("No collections found in ChromaDB. Run build_index.py first.")
    st.stop()

selected = st.sidebar.selectbox("Select collection", collection_names)
collection = chroma_client.get_collection(selected)

st.title("🧭 ChromaDB Explorer")
st.caption(f"Exploring collection: **{selected}**")

# --- Info section ---
col1, col2 = st.columns(2)
with col1:
    st.metric("Documents", collection.count())
with col2:
    st.metric("Chroma path", "./chroma_db")

st.divider()

# --- Query interface ---
st.subheader("🔍 Semantic search")
query = st.text_input("Enter a search phrase:")
num_results = st.slider("Number of results", 1, 10, 3)

if query:
    with st.spinner("Searching..."):
        results = collection.query(
            query_texts=[query],
            n_results=num_results,
            include=["documents", "metadatas", "distances"]
        )

    st.write(f"### Results for: *{query}*")
    for i, doc in enumerate(results["documents"][0]):
        st.markdown(f"#### Result {i+1}")
        st.write(f"**Distance:** {results['distances'][0][i]:.4f}")
        st.write(f"**Metadata:** `{results['metadatas'][0][i]}`")
        st.text_area("Content preview", doc[:1500], height=200)
        st.divider()

# --- Browse all documents (limited) ---
st.subheader("📚 Browse stored documents")
limit = st.slider("Show first N documents", 1, 20, 5)

if st.button("Show documents"):
    data = collection.get(include=["documents", "metadatas"], limit=limit)
    for i, doc in enumerate(data["documents"]):
        st.markdown(f"#### Document {i+1}")
        st.write(f"**Metadata:** `{data['metadatas'][i]}`")
        st.text_area("Content preview", doc[:1500], height=200)
        st.divider()

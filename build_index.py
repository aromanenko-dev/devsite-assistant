import os
import re
import chromadb
from langchain_community.document_loaders import DirectoryLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# --- 1. Load all MDX docs ---
print("📚 Loading MDX files...")
loader = DirectoryLoader(
    path="./data",
    glob="**/*.mdx",
    loader_cls=UnstructuredMarkdownLoader,
    show_progress=True
)
docs = loader.load()
print(f"✅ Loaded {len(docs)} documents")

# --- 2. Clean up MDX content (remove JSX/HTML tags safely) ---
def clean_mdx(text):
    # remove jsx/react tags but preserve <T> inside code
    text = re.sub(r"<[^>\n]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

for d in docs:
    d.page_content = clean_mdx(d.page_content)
    # Ensure file path metadata
    d.metadata["source"] = d.metadata.get("source", d.metadata.get("file_path", "unknown"))

# --- 3. Split into smaller text chunks ---
print("✂️ Splitting documents into chunks...")
splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,  # about 600-800 words per chunk
    chunk_overlap=100,
    separators=["\n\n", "\n", ".", "!", "?", " "],
)
chunks = splitter.split_documents(docs)
print(f"✅ Created {len(chunks)} text chunks")

# --- 4. Create embeddings ---
print("🔢 Creating embeddings with BAAI/bge-small-en ...")
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en")

# --- 5. Create or overwrite Chroma collection ---
print("💾 Building Chroma vectorstore...")
persist_dir = "./chroma_db"
if os.path.exists(persist_dir):
    print("⚠️ Removing old Chroma database...")
    import shutil
    shutil.rmtree(persist_dir)

vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    collection_name="devsite_docs",
    persist_directory=persist_dir,
)

vectorstore.persist()
print("✅ Done! Indexed all documentation chunks.")
print(f"📦 Total indexed chunks: {len(chunks)}")

import argparse
import chromadb
import os
import re
import shutil

from langchain_community.document_loaders import DirectoryLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# --- 1. Load all MDX/MD docs ---
print("📚 Loading documentation files...")
parser = argparse.ArgumentParser(description="Build Chroma index from Markdown/MDX files")
parser.add_argument(
    "--path", 
    type=str, 
    nargs="+",
    default=["./data"], 
    help="Path(s) to directory containing Markdown/MDX files (supports multiple paths)"
)
args = parser.parse_args()

# Ensure paths is always a list
paths = args.path if isinstance(args.path, list) else [args.path]

all_docs = []
for path in paths:
    print(f"📂 Loading from: {path}")
    for glob_pattern in ["**/*.mdx", "**/*.md"]:
        loader = DirectoryLoader(
            path=path,
            glob=glob_pattern,
            loader_cls=UnstructuredMarkdownLoader,
            show_progress=True,
            silent_errors=True
        )
        try:
            docs = loader.load()
            all_docs.extend(docs)
            print(f"✅ Loaded {len(docs)} documents from {path}")
        except Exception as e:
            print(f"⚠️ Error loading from {path}: {e}")
            continue

print(f"📚 Total documents loaded: {len(all_docs)}")

# --- 2. Clean up MDX content (remove JSX/HTML tags safely) ---
def clean_mdx(text):
    # remove jsx/react tags but preserve <T> inside code
    text = re.sub(r"<[^>\n]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

for d in all_docs:
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
chunks = splitter.split_documents(all_docs)
print(f"✅ Created {len(chunks)} text chunks")

# --- 4. Create embeddings ---
print("🔢 Creating embeddings with BAAI/bge-small-en ...")
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en")

# --- 5. Create or overwrite Chroma collection ---
print("💾 Building Chroma vectorstore...")
persist_dir = "./chroma_db"
if os.path.exists(persist_dir):
    print("⚠️ Removing old Chroma database...")
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

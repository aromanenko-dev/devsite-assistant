"""
Code Search Agent - Search and analyze code repositories
Indexes source code files with enhanced semantic extraction
"""

import argparse
import chromadb
import os
import shutil
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from code_indexers.enhanced_indexer import EnhancedCodeIndexer

# Code file extensions to index (prioritize Java and XML)
CODE_EXTENSIONS = [
    "*.java",    # Java (priority)
    "*.xml",     # XML (priority)
    "*.py",      # Python
    "*.js",      # JavaScript
    "*.ts",      # TypeScript
    "*.jsx",     # JSX
    "*.tsx",     # TSX
    "*.go",      # Go
    "*.rs",      # Rust
    "*.cpp",     # C++
    "*.c",       # C
    "*.cs",      # C#
    "*.rb",      # Ruby
    "*.php",     # PHP
    "*.sql",     # SQL
]

def load_code_files(paths, exclude_dirs=None):
    """Load source code files with enhanced semantic extraction"""
    print("📝 Loading source code files...")
    
    if exclude_dirs is None:
        exclude_dirs = ["node_modules", "venv", ".venv", "__pycache__", ".git", "dist", "build", "target"]
    
    indexer = EnhancedCodeIndexer()
    all_docs = []
    total_files = 0
    
    for base_path in paths:
        if not os.path.exists(base_path):
            print(f"⚠️ Path not found: {base_path}")
            continue
        
        print(f"📂 Indexing code in: {base_path}")
        
        for root, dirs, files in os.walk(base_path):
            # Exclude directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                file_path = os.path.join(root, file)
                
                # Check if file matches supported extensions
                if not any(Path(file).match(ext) for ext in CODE_EXTENSIONS):
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        code = f.read()
                    
                    if not code.strip():
                        continue
                    
                    # Create enhanced chunks with semantic extraction
                    chunks = indexer.create_enhanced_chunks(file_path, code)
                    
                    all_docs.extend(chunks)
                    total_files += 1
                    
                    if total_files % 10 == 0:
                        print(f"  ✅ Processed {total_files} files ({len(all_docs)} chunks)")
                
                except Exception as e:
                    print(f"  ⚠️ Error processing {file_path}: {e}")
                    continue
    
    print(f"📚 Total files loaded: {total_files}")
    print(f"📦 Total chunks created: {len(all_docs)}")
    return all_docs

def build_code_index(paths, collection_name="devsite_code", exclude_dirs=None):
    """Build a code search index with enhanced semantic extraction"""
    
    # Load code files
    docs = load_code_files(paths, exclude_dirs)
    
    if not docs:
        print("❌ No code files found. Check your paths.")
        return
    
    # Create embeddings
    print("🔢 Creating embeddings with BAAI/bge-small-en...")
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en")
    
    # Build vectorstore
    print("💾 Building code search index...")
    persist_dir = "./chroma_db_code"
    
    if os.path.exists(persist_dir):
        print("⚠️ Removing old code index...")
        shutil.rmtree(persist_dir)
    
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=persist_dir,
    )
    
    vectorstore.persist()
    print("✅ Code search index built successfully!")
    print(f"📦 Total indexed chunks: {len(docs)}")
    print(f"📂 Index saved to: {persist_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build enhanced code search index for source code repositories"
    )
    parser.add_argument(
        "--path",
        type=str,
        nargs="+",
        default=["./"],
        help="Path(s) to source code directories (default: current directory)"
    )
    parser.add_argument(
        "--exclude-dirs",
        type=str,
        nargs="+",
        default=["node_modules", "venv", ".venv", "__pycache__", ".git", "dist", "build", "target"],
        help="Directories to exclude from indexing"
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="devsite_code",
        help="Name of the Chroma collection (default: devsite_code)"
    )
    
    args = parser.parse_args()
    
    # Ensure paths is always a list
    paths = args.path if isinstance(args.path, list) else [args.path]
    
    build_code_index(paths, args.collection, args.exclude_dirs)

"""
Code Search Agent - Search and analyze code repositories
Indexes source code files and provides semantic search with context
"""

import argparse
import chromadb
import os
import re
import shutil
from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Code file extensions to index
CODE_EXTENSIONS = [
    "*.py",      # Python
    "*.js",      # JavaScript
    "*.ts",      # TypeScript
    "*.jsx",     # JSX
    "*.tsx",     # TSX
    "*.java",    # Java
    "*.go",      # Go
    "*.rs",      # Rust
    "*.cpp",     # C++
    "*.c",       # C
    "*.h",       # Header files
    "*.cs",      # C#
    "*.rb",      # Ruby
    "*.php",     # PHP
    "*.sql",     # SQL
    "*.sh",      # Shell scripts
    "*.yaml",    # YAML
    "*.yml",     # YAML
    "*.json",    # JSON
    "*.xml",     # XML
    "*.toml",    # TOML
]

def clean_code(text):
    """Clean code while preserving structure and comments"""
    # Remove very long sequences of whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def extract_code_context(file_path, content):
    """Extract function/class names and context from code"""
    context = {
        "file_path": file_path,
        "functions": [],
        "classes": [],
        "imports": []
    }
    
    # Extract Python functions
    if file_path.endswith('.py'):
        functions = re.findall(r'def\s+(\w+)\s*\(', content)
        context["functions"].extend(functions[:10])  # Limit to 10
        classes = re.findall(r'class\s+(\w+)', content)
        context["classes"].extend(classes[:5])
        imports = re.findall(r'(?:from|import)\s+[\w.]+', content)
        context["imports"].extend(imports[:5])
    
    # Extract JavaScript/TypeScript functions
    elif file_path.endswith(('.js', '.ts', '.jsx', '.tsx')):
        functions = re.findall(r'(?:function|const|let)\s+(\w+)\s*(?:=|:|\()', content)
        context["functions"].extend(functions[:10])
        classes = re.findall(r'class\s+(\w+)', content)
        context["classes"].extend(classes[:5])
    
    return context

def load_code_files(paths):
    """Load source code files from specified paths"""
    print("📝 Loading source code files...")
    
    all_docs = []
    
    for path in paths:
        if not os.path.exists(path):
            print(f"⚠️ Path not found: {path}")
            continue
            
        print(f"📂 Indexing code in: {path}")
        
        # Load each code file type
        for ext_pattern in CODE_EXTENSIONS:
            glob_pattern = f"**/{ext_pattern}"
            
            try:
                loader = DirectoryLoader(
                    path=path,
                    glob=glob_pattern,
                    loader_cls=TextLoader,
                    show_progress=False,
                    silent_errors=True
                )
                docs = loader.load()
                
                if docs:
                    # Add code context to metadata
                    for doc in docs:
                        context = extract_code_context(doc.metadata.get('source', ''), doc.page_content)
                        # Keep only simple metadata types (str, int, float, bool)
                        doc.metadata = {
                            'source': doc.metadata.get('source', ''),
                            'language': Path(doc.metadata.get('source', '')).suffix.lstrip('.'),
                            'num_functions': len(context.get('functions', [])),
                            'num_classes': len(context.get('classes', [])),
                            'num_imports': len(context.get('imports', []))
                        }
                    
                    all_docs.extend(docs)
                    print(f"  ✅ Loaded {len(docs)} {ext_pattern} files")
            except Exception as e:
                # Silently skip errors
                pass
    
    print(f"📚 Total code files loaded: {len(all_docs)}")
    return all_docs

def build_code_index(paths, collection_name="devsite_code"):
    """Build a code search index"""
    
    # Load code files
    docs = load_code_files(paths)
    
    if not docs:
        print("❌ No code files found. Check your paths.")
        return
    
    # Clean code
    print("🧹 Cleaning code...")
    for doc in docs:
        doc.page_content = clean_code(doc.page_content)
    
    # Split into chunks (larger chunks for code)
    print("✂️ Splitting code into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,  # Larger chunks for code context
        chunk_overlap=200,
        separators=["\n\n", "\ndef ", "\nclass ", "\n", " "],
    )
    chunks = splitter.split_documents(docs)
    print(f"✅ Created {len(chunks)} code chunks")
    
    # Create embeddings
    print("🔢 Creating embeddings...")
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en")
    
    # Build vectorstore
    print("💾 Building code search index...")
    persist_dir = "./chroma_db_code"
    
    if os.path.exists(persist_dir):
        print("⚠️ Removing old code index...")
        shutil.rmtree(persist_dir)
    
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=persist_dir,
    )
    
    vectorstore.persist()
    print("✅ Code search index built!")
    print(f"📦 Total indexed code chunks: {len(chunks)}")
    print(f"📂 Index saved to: {persist_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build code search index for source code repositories"
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
        default=["node_modules", "venv", ".venv", "__pycache__", ".git", "dist", "build"],
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
    
    build_code_index(paths, args.collection)

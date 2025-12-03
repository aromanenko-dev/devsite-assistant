"""
Intelligent router that directs queries to either documentation or code search
"""

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

llm = ChatOllama(model="gpt-oss:20b")

ROUTER_PROMPT = ChatPromptTemplate.from_template(
    """You are a query router. Analyze the user's question and determine which knowledge source to use.

Categories:
- DOCS: General information, architecture, principles, guides, how-to, setup, configuration
- CODE: Implementation details, specific functions, classes, bugs, patterns in codebase
- BOTH: Questions that need both documentation context and code examples

Respond with ONLY one word: DOCS, CODE, or BOTH

Examples:
"How do I set up the project?" -> DOCS
"What does the authenticate() function do?" -> CODE
"How is authentication implemented in our system?" -> BOTH
"What are the design principles?" -> DOCS
"Show me the payment processing logic" -> CODE
"Explain the error handling strategy and show examples" -> BOTH

User question: {question}

Response (one word only):"""
)

def route_query(question):
    """Determine if query should go to docs, code, or both"""
    prompt = ROUTER_PROMPT.format(question=question)
    response = llm.invoke(prompt).content.strip().upper()
    
    # Ensure valid response
    if response not in ["DOCS", "CODE", "BOTH"]:
        response = "BOTH"  # Default to both if unclear
    
    return response

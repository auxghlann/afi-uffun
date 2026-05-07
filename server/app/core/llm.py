import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Load environment variables from the .env file
load_dotenv()

def get_operator_llm() -> ChatGroq:
    """Returns a pre-configured ChatGroq LLM instance for the AI operator."""
    
    api_key = os.getenv("GROQ_API_KEY", "")
    
    if not api_key:
        raise ValueError("CRITICAL: GROQ_API_KEY is missing or invalid. Please check your server/.env file.")
        
    return ChatGroq(
        api_key=api_key,
        model="llama-3.3-70b-versatile",
        temperature=0.1
    )

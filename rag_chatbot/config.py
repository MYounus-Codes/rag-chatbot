"""
Configuration module for the Support RAG Chatbot.
Sets up the OpenRouter-based LLM client and model configuration.
"""

import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import OpenAIChatCompletionsModel, set_tracing_disabled

# Load environment variables
load_dotenv()

# Disable tracing since we're not using OpenAI's platform
set_tracing_disabled(True)

# API Keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "support-rag-workflow-chatbot")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")
BASE_URL = os.getenv("BASE_URL", "https://demo-web-ruddy-two.vercel.app")

# Validate required environment variables
def validate_config():
    """Validate that all required environment variables are set."""
    required_vars = {
        "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
        "PINECONE_API_KEY": PINECONE_API_KEY,
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_KEY": SUPABASE_KEY,
    }
    
    missing_vars = [name for name, value in required_vars.items() if not value]
    
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}. "
            "Please check your .env file."
        )


def get_openrouter_client() -> AsyncOpenAI:
    """Create and return an AsyncOpenAI client configured for OpenRouter."""
    return AsyncOpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )


def get_llm_model() -> OpenAIChatCompletionsModel:
    """Create and return the LLM model configured for OpenRouter."""
    external_client = get_openrouter_client()
    
    # Using a free model from OpenRouter
    return OpenAIChatCompletionsModel(
        model="xiaomi/mimo-v2-flash:free",  # Free Gemma model
        openai_client=external_client
    )


# Pre-configured model instance for use across agents
_llm_model = None


def get_model() -> OpenAIChatCompletionsModel:
    """Get or create the singleton LLM model instance."""
    global _llm_model
    if _llm_model is None:
        _llm_model = get_llm_model()
    return _llm_model

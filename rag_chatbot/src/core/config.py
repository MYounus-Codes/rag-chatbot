"""
Configuration module for the AM ROBOTS Support RAG Chatbot.
Handles environment variables, LLM client setup, and validation.
"""

import os
import sys
from typing import Optional, TYPE_CHECKING
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check Python version
if sys.version_info < (3, 12):
    import warnings
    warnings.warn(
        f"Python 3.12+ is recommended. Current version: {sys.version_info.major}.{sys.version_info.minor}",
        RuntimeWarning
    )

# Conditional imports for type checking and runtime
if TYPE_CHECKING:
    from openai import AsyncOpenAI
    from agents import OpenAIChatCompletionsModel


class Config:
    """Centralized configuration management."""
    
    # API Keys
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "support-rag-workflow-chatbot")
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    # SMTP Email
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")
    
    # Application
    BASE_URL: str = os.getenv("BASE_URL", "https://demo-web-ruddy-two.vercel.app")
    PRODUCTS_BASE_PATH: str = os.getenv("PRODUCTS_BASE_PATH", "products")
    
    # LLM Settings
    LLM_MODEL: str = os.getenv("LLM_MODEL", "xiaomi/mimo-v2-flash:free")
    
    @classmethod
    def validate(cls) -> None:
        """Validate that all required environment variables are set."""
        required_vars = {
            "OPENROUTER_API_KEY": cls.OPENROUTER_API_KEY,
            "PINECONE_API_KEY": cls.PINECONE_API_KEY,
            "SUPABASE_URL": cls.SUPABASE_URL,
            "SUPABASE_KEY": cls.SUPABASE_KEY,
        }
        
        missing_vars = [name for name, value in required_vars.items() if not value]
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}. "
                "Please check your .env file."
            )


def get_openrouter_client():
    """Create and return an AsyncOpenAI client configured for OpenRouter."""
    from openai import AsyncOpenAI
    return AsyncOpenAI(
        api_key=Config.OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )


def get_llm_model():
    """Create and return the LLM model configured for OpenRouter."""
    from agents import OpenAIChatCompletionsModel, set_tracing_disabled
    
    # Disable tracing since we're not using OpenAI's platform
    set_tracing_disabled(True)
    
    external_client = get_openrouter_client()
    return OpenAIChatCompletionsModel(
        model=Config.LLM_MODEL,
        openai_client=external_client
    )


# Singleton LLM model instance
_llm_model = None


def get_model():
    """Get or create the singleton LLM model instance."""
    global _llm_model
    if _llm_model is None:
        _llm_model = get_llm_model()
    return _llm_model

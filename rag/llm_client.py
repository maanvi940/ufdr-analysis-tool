"""
LLM Client Factory for UFDR Analysis Tool

Centralizes LLM client creation for:
- Query Engine (RAG)
- Report Generator
- Cross-Case Analyzer

Supports:
- OpenRouter (DeepSeek, etc.)
- Gemini
- OpenAI
"""

import os
import logging
from typing import Optional, Any, Tuple

logger = logging.getLogger(__name__)


def get_llm_client() -> Optional[Tuple[str, Any]]:
    """
    Get configured LLM client for reasoning.
    Returns None if no API key is configured (graceful fallback).
    
    Returns:
        (provider_name, client_object)
    """
    # Try OpenRouter first (if configured)
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if openrouter_key:
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_key,
                default_headers={
                    "HTTP-Referer": "https://github.com/kartikay/ufdr-analysis-tool",
                    "X-Title": "UFDR Analysis Tool",
                },
            )
            logger.info("Using OpenRouter API for reasoning")
            return ("openrouter", client)
        except Exception as e:
            logger.warning(f"OpenRouter setup failed: {e}")

    # Try Gemini next
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            logger.info("Using Gemini API for reasoning")
            return ("gemini", model)
        except Exception as e:
            logger.warning(f"Gemini setup failed: {e}")
    
    # Try OpenAI as fallback
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            logger.info("Using OpenAI API for reasoning")
            return ("openai", client)
        except Exception as e:
            logger.warning(f"OpenAI setup failed: {e}")
    
    logger.info("No LLM API key configured — retrieval-only mode")
    return None

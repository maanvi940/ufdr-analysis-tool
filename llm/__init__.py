"""
LLM Integration Module
Ollama client for Llama 3.1-8B
"""

from llm.ollama_client import OllamaClient, get_ollama_client
from llm.report_generator import ForensicReportGenerator

__all__ = [
    'OllamaClient',
    'get_ollama_client',
    'ForensicReportGenerator'
]

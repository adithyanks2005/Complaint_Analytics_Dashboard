import os
import json
import logging
from typing import Literal

# Placeholder for LLM integration. Replace with actual API calls as needed.

def _mock_priority(text: str) -> Literal["Low", "Medium", "High"]:
    """Simple heuristic priority based on keywords.
    """
    low_keywords = ["minor", "suggestion", "question"]
    high_keywords = ["urgent", "critical", "severe", "pain", "breakdown"]
    text_lower = text.lower()
    if any(k in text_lower for k in high_keywords):
        return "High"
    if any(k in text_lower for k in low_keywords):
        return "Low"
    return "Medium"

def compute_priority(complaint_text: str) -> Literal["Low", "Medium", "High"]:
    """Compute priority for a complaint.

    In production, replace the mock with a call to an LLM service (e.g., OpenAI, Anthropic).
    The function reads environment variable `AI_MODEL` to decide which model to use.
    """
    # Example integration point:
    # model = os.getenv("AI_MODEL")
    # if model == "openai":
    #     ... call OpenAI API ...
    # For now, use mock heuristic.
    return _mock_priority(complaint_text)

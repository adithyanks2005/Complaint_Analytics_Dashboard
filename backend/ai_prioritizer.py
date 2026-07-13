from typing import Literal


def _mock_priority(text: str) -> Literal["Low", "Medium", "High"]:
    """Keyword-based priority heuristic for complaint text."""
    text_lower = text.lower()
    high_keywords = [
        "urgent", "critical", "severe", "emergency", "danger", "hazard",
        "flood", "flooding", "accident", "contamination", "contaminated",
        "sewage", "overflow", "burst", "collapse", "collapsed", "cave-in",
        "blocked drain", "no water", "water cut", "pipeline leak",
    ]
    low_keywords = [
        "minor", "suggestion", "question", "flickering", "small",
        "pothole", "crack", "bins", "not collected", "streetlight",
    ]
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
    return _mock_priority(complaint_text)

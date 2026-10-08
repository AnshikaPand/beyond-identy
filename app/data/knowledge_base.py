"""
Built-in Q&A Knowledge Base for Beyond Identity 24/7 Assistant.

Stores verified Small Talk and Rights & Support questions and answers.
Provides fast token-overlap and fuzzy keyword matching (supporting English and Hinglish)
along with mandatory safety/crisis checks before falling back to any other logic.
"""
import json
import os
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# Try to import rapidfuzz; if not available, gracefully fall back to Python's built-in difflib
try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    import difflib
    HAS_RAPIDFUZZ = False

JSON_DATA_PATH = Path(__file__).resolve().parent / "chatbot_data.json"

CRISIS_SAFETY_ANSWER = (
    "You are not alone. Call Tele-MANAS 14416 (free, 24/7 mental health support). "
    "If you are in immediate danger, call 112."
)

FALLBACK_ANSWER = (
    "Sorry, I don't have a verified answer for that yet. "
    "You can try one of the topics above, or call the helpline for direct help."
)

# Load questions from JSON file
def load_kb_data() -> Dict[str, Any]:
    if JSON_DATA_PATH.exists():
        try:
            with open(JSON_DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"safety_rule": {"triggers": [], "answer": CRISIS_SAFETY_ANSWER}, "fallback": {"answer": FALLBACK_ANSWER}, "questions": []}


KB_DATA = load_kb_data()
QUESTIONS: List[Dict[str, Any]] = KB_DATA.get("questions", [])

CRISIS_KEYWORDS = [
    "suicide",
    "kill myself",
    "harm",
    "self harm",
    "self-harm",
    "abuse",
    "danger",
    "end my life",
    "marna chahta hoon",
    "marna chahti hoon",
    "jaan de dunga",
    "jaan lena",
    "physical abuse",
    "sexual abuse",
    "in danger",
    "unsafe",
    "hanging myself",
    "cut myself",
    "crisis",
    "police violence",
    "physical violence",
    "emergency help",
]


def normalize_text(text: str) -> str:
    """Normalize input text: lowercase, strip punctuation, collapse whitespace."""
    if not text:
        return ""
    t = text.lower().strip()
    # Replace non-alphanumeric characters with space
    t = re.sub(r"[^\w\s]", " ", t)
    # Collapse consecutive spaces
    t = re.sub(r"\s+", " ", t).strip()
    return t


def is_crisis_query(query: str) -> bool:
    """Safety check: Detect distress, self-harm, or immediate physical danger."""
    norm = normalize_text(query)
    if not norm:
        return False

    for kw in CRISIS_KEYWORDS:
        norm_kw = normalize_text(kw)
        if " " in norm_kw:
            if norm_kw in norm:
                return True
        else:
            pattern = r"\b" + re.escape(norm_kw) + r"\b"
            if re.search(pattern, norm):
                return True
    return False


COMMON_STOP_WORDS = {
    "is", "are", "am", "the", "a", "an", "in", "on", "at", "to", "for", "of",
    "with", "and", "or", "what", "how", "tell", "me", "there", "i", "can", "do"
}


def _calculate_trigger_score(norm_query: str, norm_trigger: str) -> float:
    """Calculates match score between normalized query and normalized trigger (0.0 to 1.0)."""
    if not norm_query or not norm_trigger:
        return 0.0

    # 1. Exact match
    if norm_query == norm_trigger:
        return 1.0

    # 2. Whole trigger appears as exact word phrase in query
    pattern = r"\b" + re.escape(norm_trigger) + r"\b"
    if re.search(pattern, norm_query):
        # If trigger is a single common stop-word, do not trigger high score
        if norm_trigger in COMMON_STOP_WORDS:
            return 0.2

        q_tokens = norm_query.split()
        t_tokens = norm_trigger.split()
        ratio = len(t_tokens) / max(len(q_tokens), 1)

        # Domain keywords that are highly specific
        domain_terms = {
            "hrt", "garima", "greh", "nalsa", "ayushman", "15100", "14416", "112",
            "smile", "kaise", "haal", "theek", "udaas", "namaste", "alvida", "bot",
            "accha", "shukriya", "dhanyavaad", "badhiya", "certificate", "fir",
            "shelter", "insurance", "discrimination", "rights"
        }
        if any(tok in domain_terms for tok in t_tokens):
            return min(0.96, 0.82 + (0.15 * ratio))

        return min(0.92, 0.70 + (0.25 * ratio))

    # Reverse: normalized query is contained in trigger (e.g. user types "garima greh" and trigger is "garima greh shelters")
    if len(norm_query) >= 3 and re.search(r"\b" + re.escape(norm_query) + r"\b", norm_trigger):
        if norm_query not in COMMON_STOP_WORDS:
            return 0.88

    # 3. Token sort / overlap
    if HAS_RAPIDFUZZ:
        sort_score = fuzz.token_sort_ratio(norm_query, norm_trigger) / 100.0
        q_toks = set(norm_query.split())
        t_toks = set(norm_trigger.split())
        overlap = len(q_toks & t_toks) / max(len(t_toks), 1)
        if overlap >= 0.7:
            partial = fuzz.partial_ratio(norm_query, norm_trigger) / 100.0
            return max(sort_score, min(0.92, partial * 0.9))
        return sort_score
    else:
        q_toks = set(norm_query.split())
        t_toks = set(norm_trigger.split())
        overlap = len(q_toks & t_toks) / max(len(t_toks), 1)
        seq_ratio = difflib.SequenceMatcher(None, norm_query, norm_trigger).ratio()
        return max(seq_ratio, overlap * 0.85)


def find_best_match(query: str, threshold: float = 0.65) -> Optional[Dict[str, Any]]:
    """
    Finds the best matching item from the knowledge base.
    Returns dictionary with {id, category, question, answer, score, matched_trigger} or None.
    """
    if not query or not query.strip():
        return None

    # Step 0: Check Safety Rule first
    if is_crisis_query(query):
        return {
            "id": "crisis_safety",
            "category": "crisis",
            "question": "Safety & Crisis SOS",
            "answer": CRISIS_SAFETY_ANSWER,
            "score": 1.0,
            "matched_trigger": "safety_rule",
            "is_crisis": True,
        }

    norm_query = normalize_text(query)
    if not norm_query:
        return None

    best_item: Optional[Dict[str, Any]] = None
    best_score = 0.0
    best_trigger = ""

    for item in QUESTIONS:
        triggers = item.get("triggers", [])
        for trigger in triggers:
            norm_trigger = normalize_text(trigger)
            score = _calculate_trigger_score(norm_query, norm_trigger)
            if score > best_score:
                best_score = score
                best_trigger = trigger
                best_item = item

    if best_score >= threshold and best_item is not None:
        return {
            "id": best_item.get("id"),
            "category": best_item.get("category"),
            "question": best_item.get("question"),
            "answer": best_item.get("answer"),
            "score": round(best_score, 3),
            "matched_trigger": best_trigger,
            "is_crisis": False,
        }

    return None


def get_all_knowledge_items() -> List[Dict[str, Any]]:
    """Returns all Q&A items defined in the knowledge base."""
    return QUESTIONS


def answer_query(query: str, threshold: float = 0.65) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Answers a query using the built-in knowledge base.
    Returns (answer_text, match_info).
    If no match above threshold, returns (FALLBACK_ANSWER, None).
    """
    match = find_best_match(query, threshold=threshold)
    if match:
        return match["answer"], match
    return FALLBACK_ANSWER, None

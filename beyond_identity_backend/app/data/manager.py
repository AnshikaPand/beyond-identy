"""
Knowledge Base Manager for Beyond Identity Q&A Repository.
Aggregates modular question domains covering Indian constitutional law,
statutory rights, documentation, workplace equality, housing, and transgender parenting.
"""
import json
from typing import List, Dict, Any, Optional

from app.data.domain1_legal import LEGAL_QA
from app.data.domain2_docs import DOCS_QA
from app.data.domain3_workplace import WORKPLACE_QA
from app.data.domain4_housing import HOUSING_QA
from app.data.domain5_parents import PARENTS_QA

# Combined Master Knowledge Base (Total 220 Q&As)
ALL_QA: List[Dict[str, Any]] = (
    LEGAL_QA + DOCS_QA + WORKPLACE_QA + HOUSING_QA + PARENTS_QA
)


def get_all_qa(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns all Q&A items, optionally filtered by category name."""
    if not category:
        return ALL_QA
    cat_lower = category.strip().lower()
    return [
        qa for qa in ALL_QA
        if cat_lower in qa.get("category", "").lower()
    ]


def get_qa_by_id(qa_id: int) -> Optional[Dict[str, Any]]:
    """Finds a single Q&A item by its integer ID."""
    for qa in ALL_QA:
        if qa.get("id") == qa_id:
            return qa
    return None


def get_categories() -> List[str]:
    """Returns a list of unique category names in the knowledge base."""
    seen = set()
    categories = []
    for qa in ALL_QA:
        cat = qa.get("category")
        if cat and cat not in seen:
            seen.add(cat)
            categories.append(cat)
    return categories


def search_qa(
    query: str,
    category: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Search Q&A items using keyword and token matching across questions,
    answers, applicable laws, and keywords.
    """
    query_lower = query.strip().lower()
    if not query_lower:
        return ALL_QA[:limit]

    terms = [t for t in query_lower.split() if len(t) > 2]
    scored: List[tuple] = []

    candidates = get_all_qa(category=category) if category else ALL_QA

    for item in candidates:
        score = 0
        q_text = item.get("question", "").lower()
        a_text = item.get("answer", "").lower()
        law_text = item.get("applicable_law", "").lower()
        keywords = [k.lower() for k in item.get("keywords", [])]

        # Exact phrase in question
        if query_lower in q_text:
            score += 15

        # Exact phrase in answer
        if query_lower in a_text:
            score += 8

        # Exact keyword match
        for kw in keywords:
            if kw in query_lower or query_lower in kw:
                score += 10
            for term in terms:
                if term in kw:
                    score += 3

        # Term matching
        for term in terms:
            if term in q_text:
                score += 4
            if term in a_text:
                score += 2
            if term in law_text:
                score += 3

        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:limit]]


def export_json(filepath: Optional[str] = None) -> str:
    """Exports all Q&As as a formatted JSON string or saves to a file."""
    json_data = json.dumps(ALL_QA, indent=2, ensure_ascii=False)
    if filepath:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(json_data)
    return json_data

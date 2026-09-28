"""
Beyond Identity 500 Transgender Questions & Answers Knowledge Base.
Modular repository covering Indian legal rights, documentation, healthcare,
workplace, housing, police grievances, mental health, education, and community terminology.
"""
from app.data.manager import (
    get_all_qa,
    search_qa,
    export_json,
    get_qa_by_id,
    get_categories,
    ALL_QA,
)
from app.data.domain1_legal import LEGAL_QA
from app.data.domain2_docs import DOCS_QA
from app.data.domain3_workplace import WORKPLACE_QA
from app.data.domain4_housing import HOUSING_QA
from app.data.domain5_parents import PARENTS_QA

__all__ = [
    "get_all_qa",
    "search_qa",
    "export_json",
    "get_qa_by_id",
    "get_categories",
    "ALL_QA",
    "LEGAL_QA",
    "DOCS_QA",
    "WORKPLACE_QA",
    "HOUSING_QA",
    "PARENTS_QA",
]

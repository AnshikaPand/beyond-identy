import json
from app.data import knowledge_base

queries = [
    "is being gay legal in india?",
    "is homosexuality a crime under section 377?",
    "section 377",
    "can same sex couples marry in india?",
    "can two men get married in india?",
    "same sex relationships",
    "is conversion therapy legal in india?",
    "can doctors cure gay people?",
    "conversion therapy",
    "where can i get prep or pep in india for safe sex?",
    "safe sex for lgbtq",
    "prep and pep",
    "where can i find lgbtq support groups in mumbai or delhi?",
    "humsafar trust",
    "sappho for equality",
]

for q in queries:
    match = knowledge_base.find_best_match(q)
    if match:
        print(f"Query: '{q}' -> ID: {match.get('id')}, Category: {match.get('category')}, Tag: {match.get('tag')}, Score: {match.get('score')}, Trigger: '{match.get('matched_trigger')}'")
    else:
        print(f"Query: '{q}' -> No match")

import json
from pathlib import Path

cb_path = Path("app/data/chatbot_data.json")
intents_path = Path("app/data/intents.json")

# Update chatbot_data.json
with open(cb_path, "r", encoding="utf-8") as f:
    cb_data = json.load(f)

for q in cb_data["questions"]:
    if q["id"] == 35:
        for t in ["can doctors cure gay people", "cure gay", "can doctors cure homosexuality"]:
            if t not in q["triggers"]:
                q["triggers"].append(t)
    elif q["id"] == 36:
        for t in ["where can i get prep or pep in india for safe sex", "prep and pep"]:
            if t not in q["triggers"]:
                q["triggers"].append(t)
    elif q["id"] == 37:
        for t in ["where can i find lgbtq support groups in mumbai or delhi", "sappho for equality", "sappho"]:
            if t not in q["triggers"]:
                q["triggers"].append(t)

# Also update the intents array in cb_data if present
if "intents" in cb_data:
    for intent in cb_data["intents"]:
        tag = intent.get("tag")
        if tag == "conversion_therapy_ban":
            for p in ["can doctors cure gay people", "cure gay"]:
                if p not in intent["patterns"]:
                    intent["patterns"].append(p)
        elif tag == "lgbtq_safe_sex_prep":
            for p in ["where can i get prep or pep in india for safe sex", "prep and pep"]:
                if p not in intent["patterns"]:
                    intent["patterns"].append(p)
        elif tag == "lgbtq_community_groups":
            for p in ["where can i find lgbtq support groups in mumbai or delhi", "sappho for equality", "sappho"]:
                if p not in intent["patterns"]:
                    intent["patterns"].append(p)

with open(cb_path, "w", encoding="utf-8") as f:
    json.dump(cb_data, f, indent=2, ensure_ascii=False)
print("Updated chatbot_data.json")

# Update intents.json
with open(intents_path, "r", encoding="utf-8") as f:
    intents_data = json.load(f)

for intent in intents_data.get("intents", []):
    tag = intent.get("tag")
    if tag == "conversion_therapy_ban":
        for p in ["can doctors cure gay people", "cure gay"]:
            if p not in intent["patterns"]:
                intent["patterns"].append(p)
    elif tag == "lgbtq_safe_sex_prep":
        for p in ["where can i get prep or pep in india for safe sex", "prep and pep"]:
            if p not in intent["patterns"]:
                intent["patterns"].append(p)
    elif tag == "lgbtq_community_groups":
        for p in ["where can i find lgbtq support groups in mumbai or delhi", "sappho for equality", "sappho"]:
            if p not in intent["patterns"]:
                intent["patterns"].append(p)

with open(intents_path, "w", encoding="utf-8") as f:
    json.dump(intents_data, f, indent=2, ensure_ascii=False)
print("Updated intents.json")

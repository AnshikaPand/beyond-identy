"""
Unit tests for the Beyond Identity Chatbot Router and Service.
Tests intent detection, live database listing retrieval, legal Q&A matching,
crisis SOS responses, and prompt recommendations.
"""
import re
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_chatbot_prompts_endpoint():
    response = client.get("/chatbot/prompts")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert len(data["categories"]) >= 4
    categories = [c["id"] for c in data["categories"]]
    assert "jobs" in categories
    assert "healthcare" in categories
    assert "crisis" in categories


def test_chatbot_stats_endpoint():
    response = client.get("/chatbot/stats")
    assert response.status_code == 200
    data = response.json()
    assert "verified_listings" in data
    assert "legal_qa_items" in data
    assert data["emergency_helpline"] == "868989330"


def test_chatbot_emergency_crisis_query():
    payload = {
        "query": "I am in crisis and facing police violence, I need immediate emergency help",
        "history": [],
    }
    response = client.post("/chatbot/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "emergency_crisis"
    assert "868989330" in data["reply"]
    assert "14416" in data["reply"]
    assert "15100" in data["reply"]
    assert len(data["suggested_prompts"]) > 0


def test_chatbot_employment_query():
    payload = {
        "query": "Find me trans-inclusive jobs or customer support roles in Mumbai",
        "history": [],
    }
    response = client.post("/chatbot/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "employment"
    assert "Section 9" in data["reply"] or "workplace" in data["reply"].lower()
    assert isinstance(data["suggestions"], list)


def test_chatbot_housing_query():
    payload = {
        "query": "My landlord is trying to evict me because I am transgender. Where can I find safe housing or Garima Greh?",
        "history": [],
    }
    response = client.post("/chatbot/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "housing"
    assert "Garima Greh" in data["reply"]
    assert "Section 12" in data["reply"]


def test_chatbot_healthcare_query():
    payload = {
        "query": "What are the safe guidelines for HRT and gender affirmation surgery coverage?",
        "history": [],
    }
    response = client.post("/chatbot/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "healthcare"
    assert "Ayushman Bharat" in data["reply"] or "WPATH" in data["reply"]


def test_chatbot_legal_rights_query():
    payload = {
        "query": "Can transgender parents adopt a child under CARA regulations in India?",
        "history": [],
    }
    response = client.post("/chatbot/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "legal_rights"
    assert "NALSA" in data["reply"] or "15100" in data["reply"]


def test_chatbot_empty_query_validation():
    response = client.post("/chatbot/query", json={"query": "   "})
    assert response.status_code == 400
    assert "Query cannot be empty" in response.json()["detail"]


def test_chatbot_chitchat_what_are_you_doing():
    for q in ["hii what are you doing", "what are you doing?", "what r u doing", "wyd"]:
        response = client.post("/chatbot/query", json={"query": q})
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "chitchat_doing"
        assert "doing great" in data["reply"].lower() or "beyond identity" in data["reply"].lower()


def test_chatbot_chitchat_greeting():
    for q in ["hii", "hello", "hey there", "namaste"]:
        response = client.post("/chatbot/query", json={"query": q})
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "chitchat_greeting"
        assert "Namaste! Welcome to Beyond Identity" in data["reply"]
        assert len(data["suggested_prompts"]) == 0


def test_chatbot_chitchat_how_are_you():
    for q in ["how are you doing today", "how are you", "hello how are you"]:
        response = client.post("/chatbot/query", json={"query": q})
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "chitchat_howareyou"
        assert "doing well, thank you" in data["reply"].lower()


def test_chatbot_chitchat_user_good():
    for q in ["I am fine", "I'm good", "doing well", "all good"]:
        response = client.post("/chatbot/query", json={"query": q})
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "chitchat_user_good"
        assert "great to hear" in data["reply"].lower() or "glad to hear" in data["reply"].lower()


def test_chatbot_unclear_query():
    for q in ["?", "???", "..."]:
        response = client.post("/chatbot/query", json={"query": q})
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "unclear"
        assert "clarify" in data["reply"].lower()


def test_chatbot_family_coming_out():
    for q in ["how do I tell my family", "coming out to parents"]:
        response = client.post("/chatbot/query", json={"query": q})
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "family_coming_out"
        assert "coming out" in data["reply"].lower()
        # Verify length is short (2-4 sentences)
        sentences = [s.strip() for s in data["reply"].split(".") if s.strip()]
        assert 1 <= len(sentences) <= 4


def test_chatbot_confused_need_help():
    for q in ["I'm confused", "I need help"]:
        response = client.post("/chatbot/query", json={"query": q})
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "confused_need_help"
        assert "confused" in data["reply"].lower()
        sentences = [s.strip() for s in data["reply"].split(".") if s.strip()]
        assert 1 <= len(sentences) <= 4


def test_chatbot_out_of_scope_query():
    for q in ["What is the capital of France?", "Write python code to reverse a string", "How to bake a cake?"]:
        response = client.post("/chatbot/query", json={"query": q})
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "out_of_scope"
        assert "verified answer" in data["reply"].lower() or "helpline" in data["reply"].lower()


def test_chatbot_basics_and_terminology():
    response = client.post("/chatbot/query", json={"query": "What does transgender mean?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "basics_terminology"
    assert "gender identity" in data["reply"].lower()
    sentences = [s.strip() for s in data["reply"].split(".") if s.strip()]
    assert 1 <= len(sentences) <= 4


def test_chatbot_support_and_ally():
    response = client.post("/chatbot/query", json={"query": "How can I be a good ally to trans people?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "support_and_ally"
    assert "ally" in data["reply"].lower() or "pronouns" in data["reply"].lower()
    sentences = [s.strip() for s in data["reply"].split(".") if s.strip()]
    assert 1 <= len(sentences) <= 4


def test_chatbot_menu_options_navigation():
    options_map = {
        "1": "employment",
        "option 1": "employment",
        "2": "housing",
        "option 2": "housing",
        "3": "healthcare",
        "option 3": "healthcare",
        "4": "legal_rights",
        "option 4": "legal_rights",
        "5": "emergency_crisis",
        "option 5": "emergency_crisis",
    }
    for q, expected_intent in options_map.items():
        response = client.post("/chatbot/query", json={"query": q})
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == expected_intent


def test_chatbot_chitchat_identity():
    response = client.post("/chatbot/query", json={"query": "who are you and what can you do?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "chitchat_identity"
    assert "Beyond Identity 24/7 Assistant" in data["reply"]


def test_chatbot_chitchat_thanks():
    response = client.post("/chatbot/query", json={"query": "thank you so much for your help!"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "chitchat_thanks"
    assert "welcome" in data["reply"].lower()


def test_chatbot_government_schemes_query():
    for q in [
        "What government schemes and scholarships are available for transgender persons?",
        "Tell me about SMILE scheme and welfare benefits",
        "How do I apply for government scholarships as a trans student?",
    ]:
        response = client.post("/chatbot/query", json={"query": q})
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "scholarship_schemes"
        assert "SMILE" in data["reply"] or "transgender.dosje.gov.in" in data["reply"]
        clean_text = re.sub(r"https?://\S+|www\.\S+|\b\w+\.\w+\.\w+(\.\w+)?\b", "", data["reply"])
        sentences = [s.strip() for s in clean_text.split(".") if s.strip()]
        assert 1 <= len(sentences) <= 4
        # Suggestions should include verified schemes from the database
        assert isinstance(data["suggestions"], list)




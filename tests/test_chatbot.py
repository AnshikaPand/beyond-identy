"""
Unit tests for the Beyond Identity AI Chatbot Router and Service.
Tests intent detection, live database listing retrieval, legal Q&A matching,
crisis SOS responses, and prompt recommendations.
"""
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
        assert len(data["suggested_prompts"]) > 0


def test_chatbot_chitchat_greeting():
    for q in ["hii", "hello", "hey there", "namaste"]:
        response = client.post("/chatbot/query", json={"query": q})
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "chitchat_greeting"
        assert len(data["suggested_prompts"]) > 0


def test_chatbot_chitchat_how_are_you():
    response = client.post("/chatbot/query", json={"query": "how are you doing today"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "chitchat_howareyou"
    assert "wonderful" in data["reply"].lower() or "doing" in data["reply"].lower()


def test_chatbot_chitchat_identity():
    response = client.post("/chatbot/query", json={"query": "who are you and what can you do?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "chitchat_identity"
    assert "Beyond Identity AI" in data["reply"]


def test_chatbot_chitchat_thanks():
    response = client.post("/chatbot/query", json={"query": "thank you so much for your help!"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "chitchat_thanks"
    assert "welcome" in data["reply"].lower()


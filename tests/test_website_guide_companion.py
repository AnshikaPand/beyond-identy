"""
Comprehensive test suite for Beyond Identity Website Guide and Emotional Support Companion.
Tests:
1. Website Guide factual Q&A (purpose, mission, learning paths, features).
2. Community Interview catalog and verified spotlights (Chitra Palekar, Dr. Trinetra, Aryan Pasha, Gauri Sawant).
3. Safe handling of unverified interviews (no hallucinations).
4. Empathetic counselling-style conversations (feeling different, fear of judgment, loneliness, family worries, shame, social acceptance).
5. Grounding reassurance in real website video interviews.
6. Multi-turn conversational memory and context continuity.
7. Safety boundaries (not a disease, crisis helplines, emergency assistance).
8. Bilingual support (English and Hindi).
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# =======================================================================
# 1. Website Guide Factual Q&A Tests
# =======================================================================
def test_website_guide_what_is_beyond_identity():
    response = client.post("/chatbot/query", json={"query": "What is Beyond Identity?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "website_guide_purpose"
    assert "Beyond Identity" in data["reply"]
    assert "transgender" in data["reply"].lower()
    assert "#tab-videos" in data["reply"]
    assert "#tab-listings" in data["reply"]
    assert "#tab-awareness" in data["reply"]
    assert len(data["suggested_interviews"]) > 0


def test_website_guide_purpose():
    response = client.post("/chatbot/query", json={"query": "What is the purpose of this website?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "website_guide_purpose"
    assert "empower" in data["reply"].lower() or "mission" in data["reply"].lower()


def test_website_guide_what_can_i_learn():
    response = client.post("/chatbot/query", json={"query": "What can I learn from this platform?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "website_guide_learning"
    assert "NALSA" in data["reply"] or "rights" in data["reply"].lower()
    assert "interviews" in data["reply"].lower()
    assert len(data["suggested_prompts"]) > 0


def test_website_guide_how_many_interviews():
    response = client.post("/chatbot/query", json={"query": "How many interviews are available?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "website_guide_interviews_count"
    assert "13" in data["reply"]
    assert "Gauri Sawant" in data["reply"]
    assert "Dr. Trinetra" in data["reply"] or "Trinetra" in data["reply"]
    assert "Aryan Pasha" in data["reply"]
    assert len(data["suggested_interviews"]) >= 2


# =======================================================================
# 2. Specific Real Community Interview Spotlight Tests
# =======================================================================
def test_interview_spotlight_chitra_palekar():
    response = client.post("/chatbot/query", json={"query": "What does Chitra Palekar's interview explain?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "interview_spotlight"
    assert "Chitra Palekar" in data["reply"]
    assert "Acceptance begins at home" in data["reply"]
    assert "#tab-videos" in data["reply"]
    assert len(data["suggested_interviews"]) == 1
    assert data["suggested_interviews"][0]["interviewee_name"] == "Chitra Palekar"


def test_interview_spotlight_dr_trinetra():
    response = client.post("/chatbot/query", json={"query": "Tell me about Dr Trinetra's interview"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "interview_spotlight"
    assert "Trinetra" in data["reply"]
    assert "transition" in data["reply"].lower()
    assert len(data["suggested_interviews"]) == 1
    assert "Trinetra" in data["suggested_interviews"][0]["interviewee_name"]


def test_interview_spotlight_aryan_pasha():
    response = client.post("/chatbot/query", json={"query": "What does Aryan Pasha share in his interview?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "interview_spotlight"
    assert "Aryan Pasha" in data["reply"]
    assert "barbell" in data["reply"].lower() or "sports" in data["reply"].lower() or "musclemania" in data["reply"].lower()


def test_interview_simple_words_explanation():
    response = client.post("/chatbot/query", json={"query": "Can you explain Gauri Sawant's experience in simple words?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "interview_simple_explanation"
    assert "Gauri Sawant" in data["reply"]
    assert "Motherhood" in data["reply"] or "shelter" in data["reply"].lower() or "garima greh" in data["reply"].lower()


def test_unverified_interview_safety():
    response = client.post("/chatbot/query", json={"query": "What does Elon Musk's interview explain on Beyond Identity?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "interview_unverified"
    assert "could not find an interview" in data["reply"].lower()
    assert "13 verified" in data["reply"]
    assert "#tab-videos" in data["reply"]
    assert len(data["suggested_interviews"]) == 0


# =======================================================================
# 3. Emotional Support & Counselling-Style Protocol Tests
# =======================================================================
def test_emotional_feeling_different():
    response = client.post("/chatbot/query", json={"query": "I feel different from everyone else. Why am I like this?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "emotional_feeling_different"
    # 7-step empathetic protocol: non-judgmental validation & dignity reassurance
    assert "nothing broken" in data["reply"].lower() or "nothing shameful" in data["reply"].lower()
    # Grounded in real website interview Journey
    assert "Journey" in data["reply"]
    assert "Freedom is the courage" in data["reply"]
    assert len(data["suggested_interviews"]) > 0


def test_emotional_afraid_of_judgment():
    response = client.post("/chatbot/query", json={"query": "I'm afraid people will judge me because I am different."})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "emotional_afraid_of_judgment"
    assert "judge" in data["reply"].lower()
    assert "worth" in data["reply"].lower() or "dignity" in data["reply"].lower()
    # Grounded in Aarohi Sen's interview
    assert "Aarohi Sen" in data["reply"]
    assert len(data["suggested_interviews"]) > 0


def test_emotional_feeling_alone():
    response = client.post("/chatbot/query", json={"query": "I feel alone and nobody understands me"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "emotional_feeling_alone"
    assert "not alone" in data["reply"].lower()
    assert "Gauri Sawant" in data["reply"]
    assert "14416" in data["reply"]
    assert "868989330" in data["reply"]


def test_emotional_family_acceptance_worries():
    response = client.post("/chatbot/query", json={"query": "What will my family think? Will my parents accept me?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "emotional_family_acceptance"
    assert "safety" in data["reply"].lower()
    # Reassurance grounded in Chitra Palekar's interview
    assert "Chitra Palekar" in data["reply"]
    assert "Acceptance begins at home" in data["reply"]


def test_emotional_shame_or_embarrassment():
    response = client.post("/chatbot/query", json={"query": "I feel embarrassed about my identity"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "emotional_shame_embarrassment"
    assert "zero reason for shame" in data["reply"].lower() or "no reason for shame" in data["reply"].lower() or "nothing shameful" in data["reply"].lower()
    assert "Dr. Prasad Raj Dandekar" in data["reply"] or "minority stress" in data["reply"].lower()


def test_emotional_social_acceptance():
    response = client.post("/chatbot/query", json={"query": "Will people ever accept me?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "emotional_social_acceptance"
    assert any(term in data["reply"] for term in ["Anwesa & Megha", "Aryan Pasha", "communities"])
    assert len(data["suggested_interviews"]) > 0


def test_emotional_interview_relatability():
    response = client.post("/chatbot/query", json={"query": "I watched an interview and realized that someone has experiences similar to mine"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "emotional_interview_relatability"
    assert "resonated" in data["reply"].lower() or "similar" in data["reply"].lower() or "which interview" in data["reply"].lower()


def test_emotional_dont_know_whom_to_talk_to():
    response = client.post("/chatbot/query", json={"query": "I don't know whom to talk to"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "emotional_seeking_someone_to_talk_to"
    assert "14416" in data["reply"]
    assert "868989330" in data["reply"]


# =======================================================================
# 4. Multi-Turn Context Continuity Tests
# =======================================================================
def test_multiturn_friends_rejection_followup():
    history = [
        {"role": "user", "content": "I feel different from everyone"},
        {"role": "assistant", "content": "It can feel deeply isolating when you feel different from everyone else..."},
    ]
    response = client.post("/chatbot/query", json={
        "query": "I'm afraid my friends will reject me",
        "history": history
    })
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "multiturn_friends_rejection"
    # Acknowledges prior feeling different context
    assert "feeling different" in data["reply"].lower()
    assert "friends" in data["reply"].lower()


def test_multiturn_family_eviction_followup():
    history = [
        {"role": "user", "content": "What will my family think?"},
        {"role": "assistant", "content": "Worrying about what your family will think is deeply emotional..."},
    ]
    response = client.post("/chatbot/query", json={
        "query": "What if they kick me out of the house?",
        "history": history
    })
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "multiturn_family_eviction"
    assert "family" in data["reply"].lower()
    assert "Section 12" in data["reply"]
    assert "Garima Greh" in data["reply"]


# =======================================================================
# 5. Safety & Truth Boundaries Tests
# =======================================================================
def test_transgender_not_a_disease():
    response = client.post("/chatbot/query", json={"query": "Is being transgender a disease?"})
    assert response.status_code == 200
    data = response.json()
    assert "not an illness" in data["reply"].lower() or "not a disease" in data["reply"].lower() or "not a mental" in data["reply"].lower()


def test_how_can_i_support_someone():
    response = client.post("/chatbot/query", json={"query": "How can I support someone who is transgender?"})
    assert response.status_code == 200
    data = response.json()
    assert "pronouns" in data["reply"].lower()


# =======================================================================
# 6. Bilingual Support Tests (Hindi)
# =======================================================================
def test_hindi_website_guide():
    response = client.post("/chatbot/query", json={
        "query": "Beyond Identity website ke baare me batao",
        "language": "hi"
    })
    assert response.status_code == 200
    data = response.json()
    assert "Beyond Identity" in data["reply"]
    assert "सशक्तिकरण" in data["reply"] or "साक्षात्कार" in data["reply"]


def test_hindi_feeling_different_support():
    response = client.post("/chatbot/query", json={
        "query": "mujhe sabse alag lagta hai, main aisa kyu hu",
        "language": "hi"
    })
    assert response.status_code == 200
    data = response.json()
    assert "Journey" in data["reply"]
    assert "सम्मान" in data["reply"] or "गरिमा" in data["reply"] or "गलत नहीं" in data["reply"]

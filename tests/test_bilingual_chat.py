"""
Tests for Bilingual (English & Hindi) Chatbot and Family/LGBTQ+ Supportive Queries.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_family_transgender_questions_english():
    # 1. Did we do something wrong?
    res1 = client.post("/chatbot/query", json={
        "query": "My child is transgender, did we do something wrong?",
        "language": "en"
    })
    assert res1.status_code == 200
    data1 = res1.json()
    assert "You did nothing wrong" in data1["reply"]

    # 2. Is it an illness?
    res2 = client.post("/chatbot/query", json={
        "query": "Is it a disease?",
        "language": "en"
    })
    assert res2.status_code == 200
    data2 = res2.json()
    assert "not an illness" in data2["reply"].lower()

    # 3. How to support them?
    res3 = client.post("/chatbot/query", json={
        "query": "How can we support them?",
        "language": "en"
    })
    assert res3.status_code == 200
    data3 = res3.json()
    assert "chosen name and pronouns" in data3["reply"].lower()


def test_family_transgender_questions_hindi():
    # 1. क्या हमसे कुछ गलत हुआ?
    res1 = client.post("/chatbot/query", json={
        "query": "mera bachcha transgender hai, humne kya galat kiya",
        "language": "hi"
    })
    assert res1.status_code == 200
    data1 = res1.json()
    assert "आपसे कुछ गलत नहीं हुआ" in data1["reply"]

    # 2. क्या ये बीमारी है?
    res2 = client.post("/chatbot/query", json={
        "query": "kya ye bimari hai",
        "language": "hi"
    })
    assert res2.status_code == 200
    data2 = res2.json()
    assert "बीमारी नहीं है" in data2["reply"]

    # 3. हम कैसे सपोर्ट करें?
    res3 = client.post("/chatbot/query", json={
        "query": "hum kaise support karein",
        "language": "hi"
    })
    assert res3.status_code == 200
    data3 = res3.json()
    assert "चुना हुआ नाम और pronouns" in data3["reply"]


def test_identity_lgbtq_loving_validation():
    # 1. I am gay (English)
    res_en = client.post("/chatbot/query", json={"query": "I am gay", "language": "en"})
    assert res_en.status_code == 200
    assert "Thank you for telling me" in res_en.json()["reply"]

    # 2. I am gay (Hindi)
    res_hi = client.post("/chatbot/query", json={"query": "main gay hu", "language": "hi"})
    assert res_hi.status_code == 200
    assert "मुझे बताने के लिए शुक्रिया" in res_hi.json()["reply"]

    # 3. I am bisexual (English & Hindi)
    res_bi_en = client.post("/chatbot/query", json={"query": "I am bisexual", "language": "en"})
    assert res_bi_en.status_code == 200
    assert "Your identity is real and valid" in res_bi_en.json()["reply"]

    # 4. Scared & Confused
    res_scared = client.post("/chatbot/query", json={"query": "I am scared", "language": "en"})
    assert res_scared.status_code == 200
    assert "14416" in res_scared.json()["reply"]


def test_language_mismatch_switch_prompt():
    # User selected English, but types in Hindi
    res1 = client.post("/chatbot/query", json={
        "query": "mera bachcha transgender hai, kya ye bimari hai",
        "language": "en"
    })
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["language_switch_prompt"] is not None
    assert "Switch to हिंदी" in data1["language_switch_prompt"]

    # User selected Hindi, but types in English
    res2 = client.post("/chatbot/query", json={
        "query": "I am confused about my identity",
        "language": "hi"
    })
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["language_switch_prompt"] is not None
    assert "switch to english" in data2["language_switch_prompt"].lower()

"""
Unit tests for the Built-in Q&A Knowledge Base.
Tests English and Hinglish triggers, fuzzy matching, safety rule, and fallback.
"""
import pytest
from app.data import knowledge_base


def test_small_talk_exact_and_hinglish():
    # 1. Greetings
    for q in ["hi", "hello", "namaste", "hey"]:
        ans, match = knowledge_base.answer_query(q)
        assert match is not None
        assert match["id"] == 1
        assert "Namaste! Welcome to Beyond Identity" in ans

    # 2. How are you / Hinglish
    for q in ["how are you", "kaise ho", "kya haal hai"]:
        ans, match = knowledge_base.answer_query(q)
        assert match is not None
        assert match["id"] == 2
        assert "doing well, thank you" in ans.lower()

    # 3. I am fine / Hinglish
    for q in ["i am fine", "i'm good", "main theek hoon", "sab badhiya"]:
        ans, match = knowledge_base.answer_query(q)
        assert match is not None
        assert match["id"] == 3
        assert "great to hear" in ans.lower()

    # 4. Feeling sad / Hinglish
    for q in ["i am not fine", "i'm sad", "mood kharab hai", "main theek nahi hoon"]:
        ans, match = knowledge_base.answer_query(q)
        assert match is not None
        assert match["id"] == 4
        assert "14416" in ans

    # 5. Who are you / Hinglish
    for q in ["who are you", "what is your name", "tum kaun ho"]:
        ans, match = knowledge_base.answer_query(q)
        assert match is not None
        assert match["id"] == 5
        assert "Beyond Identity 24/7 Assistant" in ans

    # 6. What can you do / Hinglish
    for q in ["what can you do", "help", "tum kya kar sakte ho"]:
        ans, match = knowledge_base.answer_query(q)
        assert match is not None
        assert match["id"] == 6
        assert "guide you on legal rights" in ans.lower()

    # 7. Thank you / Hinglish
    for q in ["thanks", "thank you", "shukriya", "dhanyavaad"]:
        ans, match = knowledge_base.answer_query(q)
        assert match is not None
        assert match["id"] == 7
        assert "most welcome" in ans.lower()

    # 8. Good morning / time greeting
    for q in ["good morning", "good day"]:
        ans, match = knowledge_base.answer_query(q)
        assert match is not None
        assert match["id"] == 8
        assert "Good morning" in ans

    # 9. Bye / Hinglish
    for q in ["bye", "see you", "alvida"]:
        ans, match = knowledge_base.answer_query(q)
        assert match is not None
        assert match["id"] == 9
        assert "Take care" in ans

    # 10. Are you human / Hinglish
    for q in ["are you human", "are you a bot", "tum insaan ho"]:
        ans, match = knowledge_base.answer_query(q)
        assert match is not None
        assert match["id"] == 10
        assert "AI assistant" in ans

    # 11. Ok / Hinglish
    for q in ["ok", "okay", "accha", "thik hai"]:
        ans, match = knowledge_base.answer_query(q)
        assert match is not None
        assert match["id"] == 11
        assert "Alright" in ans


def test_rights_and_support_questions():
    # 12. Rights in India
    ans, match = knowledge_base.answer_query("What rights do transgender persons have in India?")
    assert match is not None
    assert match["id"] == 12
    assert "Transgender Persons (Protection of Rights) Act, 2019" in ans
    assert "NALSA" in ans

    # 13. Certificate / ID
    ans, match = knowledge_base.answer_query("How do I get a Transgender Certificate / ID?")
    assert match is not None
    assert match["id"] == 13
    assert "transgender.dosje.gov.in" in ans
    assert "District Magistrate" in ans

    # 14. Discrimination at work
    ans, match = knowledge_base.answer_query("What can I do if I face discrimination at work?")
    assert match is not None
    assert match["id"] == 14
    assert "Complaint Officer" in ans

    # 15. Report discrimination or violence
    ans, match = knowledge_base.answer_query("How do I report discrimination or violence?")
    assert match is not None
    assert match["id"] == 15
    assert "Report Discrimination tab" in ans
    assert "112" in ans

    # 16. Free legal help
    ans, match = knowledge_base.answer_query("Where can I get free legal help?")
    assert match is not None
    assert match["id"] == 16
    assert "15100" in ans
    assert "NALSA" in ans

    # 17. Shelter / Garima Greh
    ans, match = knowledge_base.answer_query("Is there shelter or housing support?")
    assert match is not None
    assert match["id"] == 17
    assert "Garima Greh" in ans
    assert "SMILE scheme" in ans

    # 18. Health insurance / Ayushman Bharat
    ans, match = knowledge_base.answer_query("Is there health insurance for transgender persons?")
    assert match is not None
    assert match["id"] == 18
    assert "Ayushman Bharat TG Plus" in ans
    assert "5 lakh" in ans

    # 19. HRT
    ans, match = knowledge_base.answer_query("Tell me about HRT.")
    assert match is not None
    assert match["id"] == 19
    assert "endocrinologist" in ans
    assert "self-medicate" in ans

    # 20. Government schemes
    ans, match = knowledge_base.answer_query("What government schemes are available?")
    assert match is not None
    assert match["id"] == 20
    assert "SMILE scheme" in ans

    # 21. Feeling low or unsafe
    ans, match = knowledge_base.answer_query("I'm feeling very low or unsafe.")
    assert match is not None
    assert "Tele-MANAS 14416" in ans
    assert "112" in ans


def test_safety_rule_crisis_triggers():
    crisis_queries = [
        "I want to kill myself",
        "thinking of suicide",
        "want to end my life",
        "harm myself tonight",
        "I am facing severe physical abuse and danger",
    ]
    for q in crisis_queries:
        ans, match = knowledge_base.answer_query(q)
        assert match is not None
        assert match["id"] == "crisis_safety"
        assert "Tele-MANAS 14416" in ans
        assert "112" in ans


def test_fallback_unrecognized_query():
    unrecognized_queries = [
        "What is the population of Tokyo?",
        "How to bake a chocolate cake at home?",
        "Write a quicksort algorithm in C++",
    ]
    for q in unrecognized_queries:
        ans, match = knowledge_base.answer_query(q)
        assert match is None
        assert "Sorry, I don't have a verified answer for that yet" in ans
        assert "helpline" in ans

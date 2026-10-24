"""
Chatbot Service for Beyond Identity.
Provides an intelligent, empathetic 24/7 conversational assistant with:
- Natural Language Intent Detection (Crisis/Emergency, Jobs, Housing, Healthcare, Legal Rights, Welfare Schemes, Incident Redressal)
- Live Database Search over verified listings (Employment, Housing, Healthcare, Schemes, Scholarships)
- 220+ Legal Q&A & Statutory Knowledge Engine integration
- Emergency Crisis Triage (Helpline: 868989330, Tele-MANAS: 14416, NALSA: 15100, 112)
- Optional Anthropic Claude 3.5 Sonnet integration when ANTHROPIC_API_KEY is configured
"""
import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app import models, schemas
from app.data import search_qa, get_all_qa
from app.services.awareness import AWARENESS_TOPICS


def clean_markdown_for_speech(text: str) -> str:
    """Strip markdown symbols and emoji numbers for smooth audio text-to-speech output."""
    clean = re.sub(r"[1-9]️⃣", " ", text)
    clean = re.sub(r"(\*\*|\*|###|##|#|`|\[|\]|\(.*?\))", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _matches_any(keywords: List[str], text: str) -> bool:
    """Matches any keyword in text using word boundaries where appropriate."""
    for k in keywords:
        pattern = r"\b" + re.escape(k) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


CHATBOT_SYSTEM_PROMPT = """You are the chatbot for "Beyond Identity", a website that gives verified information and support related to transgender and LGBTQIA+ identity, rights, and support.

MOST IMPORTANT RULE — STOP AFTER EVERY REPLY
- Respond to only the user's current message, in 2-4 short sentences maximum.
- After your reply, STOP completely. Do not add follow-up information, extra tips, or guess what they'll ask next.
- Never send more than one message in a row. Wait for the user to type again before saying anything else.
- Do not repeat or summarize what you already said in earlier messages.

GREETING
- If the user says "hi" / "hello", reply exactly in this style:
  "Hi! I'm Beyond Identity — a website where you get verified, trustworthy information about transgender and LGBTQIA+ identity, rights, and support."
- Then STOP. Do not ask a question yet, do not explain more. Wait for the user's next message.

HANDLING QUESTIONS
- When the user asks for help (e.g. "I am gay", "I need help", "I'm confused", "how do I tell my family"), give a short, warm, practical reply — about 2 to 4 sentences, or at most 2-3 short points.
- Keep it specific to what they asked. Do not give a long lecture.
- End your reply there and wait. Do not keep adding "also you could..." after your own answer.

TONE
- Warm, respectful, affirmative, non-judgmental. Use the name/pronouns the user gives.
- Simple, plain language — avoid long paragraphs.
- For medical or legal questions, give general guidance only and suggest a qualified doctor or lawyer for anything specific.

SAFETY
- If the user sounds distressed or unsafe, respond gently, encourage them to reach out to someone they trust or a local helpline, then stop and wait — do not lecture.

SCOPE
- Answer questions about transgender and LGBTQIA+ identities (Gay, Lesbian, Bisexual, Transgender, Queer, Intersex, Asexual), rights in India (Section 377, NALSA, TG Persons Act), healthcare basics, coming out, community groups, family/workplace support, and being an ally.
- For completely unrelated topics (sports, weather, coding, etc.), politely say this chat is focused on LGBTQIA+ and transgender-related support.
"""


def detect_intent(query: str) -> str:
    """Detect conversational intent conforming to Beyond Identity chatbot rules."""
    q = query.strip().lower()

    # 1. Check for Unclear or Empty Queries (e.g. "?", "???", "...", "what?")
    clean_punct = re.sub(r"[\s\?\.\!\,\-\_\:\;]", "", q)
    if not clean_punct or q in ("?", "??", "???", "...", "what?", "huh"):
        return "unclear"

    # 2. Emergency / Crisis / Distress / Unsafe
    emergency_keywords = [
        "suicide", "kill myself", "harm", "self harm", "crisis", "sos", "emergency", "danger",
        "attacked", "beaten", "threatened", "police violence", "immediate help",
        "save me", "depressed", "mental breakdown", "helpline", "call helpline",
        "unsafe", "in danger", "being hit", "abuse", "abused", "physical threat"
    ]
    if _matches_any(emergency_keywords, q):
        return "emergency_crisis"

    # 3. Help, Confused & Coming Out queries
    coming_out_patterns = [
        r"\b(tell|telling)\s+(my\s+)?(family|parents|mom|dad|mother|father|relatives)\b",
        r"\bhow\s+(do|can)\s+i\s+tell\b",
        r"\bcoming\s+out\b",
        r"\bcome\s+out\b",
    ]
    if any(re.search(p, q, re.IGNORECASE) for p in coming_out_patterns):
        return "family_coming_out"

    confused_keywords = [
        "i need help", "need help", "i'm confused", "im confused", "feel confused",
        "feeling confused", "so confused", "can you help me"
    ]
    if _matches_any(confused_keywords, q):
        return "confused_need_help"

    # 3. Conversational / Small Talk Intention Check
    # A. "How are you" / "How r u" / "How's it going" (including combined "hello how are you")
    howareyou_patterns = [
        r"\bhow\s+(are|r)\s+(you|u)\b",
        r"\bhow\s+(are|r)\s+(you|u)\s+doing\b",
        r"\bhow\s+do\s+you\s+do\b",
        r"\bhow\'?s\s+it\s+going\b",
        r"\bhows\s+it\s+going\b",
        r"\bhow\s+have\s+you\s+been\b",
    ]
    if any(re.search(p, q, re.IGNORECASE) for p in howareyou_patterns):
        return "chitchat_howareyou"

    # B. "What are you doing" / "wyd" (takes priority over plain greeting)
    doing_patterns = [
        r"\bwhat\s+(are|r)\s+(you|u)\s+doing\b",
        r"\bwhat\s+(are|r)\s+(you|u)\s+up\s+to\b",
        r"\bwhat\s+(are|r)\s+(you|u)\s+upto\b",
        r"\bwhat\s+do\s+you\s+do\b",
        r"\bwyd\b",
        r"\bwhat\'?s\s+up\b",
        r"\bwhats\s+up\b",
        r"\bwassup\b",
        r"\bsup\b",
    ]
    if any(re.search(p, q, re.IGNORECASE) for p in doing_patterns):
        return "chitchat_doing"

    # C. User replies about feeling good / fine: "I am fine", "I'm good", etc.
    user_good_patterns = [
        r"\bi\s*(am|\'m)?\s*(doing\s+)?(good|fine|great|well|awesome|okay|ok)\b",
        r"\b(doing|feeling)\s+(good|fine|great|well)\b",
        r"\ball\s+good\b",
        r"\bfit\s+and\s+fine\b",
        r"^(good|fine|great|well|all good|awesome|ok|okay)[\.\!]?$",
    ]
    if any(re.search(p, q, re.IGNORECASE) for p in user_good_patterns) and not any(neg in q for neg in ("not", "never", "unhappy", "bad")):
        return "chitchat_user_good"

    # D. Greetings: "hello", "hi", "hey", "namaste", etc.
    greeting_keywords = [
        "hi", "hii", "hiii", "hello", "helo", "hey", "heyy", "heyyy", "hey there",
        "hola", "namaste", "namaskar", "vanakkam", "pranam", "greetings",
        "good morning", "good evening", "good afternoon"
    ]
    if _matches_any(greeting_keywords, q):
        return "chitchat_greeting"

    # E. "Who are you" / "What can you do" / "What is this"
    identity_patterns = [
        r"\bwho\s+(are|r)\s+(you|u)\b",
        r"\bwhat\s+(are|r)\s+(you|u)\b",
        r"\bwho\s+made\s+(you|u)\b",
        r"\bare\s+(you|u)\s+(an\s+)?ai\b",
        r"\bare\s+(you|u)\s+(a\s+)?bot\b",
        r"\bwhat\s+can\s+(you|u)\s+do\b",
        r"\btell\s+me\s+about\s+(yourself|you)\b",
        r"\bwhat\s+is\s+beyond\s+identity\b",
    ]
    if any(re.search(p, q, re.IGNORECASE) for p in identity_patterns):
        return "chitchat_identity"

    # F. "Thank you" / "Thanks"
    thanks_keywords = [
        "thank you", "thanks", "thank u", "thx", "thank you so much",
        "dhanyawad", "shukriya", "much appreciated"
    ]
    if _matches_any(thanks_keywords, q):
        return "chitchat_thanks"

    # G. Compliments & Positive feedback
    compliment_keywords = [
        "awesome", "great job", "nice work", "you are great", "you're great",
        "love you", "cool", "superb", "brilliant", "amazing", "wonderful", "good bot"
    ]
    if _matches_any(compliment_keywords, q):
        return "chitchat_compliment"

    # H. Farewell / Goodbye / Good night
    if any(re.search(p, q, re.IGNORECASE) for p in [r"\bgood\s*night\b", r"\bshubh\s*ratri\b"]):
        return "good_night"

    farewell_keywords = [
        "bye", "goodbye", "see you", "cya", "take care", "tata"
    ]
    if _matches_any(farewell_keywords, q):
        return "chitchat_farewell"

    # I. Transgender self-identification ("I am transgender", "I'm trans", etc.)
    trans_self_patterns = [
        r"\b(i am|i\'m|am i|i think i am|i think i\'m|mai|main)\s+(transgender|trans|trans\s*woman|trans\s*man|hijra|kinnar)\b",
        r"\bi\s+(identify\s+as|am)\s+(a\s+)?(transgender|trans\s+person|trans\s+woman|trans\s+man)\b",
    ]
    if any(re.search(p, q, re.IGNORECASE) for p in trans_self_patterns):
        return "user_is_transgender"

    # 4. Direct Option / Number Selection
    q_clean = re.sub(r"[^a-zA-Z0-9\s]", " ", q).strip()
    words = q_clean.split()
    first_token = words[0] if words else ""
    if q_clean in ("1", "option 1", "option1", "choice 1", "first option") or (len(words) <= 3 and first_token == "1"):
        return "employment"
    if q_clean in ("2", "option 2", "option2", "choice 2", "second option") or (len(words) <= 3 and first_token == "2"):
        return "housing"
    if q_clean in ("3", "option 3", "option3", "choice 3", "third option") or (len(words) <= 3 and first_token == "3"):
        return "healthcare"
    if q_clean in ("4", "option 4", "option4", "choice 4", "fourth option") or (len(words) <= 3 and first_token == "4"):
        return "legal_rights"
    if q_clean in ("5", "option 5", "option5", "choice 5", "fifth option") or (len(words) <= 3 and first_token == "5"):
        return "emergency_crisis"

    # 5. Employment & Jobs (checked before ally support so customer support / jobs are identified properly)
    job_keywords = [
        "job", "jobs", "employment", "work", "hiring", "vacancy", "career", "salary",
        "interview", "resume", "cv", "retail", "tech", "customer support"
    ]
    if _matches_any(job_keywords, q):
        return "employment"

    # 6. LGBTQIA+ Specific Intent Checks
    # A. Gay identity
    if any(re.search(p, q, re.IGNORECASE) for p in [
        r"\b(i am|i\'m|am i|i think i am|i think i\'m)\s+gay\b",
        r"\bgay\s+(man|boy|guy|rights|identity|support)\b",
        r"\bwhat\s+does\s+gay\s+mean\b",
    ]):
        return "user_is_gay"

    # B. Lesbian identity
    if any(re.search(p, q, re.IGNORECASE) for p in [
        r"\b(i am|i\'m|am i|i think i am|i think i\'m)\s+lesbian\b",
        r"\blesbian\s+(woman|girl|rights|identity|support)\b",
        r"\bwhat\s+does\s+lesbian\s+mean\b",
    ]):
        return "user_is_lesbian"

    # C. Bisexual identity
    if any(re.search(p, q, re.IGNORECASE) for p in [
        r"\b(i am|i\'m|am i|i think i am|i think i\'m)\s+(bi|bisexual)\b",
        r"\bbisexual\s+(support|identity|meaning|rights)\b",
        r"\bwhat\s+does\s+bisexual\s+mean\b",
    ]):
        return "user_is_bisexual"

    # D. Asexual identity
    if any(re.search(p, q, re.IGNORECASE) for p in [
        r"\b(i am|i\'m|am i|i think i am|i think i\'m)\s+(asexual|ace)\b",
        r"\basexuality\b",
        r"\basexual\s+(spectrum|support|identity)\b",
    ]):
        return "user_is_asexual"

    # E. Section 377 & Homosexuality Legality in India
    if any(re.search(p, q, re.IGNORECASE) for p in [
        r"\bsection\s*377\b",
        r"\b377\b",
        r"\bis\s+being\s+gay\s+(legal|a\s+crime|allowed)\b",
        r"\bis\s+homosexuality\s+(legal|a\s+crime|allowed)\b",
        r"\bdecriminali[zs]ed\b",
    ]):
        return "section_377_legal"

    # F. Same-sex Marriage & Relationships
    if any(re.search(p, q, re.IGNORECASE) for p in [
        r"\bsame\s*[- ]?sex\s*(marriage|wedding|marry|relationship|couple|cohabitation|living)\b",
        r"\bcan\s+(two\s+men|two\s+women|two\s+boys|two\s+girls|same\s*[- ]?sex\s*couples|gay\s*couples|lesbian\s*couples)\s+(get\s+)?(marry|married)\b",
        r"\bgay\s*marriage\b",
        r"\blesbian\s*marriage\b",
    ]):
        return "same_sex_marriage_relationships"

    # G. Conversion Therapy Ban
    if any(re.search(p, q, re.IGNORECASE) for p in [
        r"\bconversion\s+(therapy|treatment|cure)\b",
        r"\bcan\s+a\s+doctor\s+cure\s+(gay|homosexuality|transgender)\b",
        r"\bis\s+conversion\s+therapy\s+(legal|banned)\b",
    ]):
        return "conversion_therapy_ban"

    # H. Forced Marriage Protection
    if any(re.search(p, q, re.IGNORECASE) for p in [
        r"\bforced\s+marriage\b",
        r"\bforcing\s+me\s+to\s+marry\b",
        r"\bforce\s+me\s+to\s+marry\b",
        r"\bparents\s+forcing\s+me\b",
    ]):
        return "forced_marriage_protection"

    # I. LGBTQ+ Safe Sex & PrEP / PEP
    if any(re.search(p, q, re.IGNORECASE) for p in [
        r"\bprep\b",
        r"\bpep\b",
        r"\bsafe\s+sex\b",
        r"\bhiv\s+(test|testing|clinic|prevention)\b",
        r"\bnaco\b",
    ]):
        return "lgbtq_safe_sex_prep"

    # J. LGBTQ+ Community Groups
    if any(re.search(p, q, re.IGNORECASE) for p in [
        r"\bhumsafar\b",
        r"\bsappho\b",
        r"\bnaz\s+foundation\b",
        r"\blgbt(q|qia)?\s+(group|community|support\s*group|ngo|meetup|centre|center)\b",
    ]):
        return "lgbtq_community_groups"

    # 7. Core Transgender & Gender Identity Topics
    # Topic A: Transgender and gender identity basics & terminology
    basics_keywords = [
        "transgender", "trans", "gender identity", "gender expression", "cisgender",
        "non-binary", "nonbinary", "pronoun", "pronouns", "dysphoria", "gender dysphoria",
        "deadname", "deadnaming", "queer", "intersex", "third gender", "trans person",
        "trans man", "trans woman", "transmasc", "transfem", "ftm", "mtf",
        "what does transgender mean", "what is transgender", "transgender meaning",
        "gay", "lesbian", "bisexual", "asexual", "pansexual"
    ]
    if _matches_any(["pronoun", "pronouns", "cisgender", "non-binary", "nonbinary", "gender identity", "gender expression", "deadname", "deadnaming", "what is trans", "what does trans"], q):
        return "basics_terminology"

    # Topic B: Rights and laws (for India: Transgender Persons Act 2019, NALSA judgment, ID/certificate process)
    legal_keywords = [
        "rights", "law", "legal", "tg act", "transgender act", "act 2019", "nalsa", "article 14",
        "article 21", "certificate", "id card", "identity card", "district magistrate",
        "dm", "affidavit", "aadhaar", "pan card", "passport", "adopt", "adoption",
        "child", "custody", "marriage", "free legal aid", "15100", "section 12", "section 18",
        "national portal", "dm certificate", "section 377", "377", "supriyo"
    ]
    if _matches_any(legal_keywords, q):
        return "legal_rights"

    # Topic C: Healthcare and transition information (general info only)
    health_keywords = [
        "hrt", "hormone", "hormones", "therapy", "doctor", "clinic", "surgery", "srs",
        "gender affirmation", "transition", "transitioning", "endocrinologist", "blood test", "blood tests",
        "ayushman", "pmjay", "pm-jay", "estrogen", "testosterone", "blockers", "prep", "pep", "hiv"
    ]
    if _matches_any(health_keywords, q):
        return "healthcare"

    # Topic D: Mental health and emotional support
    mental_keywords = [
        "mental health", "emotional support", "tele-manas", "14416", "counselor", "counseling",
        "psychiatrist", "psychologist", "anxiety", "depression", "lonely", "dysphoric"
    ]
    if _matches_any(mental_keywords, q):
        return "mental_health"

    # Topic E: Family, friends and workplace support, and how to be a good ally
    ally_keywords = [
        "ally", "allies", "good ally", "allyship", "be an ally",
        "parents", "parenting", "family support", "coming out", "come out",
        "workplace support", "colleague", "colleagues", "coworker",
        "how to support", "be supportive", "acceptance"
    ]
    if _matches_any(ally_keywords, q):
        return "support_and_ally"

    # Other Transgender-related domains in Beyond Identity portal:
    # Employment & Jobs
    job_keywords = [
        "job", "jobs", "employment", "work", "hiring", "vacancy", "career", "salary",
        "interview", "resume", "cv", "retail", "tech", "customer support"
    ]
    if _matches_any(job_keywords, q):
        return "employment"

    # Housing & Shelters
    housing_keywords = [
        "housing", "house", "rent", "room", "flat", "apartment", "landlord",
        "evict", "eviction", "shelter", "garima greh", "pg", "transit shelter",
        "kicked out", "homeless"
    ]
    if _matches_any(housing_keywords, q):
        return "housing"

    # Incident reporting
    incident_keywords = [
        "report", "incident", "harass", "harassment", "discrimination", "extort",
        "complaint", "file a complaint", "abuse", "fir", "police station", "bribe"
    ]
    if _matches_any(incident_keywords, q):
        return "incident_report"

    # Welfare Schemes
    scheme_keywords = [
        "scheme", "schemes", "scholarship", "scholarships", "smile", "pm-daksh", "daksh", "welfare",
        "financial aid", "grant", "grants", "stipend", "government benefit", "government scheme",
        "ration", "pension", "mazhavillu", "garima greh", "ayushman scheme", "utthan kosh",
        "sweekruti", "mythri"
    ]
    if _matches_any(scheme_keywords, q):
        return "scholarship_schemes"

    if _matches_any(basics_keywords, q):
        return "basics_terminology"

    # Comprehensive LGBTQ+ keywords
    lgbtq_keywords = [
        "gay", "lesbian", "bisexual", "bi", "asexual", "ace", "pansexual", "queer",
        "intersex", "nonbinary", "non-binary", "genderfluid", "lgbt", "lgbtq", "lgbtqia",
        "section 377", "377", "conversion therapy", "forced marriage", "same sex",
        "same-sex", "prep", "pep", "hiv", "humsafar", "sappho", "naz foundation",
        "supriyo", "same-sex marriage", "gay marriage", "lesbian marriage", "orientation"
    ]

    # Check for obvious out-of-scope queries (weather, coding, math, sports, recipes, etc.)
    out_of_scope_patterns = [
        r"\b(weather|temperature|rain|forecast)\b",
        r"\b(python|javascript|code|coding|programming|function|compiler|bug)\b",
        r"\b(cricket|football|soccer|ipl|match|score|fifa)\b",
        r"\b(recipe|cook|cooking|bake|cake|food)\b",
        r"\b(capital of|president of|prime minister of)\b",
        r"\b(bitcoin|crypto|stock market|cryptocurrency)\b",
        r"\b(movie|cinema|netflix|song|actor|actress)\b",
    ]
    if any(re.search(p, q, re.IGNORECASE) for p in out_of_scope_patterns):
        return "out_of_scope"

    words_list = q.split()
    if len(words_list) >= 4 and not _matches_any(
        basics_keywords + legal_keywords + health_keywords + mental_keywords + ally_keywords + job_keywords + housing_keywords + lgbtq_keywords,
        q
    ):
        return "out_of_scope"

    return "general"


def search_listings_in_db(
    db: Session,
    intent: str,
    query: str,
    category_filter: Optional[str] = None,
    location_filter: Optional[str] = None,
    limit: int = 5,
) -> List[schemas.ChatbotItemOut]:
    """Query live database listings matching intent, category, location, and keywords."""
    db_query = db.query(models.Listing).filter(
        models.Listing.status == models.VerificationStatus.verified
    )

    # Intent-based category filtering
    category_map = {
        "employment": models.ListingCategory.employment,
        "housing": models.ListingCategory.housing,
        "healthcare": models.ListingCategory.healthcare,
        "scholarship_schemes": None,  # will search scheme & scholarship
    }

    if category_filter:
        cf_clean = category_filter.strip().lower()
        if cf_clean in ("scholarships", "scholarship"):
            db_query = db_query.filter(
                or_(
                    models.Listing.category == models.ListingCategory.scholarship,
                    models.Listing.category == models.ListingCategory.scheme,
                )
            )
        elif cf_clean in ("government_scheme", "government_schemes", "schemes", "scheme"):
            db_query = db_query.filter(models.Listing.category == models.ListingCategory.scheme)
        else:
            try:
                db_query = db_query.filter(models.Listing.category == models.ListingCategory(cf_clean))
            except Exception:
                pass
    elif intent in category_map and category_map[intent] is not None:
        db_query = db_query.filter(models.Listing.category == category_map[intent])
    elif intent == "scholarship_schemes":
        db_query = db_query.filter(
            or_(
                models.Listing.category == models.ListingCategory.scheme,
                models.Listing.category == models.ListingCategory.scholarship,
            )
        )

    # Location filter if specified
    if location_filter:
        db_query = db_query.filter(models.Listing.location.ilike(f"%{location_filter}%"))

    # Keyword search across title, description, and organization
    terms = [t for t in query.lower().split() if len(t) > 2]
    if terms:
        or_clauses = []
        for t in terms[:3]:
            or_clauses.append(models.Listing.title.ilike(f"%{t}%"))
            or_clauses.append(models.Listing.description.ilike(f"%{t}%"))
            or_clauses.append(models.Listing.organization_name.ilike(f"%{t}%"))
            or_clauses.append(models.Listing.location.ilike(f"%{t}%"))
        
        # If we have keyword matches, try filtering by them; if empty, we fall back to category query
        keyword_matched = db_query.filter(or_(*or_clauses)).limit(limit).all()
        if keyword_matched:
            return [_to_chatbot_item(item) for item in keyword_matched]

    listings = db_query.limit(limit).all()
    return [_to_chatbot_item(item) for item in listings]


def _to_chatbot_item(item: models.Listing) -> schemas.ChatbotItemOut:
    category_name = item.category.value if hasattr(item.category, "value") else str(item.category)
    badge = f"Verified {category_name.capitalize()}"
    return schemas.ChatbotItemOut(
        id=item.id,
        category=category_name,
        title=item.title,
        organization_name=item.organization_name or "Verified Organization",
        location=item.location or "Pan-India",
        contact_info=item.contact_info,
        description=item.description,
        status="verified",
        verification_notes=item.verification_notes,
        badge=badge,
    )


def generate_curated_reply(
    intent: str,
    query: str,
    suggestions: List[schemas.ChatbotItemOut],
) -> tuple[str, List[str]]:
    """Generates empathetic, warm, concise responses adhering to the chatbot behavior and rules."""
    suggested_prompts: List[str] = []

    if intent == "unclear":
        reply = "Could you please clarify what specific question you have?"

    elif intent == "emergency_crisis":
        reply = (
            "I'm so sorry you're feeling distressed or unsafe, and your safety is the most important thing. "
            "Please reach out to someone you trust, or contact the 24/7 Transgender Helpline at 868989330, "
            "Tele-MANAS at 14416, NALSA legal aid at 15100, or emergency services at 112. "
            "Support is available right now."
        )
        suggested_prompts = [
            "Call Helpline: 868989330",
            "Tele-MANAS: 14416",
            "NALSA Free Legal Aid: 15100",
        ]

    elif intent == "family_coming_out":
        reply = (
            "Coming out to your family is a deeply personal step, and your emotional and physical safety should always come first. "
            "Take your time until you feel ready, consider sharing simple educational resources to help them understand, "
            "and lean on supportive friends as you take this step."
        )

    elif intent == "confused_need_help":
        reply = (
            "It is completely normal to feel confused or overwhelmed, and you do not have to have everything figured out right away. "
            "Beyond Identity provides verified guidance on gender identity, Indian legal rights, healthcare, and community support. "
            "What specific question can I help you with?"
        )

    elif intent == "chitchat_greeting":
        reply = "Hi! I'm Beyond Identity — a website where you get verified, trustworthy information about transgender identity and related topics."

    elif intent == "chitchat_howareyou":
        reply = "I'm doing well, thanks! How can I help you today?"

    elif intent == "chitchat_user_good":
        reply = "I'm glad to hear that! What would you like to know about transgender identity or support?"

    elif intent == "chitchat_doing":
        reply = "I'm right here on Beyond Identity and ready to help with any transgender-related questions you have."

    elif intent == "chitchat_identity":
        reply = "I am the Beyond Identity Assistant, here to provide verified, trustworthy information about transgender identity, rights, and support."

    elif intent == "chitchat_thanks":
        reply = "You're very welcome! Feel free to reach out whenever you need information."

    elif intent == "chitchat_compliment":
        reply = "Thank you so much, that's very kind! How can I help you today?"

    elif intent == "chitchat_farewell":
        reply = "Goodbye! Take care, and feel free to reach out anytime."

    elif intent == "good_night":
        reply = "Good night and sweet dreams! Take gentle care of yourself. Beyond Identity is always here for you whenever you return."
        suggested_prompts = []

    elif intent == "user_is_transgender":
        reply = (
            "Thank you for sharing this with me. Who you are is completely valid, beautiful, and deeply respected. "
            "Beyond Identity is your safe haven. Under Indian law (NALSA 2014 & TG Act 2019), you have the fundamental right "
            "to self-perceived gender identity. How are you feeling about it today, and how can I best support you?"
        )
        suggested_prompts = [
            "What are my legal rights in India?",
            "How to get TG Certificate",
            "Garima Greh Shelters",
        ]

    elif intent == "basics_terminology":
        reply = (
            "Transgender describes a person whose gender identity differs from the sex assigned to them at birth. "
            "Gender identity is an internal, personal sense of who you are, while pronouns and gender expression are ways to share and respect that identity. "
            "Everyone's journey is unique and valid."
        )

    elif intent == "legal_rights":
        reply = (
            "In India, the Supreme Court NALSA judgment (2014) and the Transgender Persons Act 2019 protect your right to self-perceived gender identity. "
            "You can apply online for a Transgender Certificate at transgender.dosje.gov.in without requiring surgery. "
            "For specific legal issues, free legal aid is available under NALSA Section 12 at 15100, or you can consult a qualified lawyer."
        )

    elif intent == "healthcare":
        reply = (
            "Gender-affirming healthcare can include counseling, hormone therapy (HRT), and surgeries tailored to your personal needs. "
            "In India, the Ayushman Bharat TG package provides health cover up to ₹5 Lakh per year for eligible individuals. "
            "Please note this is general guidance only; consult a qualified doctor or endocrinologist before starting or changing medical care."
        )

    elif intent == "mental_health":
        reply = (
            "Navigating gender identity, dysphoria, or stress can be challenging, but you do not have to carry it alone. "
            "You can speak with a queer-affirmative counselor, or call the 24/7 Tele-MANAS helpline at 14416 "
            "or the Transgender Community Helpline at 868989330 for free, confidential mental health support."
        )

    elif intent == "support_and_ally":
        reply = (
            "Being a good ally means listening with empathy, respecting a person's chosen name and pronouns, and speaking up against harassment. "
            "Educating yourself and fostering an accepting environment at home or work makes a meaningful difference."
        )

    elif intent == "employment":
        reply = (
            "Under the Transgender Persons Act 2019, discrimination in recruitment, wages, and workplace conditions is prohibited in India. "
            "Establishments must designate a Complaints Officer to address discrimination grievances. "
            "For specific workplace disputes, please consult a qualified lawyer or legal aid."
        )

    elif intent == "housing":
        reply = (
            "Under Section 12 of the Transgender Persons Act 2019, arbitrary eviction from a home or rental property based on gender identity is unlawful. "
            "For emergency shelter, the government operates Garima Greh transit shelter homes across India. "
            "For legal disputes with landlords, reach out to NALSA free legal aid at 15100."
        )

    elif intent == "incident_report":
        reply = (
            "Under Section 18 of the Transgender Persons Act 2019, abuse or discrimination against transgender persons carries penalties up to two years imprisonment. "
            "You can file a complaint with local authorities or call NALSA Free Legal Aid at 15100 for support."
        )

    elif intent == "scholarship_schemes":
        reply = (
            "Welfare schemes and scholarships are available under the Ministry of Social Justice and Empowerment (MoSJE), "
            "including the SMILE umbrella scheme and PM-DAKSH vocational training. "
            "Applications are submitted online through the National Portal for Transgender Persons at transgender.dosje.gov.in."
        )

    elif intent == "user_is_gay":
        reply = (
            "Being gay is a natural, healthy variation of human sexuality. "
            "Consensual same-sex relationships are completely decriminalized in India following the Supreme Court's Section 377 judgment in 2018. "
            "You are valid and deserving of respect, dignity, and love."
        )
        suggested_prompts = [
            "Legal Rights in India (Section 377)",
            "LGBTQ+ Community Support Groups",
            "Tele-MANAS: 14416",
        ]

    elif intent == "user_is_lesbian":
        reply = (
            "Being a lesbian is completely natural, valid, and fully decriminalized in India. "
            "Organizations like Sappho for Equality, Nazariya, and The Humsafar Trust offer dedicated, safe community spaces and legal assistance. "
            "You are never alone, and your identity is authentic and respected."
        )
        suggested_prompts = [
            "Sappho for Equality & Support",
            "Legal Protections against Harassment",
            "Tele-MANAS: 14416",
        ]

    elif intent == "user_is_bisexual":
        reply = (
            "Bisexuality is a valid, real sexual orientation where you may be attracted to more than one gender. "
            "You do not need to prove your identity or pick a side to be authentic. "
            "Affirming peer groups and mental health professionals are here to support your journey."
        )
        suggested_prompts = [
            "LGBTQ+ Community Support",
            "Queer Affirmative Therapists",
            "Tips for Coming Out",
        ]

    elif intent == "user_is_asexual":
        reply = (
            "Asexuality is a completely normal and healthy orientation where someone experiences little to no sexual attraction. "
            "You are whole, valid, and part of a vibrant asexual and aromantic community in India such as Indian Aces."
        )
        suggested_prompts = [
            "Indian Aces Community",
            "Queer Support Groups",
            "Affirming Mental Health",
        ]

    elif intent == "user_is_nonbinary_queer":
        reply = (
            "Non-binary and queer identities are completely valid. "
            "In India, the Supreme Court's NALSA (2014) ruling protects your constitutional right to self-identify your gender beyond the binary. "
            "Your chosen name and pronouns deserve complete respect."
        )
        suggested_prompts = [
            "Transgender Persons Act 2019",
            "Pronouns & Identity Guide",
            "Free Legal Aid: 15100",
        ]

    elif intent == "section_377_legal":
        reply = (
            "In Navtej Singh Johar (2018), the Supreme Court of India unanimously struck down Section 377, decriminalizing consensual adult same-sex relationships. "
            "Being LGBTQ+ is fully legal in India with constitutional rights to equality, privacy, and dignity under Articles 14 and 21."
        )
        suggested_prompts = [
            "NALSA Legal Aid: 15100",
            "High Court Protection Writs",
            "Police Protection Guidelines",
        ]

    elif intent == "same_sex_marriage_relationships":
        reply = (
            "While the Supreme Court in Supriyo (2023) held that legal recognition of same-sex marriage requires legislation by Parliament, "
            "same-sex couples have the full constitutional right to live together in consensual cohabitation. "
            "High Courts across India regularly grant police protection to queer couples facing family harassment."
        )
        suggested_prompts = [
            "Cohabitation Rights in India",
            "High Court Protection",
            "NALSA Free Legal Aid: 15100",
        ]

    elif intent == "conversion_therapy_ban":
        reply = (
            "Conversion therapy is banned and illegal in India. "
            "The National Medical Commission (NMC) classified conversion therapy as professional medical misconduct, "
            "and the Madras High Court directed state medical councils to revoke licenses of any practitioner attempting to alter sexual orientation or gender identity."
        )
        suggested_prompts = [
            "NMC Conversion Therapy Ban",
            "Report Unethical Doctors",
            "Tele-MANAS: 14416",
        ]

    elif intent == "forced_marriage_protection":
        reply = (
            "Forced marriage is illegal in India, and adults have the constitutional right to choose their life partner. "
            "If your family is coercing or threatening you, contact emergency services at 112, reach NALSA free legal aid at 15100, "
            "or contact queer support helplines for urgent shelter and High Court protection writs."
        )
        suggested_prompts = [
            "Emergency: 112",
            "NALSA Free Legal Aid: 15100",
            "High Court Protection Writ",
        ]

    elif intent == "lgbtq_safe_sex_prep":
        reply = (
            "Free condoms, STI screening, and confidential HIV testing are available at NACO Integrated Counseling and Testing Centres (ICTC) across India (Helpline: 1097). "
            "Pre-Exposure Prophylaxis (PrEP) and Post-Exposure Prophylaxis (PEP, within 72 hours) are available through community clinics like The Humsafar Trust and YRG Care."
        )
        suggested_prompts = [
            "NACO Helpline: 1097",
            "Free HIV Testing Centres",
            "Humsafar Trust Health Clinics",
        ]

    elif intent == "lgbtq_community_groups":
        reply = (
            "Supportive LGBTQIA+ community organizations in India include The Humsafar Trust (Mumbai/Delhi), Sappho for Equality (Kolkata), "
            "Naz India, Sangama (Bengaluru), and Tweet Foundation. "
            "For confidential mental health support, you can also call Tele-MANAS at 14416 anytime."
        )
        suggested_prompts = [
            "The Humsafar Trust",
            "Sappho for Equality",
            "Tele-MANAS: 14416",
        ]

    elif intent == "out_of_scope":
        reply = "This chat is focused on LGBTQIA+ and transgender-related support, including sexual orientation, gender identity, rights, healthcare basics, coming out, and community support."

    else:
        # General / Platform Help
        reply = (
            "Beyond Identity gives verified information on transgender and LGBTQIA+ identity, Indian legal rights, healthcare basics, and community support. "
            "What would you like to know?"
        )

    return reply, suggested_prompts


def detect_query_language(text: str) -> Optional[str]:
    """
    Detects if the query is in Hindi (Devanagari or Romanized Hinglish) vs English.
    Returns 'hi', 'en', or None if indeterminate.
    """
    if not text:
        return None
    # 1. Devanagari Unicode Block (U+0900 to U+097F)
    if re.search(r"[\u0900-\u097f]", text):
        return "hi"

    # 2. Strong Romanized Hindi / Hinglish keywords
    hi_markers = [
        r"\bmain\b", r"\bmai\b", r"\bmera\b", r"\bmeri\b", r"\bmere\b",
        r"\bhum\b", r"\bhumne\b", r"\bhumein\b", r"\bmujhe\b", r"\bmujh\b",
        r"\bkya\b", r"\bhai\b", r"\bhain\b", r"\bhoon\b", r"\bhu\b",
        r"\bnahi\b", r"\bna\b", r"\bka\b", r"\bki\b", r"\bke\b", r"\bko\b",
        r"\bse\b", r"\bpar\b", r"\bpe\b", r"\bmein\b", r"\bme\b",
        r"\bkarna\b", r"\bkar\b", r"\bkarein\b", r"\bkarta\b", r"\bchahiye\b",
        r"\bkaise\b", r"\bkyu\b", r"\bkyun\b", r"\bdarr\b", r"\blag\b",
        r"\braha\b", r"\brahi\b", r"\bbaat\b", r"\bbimari\b", r"\bbachcha\b",
        r"\bshukriya\b", r"\bdhanyawad\b", r"\btheek\b", r"\bsahi\b",
        r"\bshaadi\b", r"\bpadhai\b", r"\bmarna\b"
    ]
    hi_count = sum(1 for p in hi_markers if re.search(p, text, re.IGNORECASE))
    if hi_count >= 2 or (len(text.split()) <= 4 and hi_count >= 1):
        return "hi"

    # 3. English indicators when no Hindi markers matched
    en_markers = [
        r"\bi\b", r"\bam\b", r"\bthe\b", r"\bis\b", r"\bare\b", r"\byou\b",
        r"\bwhat\b", r"\bhow\b", r"\bcan\b", r"\bwe\b", r"\bdo\b", r"\bnot\b",
        r"\bmy\b", r"\bchild\b", r"\bto\b", r"\bfor\b", r"\babout\b", r"\bthis\b"
    ]
    en_count = sum(1 for p in en_markers if re.search(p, text, re.IGNORECASE))
    if en_count >= 2 and hi_count == 0:
        return "en"

    return None


# =======================================================================
# Real Community Interviews Knowledge Source & Metadata
# =======================================================================
COMMUNITY_VIDEOS_JSON = Path(__file__).resolve().parent.parent / "data" / "community_videos.json"
ALT_COMMUNITY_VIDEOS_JSON = Path(__file__).resolve().parent.parent.parent / "beyond_identity_backend" / "app" / "data" / "community_videos.json"


def load_community_interviews() -> List[Dict[str, Any]]:
    """Loads verified real-life community interviews from permanent data registry."""
    for path in (COMMUNITY_VIDEOS_JSON, ALT_COMMUNITY_VIDEOS_JSON):
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        for idx, v in enumerate(data, start=1):
                            if "id" not in v:
                                v["id"] = idx
                        return data
            except Exception:
                pass
    return []


COMMUNITY_INTERVIEWS: List[Dict[str, Any]] = load_community_interviews()

INTERVIEWEE_NAME_MAP: Dict[str, str] = {
    "chitra palekar": "Chitra Palekar",
    "chitra": "Chitra Palekar",
    "palekar": "Chitra Palekar",
    "dr. trinetra haldar gummaraju": "Dr. Trinetra Haldar Gummaraju",
    "dr trinetra haldar gummaraju": "Dr. Trinetra Haldar Gummaraju",
    "dr trinetra": "Dr. Trinetra Haldar Gummaraju",
    "dr. trinetra": "Dr. Trinetra Haldar Gummaraju",
    "trinetra": "Dr. Trinetra Haldar Gummaraju",
    "haldar": "Dr. Trinetra Haldar Gummaraju",
    "gummaraju": "Dr. Trinetra Haldar Gummaraju",
    "gauri sawant": "Gauri Sawant",
    "gauri": "Gauri Sawant",
    "sawant": "Gauri Sawant",
    "aarohi sen": "Aarohi Sen",
    "aarohi": "Aarohi Sen",
    "aryan pasha": "Aryan Pasha",
    "aryan": "Aryan Pasha",
    "pasha": "Aryan Pasha",
    "arundhati katju & dr. menaka guruswamy": "Arundhati Katju & Dr. Menaka Guruswamy",
    "arundhati katju": "Arundhati Katju & Dr. Menaka Guruswamy",
    "menaka guruswamy": "Arundhati Katju & Dr. Menaka Guruswamy",
    "arundhati": "Arundhati Katju & Dr. Menaka Guruswamy",
    "katju": "Arundhati Katju & Dr. Menaka Guruswamy",
    "guruswamy": "Arundhati Katju & Dr. Menaka Guruswamy",
    "neel ghosh": "Neel Ghosh",
    "neel": "Neel Ghosh",
    "grace banu": "Grace Banu",
    "grace": "Grace Banu",
    "karthik subramaniam": "Karthik Subramaniam",
    "karthik": "Karthik Subramaniam",
    "subramaniam": "Karthik Subramaniam",
    "dr. prasad raj dandekar": "Dr. Prasad Raj Dandekar",
    "dr prasad raj dandekar": "Dr. Prasad Raj Dandekar",
    "dr prasad": "Dr. Prasad Raj Dandekar",
    "dr. prasad": "Dr. Prasad Raj Dandekar",
    "prasad dandekar": "Dr. Prasad Raj Dandekar",
    "prasad": "Dr. Prasad Raj Dandekar",
    "dandekar": "Dr. Prasad Raj Dandekar",
    "anwesa & megha": "Anwesa & Megha",
    "anwesa and megha": "Anwesa & Megha",
    "anwesa": "Anwesa & Megha",
    "megha": "Anwesa & Megha",
    "revathi natarajan": "Revathi Natarajan",
    "revathi": "Revathi Natarajan",
    "natarajan": "Revathi Natarajan",
    "journey": "Unknown Gay",
    "unknown gay": "Unknown Gay",
}


def find_verified_interview(query: str) -> Optional[Dict[str, Any]]:
    """Finds verified interview by interviewee name or interview title keywords."""
    q_norm = query.lower().strip()
    # 1. Match against known names & aliases
    for alias, canonical in INTERVIEWEE_NAME_MAP.items():
        pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, q_norm):
            for interview in COMMUNITY_INTERVIEWS:
                if interview.get("interviewee_name") == canonical:
                    return interview
    # 2. Match against interview title keywords
    for interview in COMMUNITY_INTERVIEWS:
        title = interview.get("title", "").lower()
        if title and title in q_norm:
            return interview
    return None


def is_unverified_interview_query(query: str) -> bool:
    """Detects if query asks about an interview/person not in the verified Beyond Identity catalog."""
    q_norm = query.lower().strip()
    if any(k in q_norm for k in ["interview", "interviewee", "video"]) and any(w in q_norm for w in ["what does", "who is", "explain", "tell me about", "summary of"]):
        if not find_verified_interview(query) and not any(p in q_norm for p in ["how many", "all interviews", "list of", "available interviews"]):
            return True
    return False


def format_interview_summary(interview: Dict[str, Any], lang: str = "en") -> str:
    """Formats verified interview summary with message, quote, duration, and website link."""
    name = interview.get("interviewee_name", "Community Leader")
    title = interview.get("title", "")
    identity = interview.get("identity_tag", "")
    quote = interview.get("key_quote", "")
    desc = interview.get("description", "")
    duration = interview.get("duration", "video")
    loc = interview.get("location", "India")

    if lang == "hi":
        return (
            f"**{name}** ({identity}) का साक्षात्कार **'{title}'** ({loc}):\n\n"
            f"**मुख्य अनुभव व संदेश:** {desc}\n\n"
            f"💬 *\"{quote}\"*\n\n"
            f"🎥 आप यह पूरा साक्षात्कार ({duration}) हमारे **[वीडियो गैलरी](#tab-videos)** में देख सकते हैं।"
        )
    return (
        f"In **{name}**'s ({identity}) interview **'{title}'** ({loc}):\n\n"
        f"**Lived Experience & Message:** {desc}\n\n"
        f"💬 *\"{quote}\"*\n\n"
        f"🎥 You can watch this inspiring {duration} interview directly in our **[Video Interviews Gallery](#tab-videos)**."
    )


def get_interviews_for_emotion_or_topic(topic: str, top_k: int = 2) -> List[Dict[str, Any]]:
    """Returns top relevant verified interviews matching emotional context or topic."""
    matched = []
    topic_map = {
        "feeling_different": ["Unknown Gay", "Dr. Trinetra Haldar Gummaraju"],
        "afraid_of_judgment": ["Aarohi Sen", "Dr. Prasad Raj Dandekar"],
        "feeling_alone": ["Gauri Sawant", "Karthik Subramaniam"],
        "family_acceptance": ["Chitra Palekar", "Gauri Sawant"],
        "shame_or_embarrassment": ["Dr. Prasad Raj Dandekar", "Unknown Gay"],
        "social_acceptance": ["Anwesa & Megha", "Aryan Pasha"],
        "workplace": ["Aarohi Sen", "Neel Ghosh", "Revathi Natarajan"],
        "transmasculine_sports": ["Aryan Pasha"],
        "clinical_transition": ["Dr. Trinetra Haldar Gummaraju"],
        "legal_rights": ["Arundhati Katju & Dr. Menaka Guruswamy", "Grace Banu"],
        "housing_shelter": ["Gauri Sawant", "Karthik Subramaniam"],
        "lesbian_marriage": ["Anwesa & Megha"],
    }
    names = topic_map.get(topic, [])
    for n in names:
        for it in COMMUNITY_INTERVIEWS:
            if it.get("interviewee_name") == n and it not in matched:
                matched.append(it)
                if len(matched) >= top_k:
                    return matched
    return matched


# =======================================================================
# Conversational Multi-Turn Context Continuity Engine
# =======================================================================
def detect_multiturn_context(query: str, history: List[dict], lang: str = "en") -> Optional[tuple[str, str, List[str], List[dict]]]:
    """Recognizes context continuity across multi-turn dialogues without restarting conversation."""
    if not history:
        return None
    last_user_msg = ""
    for m in reversed(history):
        if m.get("role") == "user":
            last_user_msg = m.get("content", "").lower()
            break
    if not last_user_msg:
        return None

    q_lower = query.lower()

    # Case 1: Prior turn touched on feeling different / alone / identity questioning,
    # and current turn expresses anxiety that friends will reject them
    prev_different = any(p in last_user_msg for p in [
        "different", "alone", "confused", "why am i like this", "sabse alag", "akela", "identity", "gay", "transgender", "lesbian"
    ])
    curr_friend_fear = any(p in q_lower for p in [
        "friend", "friends", "dost", "reject", "leave me", "hate me", "stop talking", "turn away"
    ])
    if prev_different and curr_friend_fear:
        intent = "multiturn_friends_rejection"
        if lang == "hi":
            reply = (
                "जैसा कि आपने पहले साझा किया कि आप खुद को दूसरों से अलग महसूस करते हैं, "
                "दोस्तों द्वारा अस्वीकार किए जाने का डर मन में आना बहुत स्वाभाविक है। "
                "दोनों चिंताओं को एक साथ संभालना आसान नहीं होता। "
                "सच्ची दोस्ती हमेशा उस व्यक्ति की कद्र करती है जो आप वास्तव में हैं। "
                "आपको जल्दबाजी करने की बिल्कुल जरूरत नहीं है—आप अपनी गति और सुविधा के अनुसार ही बात साझा करें। "
                "अगर आप सहज महसूस करें, तो आपके दोस्त आपके बारे में क्या सोचते हैं या आप किस बात से सबसे ज्यादा चिंतित हैं?"
            )
            prompts = ["दोस्तों से कैसे बात करें?", "सपोर्ट ग्रुप्स", "Tele-MANAS: 14416"]
        else:
            reply = (
                "Connecting back to what you shared about feeling different, worrying that your friends might reject you is completely understandable. "
                "Carrying both the feeling of being different and the anxiety of losing friendships can feel deeply exhausting. "
                "True friendship is built on seeing and valuing who you truly are, though you never have to rush into disclosing anything before you feel secure. "
                "You do not have to navigate this worry alone. If you're comfortable sharing, what makes you feel they might react this way?"
            )
            prompts = ["Tips for Talking with Friends", "LGBTQ+ Peer Groups", "Tele-MANAS: 14416"]
        interviews = get_interviews_for_emotion_or_topic("feeling_different", top_k=1)
        return (intent, reply, prompts, interviews)

    # Case 2: Prior turn was about family acceptance, and current turn expresses fear of disownment/eviction
    prev_family = any(p in last_user_msg for p in ["family", "parents", "gharwale", "mom", "dad", "mother", "father"])
    curr_eviction = any(p in q_lower for p in ["kick me out", "leave the house", "disown", "kicked out", "ghar se nikal", "throw me out"])
    if prev_family and curr_eviction:
        intent = "multiturn_family_eviction"
        if lang == "hi":
            reply = (
                "आपके परिवार की अस्वीकृति और घर से निकाले जाने की चिंता बहुत गंभीर है, और आपकी सुरक्षा सबसे महत्वपूर्ण है। "
                "ट्रांसजेंडर कानून 2019 की धारा 12 के तहत किसी भी ट्रांसजेंडर व्यक्ति को घर से बेदखल करना गैरकानूनी है। "
                "गरिमा गृह शेल्टर होम्स सुरक्षित आश्रय प्रदान करते हैं। "
                "आपातकालीन सहायता के लिए 112 और NALSA मुफ़्त कानूनी सहायता 15100 पर तुरंत संपर्क किया जा सकता है।"
            )
            prompts = ["गरिमा गृह शेल्टर", "NALSA: 15100", "आपातकालीन: 112"]
        else:
            reply = (
                "Following up on your concerns about your family, the fear of being disowned or evicted is deeply distressing, and your physical safety must come first. "
                "Under Section 12 of the Transgender Persons Act 2019, arbitrary eviction of a transgender person is unlawful. "
                "Emergency transit shelter is available through Garima Greh homes across India (championed by leaders like Gauri Sawant), and NALSA free legal aid is available at 15100. "
                "Do you have a safe place or trusted friend you could stay with if ever needed?"
            )
            prompts = ["Garima Greh Shelters", "NALSA Free Legal Aid: 15100", "Emergency: 112"]
        interviews = get_interviews_for_emotion_or_topic("housing_shelter", top_k=1)
        return (intent, reply, prompts, interviews)

    return None


# =======================================================================
# Website Guide & Real-Life Video Interview Knowledge Assistant
# =======================================================================
def detect_website_guide_or_interview(query: str, history: List[dict] = [], lang: str = "en") -> Optional[tuple[str, str, List[str], List[dict]]]:
    """Provides complete guidance on Beyond Identity website features and real video interviews."""
    q_norm = query.lower().strip()

    # 1. Simple explanation of an interview
    if any(p in q_norm for p in [
        "in simple words", "in simple terms", "simple explanation", "explain their experience",
        "explain this person's experience", "what does this particular interview explain",
        "what does this interview explain"
    ]):
        matched = find_verified_interview(query)
        if not matched and history:
            for turn in reversed(history):
                prev_text = turn.get("content", "")
                prev_matched = find_verified_interview(prev_text)
                if prev_matched:
                    matched = prev_matched
                    break
        if matched:
            name = matched.get("interviewee_name")
            desc = matched.get("description", "")
            quote = matched.get("key_quote", "")
            title = matched.get("title", "")
            if lang == "hi":
                reply = (
                    f"सरल शब्दों में, **{name}** अपने साक्षात्कार **'{title}'** में यह समझाते हैं:\n\n"
                    f"{desc}\n\n"
                    f"उनका मूल संदेश है: *\"{quote}\"*\n\n"
                    f"यह अनुभव हमें सिखाता है कि सामाजिक पूर्वाग्रहों के बावजूद अपनी पहचान पर गर्व करना और गरिमा से जीना संभव है।"
                )
            else:
                reply = (
                    f"In simple words, **{name}**'s interview **'{title}'** explains:\n\n"
                    f"{desc}\n\n"
                    f"Their core message is: *\"{quote}\"*\n\n"
                    f"This experience teaches us that despite societal misunderstandings, it is possible to live authentically with courage, dignity, and self-respect."
                )
            return ("interview_simple_explanation", reply, [f"Watch {name}'s Video", "Other Interviews", "Explore Website"], [matched])

    # 2. Specific verified interview spotlight
    matched_interview = find_verified_interview(query)
    if matched_interview:
        intent = "interview_spotlight"
        summary = format_interview_summary(matched_interview, lang=lang)
        prompts = [
            f"Watch {matched_interview.get('interviewee_name')}'s Video",
            "Browse Other Interviews",
            "Explore Beyond Identity",
        ]
        return (intent, summary, prompts, [matched_interview])

    # 3. Unverified interview query
    if is_unverified_interview_query(query):
        intent = "interview_unverified"
        if lang == "hi":
            reply = (
                "मुझे Beyond Identity के 13 सत्यापित साक्षात्कारों में इस व्यक्ति का कोई साक्षात्कार नहीं मिला। "
                "Beyond Identity पर वर्तमान में 13 वास्तविक साक्षात्कार उपलब्ध हैं जिनमें गौरी सावंत, डॉ. त्रिनेत्रा, चित्रा पालेकर, आर्यन पाशा, आरोही सेन और अन्य प्रेरणास्रोत शामिल हैं। "
                "आप हमारे [वीडियो गैलरी](#tab-videos) में सभी सत्यापित साक्षात्कार देख सकते हैं।"
            )
            prompts = ["Explore 13 Interviews", "Purpose of Beyond Identity", "Contact Support"]
        else:
            reply = (
                "I could not find an interview for that person in Beyond Identity's verified catalog. "
                "Beyond Identity currently hosts **13 verified real-life video interviews** featuring authentic community leaders like Gauri Sawant, Dr. Trinetra Haldar Gummaraju, Chitra Palekar, Aryan Pasha, Aarohi Sen, Grace Banu, and others. "
                "You can explore all verified interviews in our **[Video Interviews Gallery](#tab-videos)**."
            )
            prompts = ["Explore All 13 Interviews", "How Many Interviews?", "What is Beyond Identity?"]
        return (intent, reply, prompts, [])

    # 4. How Many Interviews are Available?
    if any(p in q_norm for p in [
        "how many interviews", "how many videos", "kitne interview", "kitne videos",
        "interviews are available", "list of interviews", "all interviews"
    ]):
        intent = "website_guide_interviews_count"
        if lang == "hi":
            reply = (
                "Beyond Identity पर कुल **13 सत्यापित वास्तविक वीडियो साक्षात्कार** उपलब्ध हैं। "
                "इनमें समुदाय के नेता, वकील, डॉक्टर, माता-पिता और एथलीट (जैसे गौरी सावंत, डॉ. त्रिनेत्रा, चित्रा पालेकर, आर्यन पाशा, आरोही सेन) अपने जीवन के संघर्ष, साहस और अधिकारों की बातें साझा करते हैं। "
                "आप इन सभी को हमारे **[वीडियो इंटरव्यू अनुभाग](#tab-videos)** में देख और सीख सकते हैं।"
            )
            prompts = ["वीडियो इंटरव्यू देखें (#tab-videos)", "वेबसाइट के उद्देश्य", "सहायता प्राप्त करें"]
        else:
            reply = (
                "Beyond Identity features **13 verified real-life video interviews** sharing authentic lived experiences across India: "
                "1. **Aarohi Sen** — Software engineer claiming workplace equality. "
                "2. **Gauri Sawant** — NALSA petitioner building Garima Greh shelters. "
                "3. **Dr. Trinetra Haldar Gummaraju** — Trans surgeon discussing clinical transition. "
                "4. **Arundhati Katju & Dr. Menaka Guruswamy** — Overturning Section 377. "
                "5. **Chitra Palekar** — Parent advocate on embracing queer children. "
                "6. **Aryan Pasha** — Transgender male athlete champion. "
                "7. **Neel Ghosh** — Non-binary corporate equality lead. "
                "8. **Grace Banu** — Dalit & transgender reservations pioneer. "
                "9. **Karthik Subramaniam** — Rural mutual aid & crisis desks. "
                "10. **Dr. Prasad Raj Dandekar** — Queer affirmative mental healthcare. "
                "11. **Anwesa & Megha** — Lesbian couple celebrating marriage equality. "
                "12. **Revathi Natarajan** — IT engineer living proud in Chennai. "
                "13. **Journey (Unknown Gay)** — Self-discovery and overcoming shame. "
                "You can watch all of them in our **[Video Interviews Gallery](#tab-videos)**."
            )
            prompts = ["Watch Interviews (#tab-videos)", "What is Beyond Identity?", "Explore Jobs & Housing"]
        return (intent, reply, prompts, COMMUNITY_INTERVIEWS[:3])

    # 5. What is Beyond Identity? / Purpose of Website
    if any(p in q_norm for p in [
        "what is beyond identity", "purpose of this website", "purpose of beyond identity",
        "what is the purpose of this platform", "about this website", "website ke baare me batao",
        "tell me about beyond identity", "what is this platform"
    ]) and not any(k in q_norm for k in ["who are you", "what can you do"]):
        intent = "website_guide_purpose"
        if lang == "hi":
            reply = (
                "**Beyond Identity** भारत में ट्रांसजेंडर और LGBTQIA+ समुदाय के सशक्तिकरण, सामाजिक सम्मान और भेदभाव मुक्ति के लिए बनाया गया एक समर्पित मंच है "
                "(SE Mini Project-1A, मार्गदर्शक: प्रो. किंटू पटेल)। मंच की मुख्य सुविधाएँ: "
                "1. 🎥 **[13 प्रेरक वीडियो साक्षात्कार](#tab-videos)** जो सच्चाई और हौसले को सामने लाते हैं। "
                "2. 💼 **[समावेशी नौकरियां व गरिमा गृह शेल्टर](#tab-listings)**। "
                "3. ⚖️ **[कानूनी अधिकार सहायता](#tab-awareness)** (ट्रांसजेंडर कानून 2019 और NALSA निर्णय)। "
                "4. 🏥 **[स्वास्थ्य व थेरेपी गाइड](#tab-health)** (आयुष्मान भारत TG कवर)। "
                "5. 🛡️ **[गुमनाम भेदभाव रिपोर्टिंग डेस्क](#tab-report)** और [केस बोर्ड](/cases)। "
                "6. 🤖 **24/7 AI भावनात्मक साथी व मार्गदर्शक**।"
            )
            prompts = ["Explore Interviews (#tab-videos)", "Inclusive Jobs & Shelters", "Legal Rights Desk"]
        else:
            reply = (
                "**Beyond Identity** is a dedicated web platform built to empower the transgender and LGBTQIA+ community across India, eliminate prejudice, and foster understanding without judgment. "
                "Developed as an SE Mini Project-1A (AY 2026-27) guided by Prof. Kintu Patel, the platform provides: "
                "1. 🎥 **[13 Real-Life Community Interviews](#tab-videos)** sharing lived experiences of courage and pride. "
                "2. 💼 **[Inclusive Jobs & Housing Shelters](#tab-listings)** (including Garima Greh homes). "
                "3. ⚖️ **[Legal Rights Awareness](#tab-awareness)** under the Transgender Persons Act 2019 and NALSA (2014). "
                "4. 🏥 **[Healthcare Navigator](#tab-health)** for safe clinical transition and Ayushman Bharat TG cover (₹5 Lakh). "
                "5. 🛡️ **[Anonymous Discrimination Reporting Desk](#tab-report)** and public [Community Case Board](/cases). "
                "6. 🤖 **24/7 AI Guide & Emotional Companion** to answer questions and listen with empathy."
            )
            prompts = ["Explore Interviews (#tab-videos)", "Inclusive Jobs & Housing", "Legal Rights Awareness"]
        return (intent, reply, prompts, COMMUNITY_INTERVIEWS[:2])

    # 6. What Can I Learn from this Platform?
    if any(p in q_norm for p in [
        "what can i learn from this platform", "what can i learn", "what can we learn",
        "what does this website teach", "kya seekh sakte hai"
    ]):
        intent = "website_guide_learning"
        if lang == "hi":
            reply = (
                "**Beyond Identity** पर आप सीख सकते हैं: "
                "1. **सच्ची पहचान:** ट्रांसजेंडर और जेंडर विविधता की वैज्ञानिक और मानवीय समझ। "
                "2. **संवैधानिक अधिकार:** NALSA (2014) और ट्रांसजेंडर कानून 2019 के तहत आत्म-पहचान व TG सर्टिफिकेट प्रक्रिया। "
                "3. **वास्तविक अनुभव:** 13 वीडियो साक्षात्कारों से जीवन के संघर्ष और सफलता की कहानियां। "
                "4. **स्वास्थ्य और सुरक्षित ट्रांजिशन:** HRT दिशा-निर्देश, Tele-MANAS (14416) मानसिक स्वास्थ्य सहायता। "
                "5. **सहानुभूति और सहयोग:** भेदभाव के खिलाफ रिपोर्टिंग और एक अच्छे सहयोगी (ally) बनने के व्यावहारिक तरीके।"
            )
            prompts = ["Explore Interviews (#tab-videos)", "Read Legal Rights", "Learn How to Be an Ally"]
        else:
            reply = (
                "On **Beyond Identity**, you can learn: "
                "1. **Gender Identity with Empathy & Science:** Understand transgender identities, eliminate myths, and recognize that diversity is natural. "
                "2. **Constitutional & Legal Rights:** Learn about self-identification rights under NALSA (2014), protection against discrimination under the Transgender Persons Act 2019, and TG Certificate procedures. "
                "3. **Inspiring Community Wisdom:** Learn from **13 authentic video interviews** with doctors, lawyers, parents, and athletes. "
                "4. **Healthcare & Affirmation:** Learn about clinical HRT pathways, Ayushman Bharat TG cover, and mental health support. "
                "5. **Empowerment & Redressal:** Learn how to be an active ally, find inclusive housing, and report harassment safely."
            )
            prompts = ["Explore Community Interviews (#tab-videos)", "Read Legal Rights", "How to Support Someone"]
        return (intent, reply, prompts, COMMUNITY_INTERVIEWS[:2])

    # 7. Is Being Transgender a Disease?
    if any(p in q_norm for p in [
        "is being transgender a disease", "is transgender a disease", "is being trans a disease",
        "is it a disease", "is it an illness", "is being trans an illness", "is being transgender an illness",
        "kya ye bimari hai", "kya transgender hona bimari hai", "transgender disease", "transgender illness",
        "transgender bimari"
    ]):
        intent = "transgender_not_a_disease"
        if lang == "hi":
            reply = (
                "जी नहीं, ट्रांसजेंडर होना कोई बीमारी नहीं है (यह कोई रोग या मानसिक विकार नहीं है)। "
                "विश्व स्वास्थ्य संगठन (WHO ICD-11) और 'इंडियन साइकियाट्रिक सोसाइटी' ने स्पष्ट रूप से पुष्टि की है कि जेंडर विविधता मानव स्वभाव का एक स्वाभाविक और सामान्य हिस्सा है। "
                "भारत के सर्वोच्च न्यायालय ने NALSA निर्णय (2014) में प्रत्येक व्यक्ति के आत्म-पहचान के अधिकार को मान्यता दी है, "
                "और नेशनल मेडिकल कमीशन (NMC) ने किसी भी प्रकार की 'कन्वर्जन थेरेपी' को पूरी तरह अवैध घोषित किया है। "
                "ट्रांसजेंडर पहचान पूर्ण गरिमा, समानता और सम्मान की हकदार है।"
            )
            prompts = ["Constitutional Rights (NALSA)", "Explore 13 Interviews", "How to Support Someone"]
        else:
            reply = (
                "No, being transgender is not an illness, disease, or mental disorder. "
                "Leading global and national medical authorities, including the World Health Organization (WHO ICD-11) and the Indian Psychiatric Society, affirm that gender diversity is a natural aspect of human variation. "
                "In the landmark NALSA (2014) judgment, the Supreme Court of India recognized the fundamental right to self-identify one's gender without pathological gatekeeping. Furthermore, the National Medical Commission (NMC) has strictly prohibited non-scientific 'conversion therapies'. "
                "Being transgender is a valid, authentic identity deserving of full legal equality, dignity, and respect."
            )
            prompts = ["Constitutional Rights (NALSA)", "Explore 13 Interviews", "How to Support Someone"]
        interviews = [v for v in COMMUNITY_INTERVIEWS if v.get("id") in [3, 10]] or COMMUNITY_INTERVIEWS[:2]
        return (intent, reply, prompts, interviews)

    # 8. How Can I Support Someone Who is Transgender?
    if any(p in q_norm for p in [
        "how can i support someone who is transgender", "how to support a transgender person",
        "how can i support a transgender", "how can we support them", "how to be an ally",
        "how to support someone who is trans", "transgender vyakti ko kaise support karein",
        "transgender ko support kaise kare", "how to support transgender"
    ]):
        intent = "how_to_support_transgender"
        if lang == "hi":
            reply = (
                "किसी ट्रांसजेंडर व्यक्ति का समर्थन करने के लिए संवेदनशीलता, सम्मान और खुला मन सबसे महत्वपूर्ण है। यहाँ 5 व्यावहारिक कदम दिए गए हैं:\n"
                "1. **चुने हुए नाम और Pronouns का सम्मान करें:** हमेशा उनके चुने हुए नाम और सही सर्वनाम (pronouns: he, she, they) का आदर करें। उनके पुराने नाम (deadnaming) का प्रयोग न करें।\n"
                "2. **बिना पूर्वाग्रह के सुनें:** उनके अनुभवों पर विश्वास करें और सहानुभूतिपूर्वक बात सुनें।\n"
                "3. **निजता और मर्यादा का ध्यान रखें:** सर्जरी या शारीरिक बनावट से जुड़े निजी या असहज सवाल न पूछें।\n"
                "4. **भेदभाव और उपहास का विरोध करें:** यदि स्कूल, कार्यस्थल या परिवार में कोई अनुचित टिप्पणी करे, तो उनके पक्ष में खड़े हों।\n"
                "5. **खुद को शिक्षित करें:** ट्रांसजेंडर कानून 2019 और NALSA निर्णय के बारे में जानें और हमारी वेबसाइट पर उपलब्ध 13 वीडियो साक्षात्कारों (जैसे चित्रा पालेकर जी का माता-पिता मार्गदर्शन) से सीखें।"
            )
            prompts = ["Explore Interviews (#tab-videos)", "Read Legal Rights", "Parent Advocate: Chitra Palekar"]
        else:
            reply = (
                "Supporting a transgender person begins with empathy, active listening, and basic human dignity. Here are 5 practical ways you can be a meaningful ally:\n"
                "1. **Respect Chosen Name and Pronouns:** Always use the person's chosen name and correct pronouns (he, she, they, or as preferred). Never use former names (deadnaming).\n"
                "2. **Listen Without Judgment:** Believe their lived experience. You don't need to understand every medical or social detail to show genuine warmth and care.\n"
                "3. **Respect Privacy and Physical Boundaries:** Avoid asking intrusive questions about surgeries, anatomy, or former appearance. Focus on their emotional well-being.\n"
                "4. **Stand Up Against Harassment:** Speak up when someone makes derogatory remarks or misgenders them in social, school, or workplace settings.\n"
                "5. **Educate Yourself and Others:** Learn about legal rights under the Transgender Persons Act 2019, NALSA (2014), and learn from real stories on Beyond Identity (such as parent advocate Chitra Palekar's interview)."
            )
            prompts = ["Explore Interviews (#tab-videos)", "Parent Advocate: Chitra Palekar", "Read Legal Rights"]
        parent_iv = find_verified_interview("chitra palekar")
        interviews = [parent_iv] if parent_iv else COMMUNITY_INTERVIEWS[:1]
        return (intent, reply, prompts, interviews)

    # 9. What does Transgender Identity Mean? / Don't understand transgender identity
    if any(p in q_norm for p in [
        "i don't understand what transgender identity means", "i dont understand what transgender identity means",
        "don't understand what transgender identity means", "dont understand what transgender identity means",
        "can you explain what transgender means", "can you explain transgender identity"
    ]):
        intent = "explain_transgender_identity"
        if lang == "hi":
            reply = (
                "**ट्रांसजेंडर व्यक्ति** वह होते हैं जिनकी आंतरिक जेंडर पहचान (gender identity) उनके जन्म के समय निर्धारित लिंग (sex assigned at birth) से भिन्न होती है:\n\n"
                "• **जन्म के समय लिंग (Sex Assigned at Birth):** जन्म के समय शारीरिक अंगों के आधार पर डॉक्टर द्वारा दी गई पहचान।\n"
                "• **जेंडर पहचान (Gender Identity):** किसी व्यक्ति का अपनी पहचान के प्रति आंतरिक और गहरा अहसास कि वे पुरुष हैं, महिला हैं, या बाइनरी सीमाओं से परे (जैसे नॉन-बाइनरी या तृतीय लिंग)।\n\n"
                "ट्रांसजेंडर होना मानव पहचान का एक स्वाभाविक और गरिमापूर्ण रूप है। भारत के सर्वोच्च न्यायालय के ऐतिहासिक **NALSA निर्णय (2014)** के तहत, अपनी जेंडर पहचान तय करना प्रत्येक नागरिक का मौलिक अधिकार है। Beyond Identity के [वीडियो अनुभाग](#tab-videos) में आप डॉ. त्रिनेत्रा और आर्यन पाशा जैसे समुदाय के नायकों के वास्तविक अनुभव देख सकते हैं।"
            )
            prompts = ["Watch Dr. Trinetra's Story", "Watch Aryan Pasha's Story", "Constitutional Rights (NALSA)"]
        else:
            reply = (
                "A **transgender person** is someone whose deeply felt internal sense of gender (gender identity) differs from the sex assigned to them at birth:\n\n"
                "• **Sex Assigned at Birth:** The physical anatomical classification recorded at birth.\n"
                "• **Gender Identity:** An individual's deeply felt, internal sense of being male, female, or outside the binary (such as non-binary or third gender).\n\n"
                "Being transgender is a natural variation of human identity. Under the Indian Supreme Court's landmark **NALSA judgment (2014)**, every citizen possesses the fundamental constitutional right to self-identify their own gender. On Beyond Identity, you can explore authentic interviews by community trailblazers like trans surgeon Dr. Trinetra Haldar Gummaraju and athlete Aryan Pasha sharing their journeys."
            )
            prompts = ["Watch Dr. Trinetra's Story", "Watch Aryan Pasha's Story", "Constitutional Rights (NALSA)"]
        interviews = [v for v in COMMUNITY_INTERVIEWS if v.get("id") in [3, 6]] or COMMUNITY_INTERVIEWS[:2]
        return (intent, reply, prompts, interviews)

    return None


# =======================================================================
# Emotional Support and Counselling-Style Companion (7-Step Protocol)
# =======================================================================
def detect_emotional_support(query: str, lang: str = "en") -> Optional[tuple[str, str, List[str], List[dict]]]:
    """Understands emotional subtext and provides empathetic, counselling-style reassurance grounded in real interviews."""
    q_norm = query.lower().strip()

    # 1. Feeling Different / "Why am I like this?"
    if any(p in q_norm for p in [
        "i feel different", "feel different from everyone", "feel different from others",
        "why am i like this", "why am i different", "why was i born like this",
        "sabse alag lagta hai", "main alag kyu hu", "main aisa kyu hu", "main aisi kyu hu"
    ]):
        intent = "emotional_feeling_different"
        if lang == "hi":
            reply = (
                "यह पूरी तरह स्वाभाविक है कि आप खुद को दूसरों से अलग पाकर उलझन या अकेलापन महसूस करें, "
                "और 'मैं ऐसा क्यों हूँ?' जैसा सवाल मन में आना भी लाजिमी है। लेकिन कृपया यह विश्वास रखें: आप में कुछ भी गलत, टूटा हुआ या शर्मनाक नहीं है। "
                "हर व्यक्ति की अपनी अनूठी सच्चाई होती है और आपकी पहचान पूरे सम्मान की हकदार है। "
                "हमारी वेबसाइट पर उपलब्ध इंटरव्यू 'Journey' में भी व्यक्ति ने मुंबई में खुद को अलग महसूस करने के बाद कहा था: "
                "\"Freedom is the courage to live authentically without hiding in fear or shame.\" "
                "यदि आप सहज हों, तो हाल ही में किस बात ने आपको ऐसा महसूस कराया?"
            )
            prompts = ["Watch Journey Interview", "Tele-MANAS: 14416", "What is Gender Identity?"]
        else:
            reply = (
                "It can feel deeply isolating when you feel different from everyone else, and it is completely natural to wonder, 'Why am I like this?' "
                "Please know with absolute certainty: there is nothing broken, shameful, or wrong with who you are. "
                "Your individuality and identity deserve dignity, patience, and respect. "
                "In our website interview *Journey*, the interviewee reflects on this exact feeling before finding pride: "
                "*\"Freedom is the courage to live authentically without hiding in fear or shame.\"* "
                "You are never alone in feeling this way. If you feel comfortable sharing, what has been making you feel this way lately?"
            )
            prompts = ["Watch Journey Interview", "Explore Community Stories", "Tele-MANAS: 14416"]
        interviews = get_interviews_for_emotion_or_topic("feeling_different", top_k=2)
        return (intent, reply, prompts, interviews)

    # 2. Afraid People Will Judge Me
    if any(p in q_norm for p in [
        "afraid people will judge", "afraid of being judged", "scared people will judge",
        "fear of judgment", "what if people judge me", "darr lagta hai log kya",
        "log judge karenge", "log kya sochenge", "log kya kahenge"
    ]):
        intent = "emotional_afraid_of_judgment"
        if lang == "hi":
            reply = (
                "लोगों द्वारा आंके जाने (judgment) का डर बहुत स्वाभाविक और मानवीय है। "
                "दूसरों की राय की चिंता मन पर भारी बोझ बन सकती है। "
                "लेकिन याद रखें: आपकी अंतर्निहित गरिमा और मूल्य किसी और की सोच या पूर्वाग्रह पर निर्भर नहीं करते। "
                "हमारी वेबसाइट पर सॉफ्टवेयर इंजीनियर और एडवोकेट आरोही सेन ने साझा किया है कि समाज के डर पर काबू पाकर ही गरिमा हासिल होती है: "
                "\"True transition isn't just medical or legal — it's claiming your rightful place in society without fear.\" "
                "क्या कोई विशेष परिस्थिति है जिसने आपके मन में यह डर बढ़ाया है?"
            )
            prompts = ["Watch Aarohi Sen's Story", "Tele-MANAS: 14416", "Community Support"]
        else:
            reply = (
                "It is completely understandable to feel afraid that people will judge you. "
                "Worrying about other people's reactions can feel like an immense weight to carry. "
                "Please remember that your intrinsic worth, dignity, and truth are not defined by anyone else's prejudices. "
                "Many leaders on Beyond Identity faced severe social prejudice before standing tall. In her interview, tech advocate Aarohi Sen reminds us: "
                "*\"True transition isn't just medical or legal — it's claiming your rightful place in society without fear.\"* "
                "You deserve acceptance just as you are. Are you feeling this fear in a particular place, like family, school, or work?"
            )
            prompts = ["Watch Aarohi Sen's Interview", "Tele-MANAS: 14416", "Find Safe Spaces"]
        interviews = get_interviews_for_emotion_or_topic("afraid_of_judgment", top_k=2)
        return (intent, reply, prompts, interviews)

    # 3. Feeling Alone / Nobody Understands Me
    if any(p in q_norm for p in [
        "i feel alone", "i feel so alone", "i feel lonely", "nobody understands me",
        "no one understands me", "i have no one", "akela lagta hai", "akela feel hota hai",
        "koi nahi samajhta", "koi sath nahi hai", "feeling alone"
    ]):
        intent = "emotional_feeling_alone"
        if lang == "hi":
            reply = (
                "यह महसूस होना कि आप बिल्कुल अकेले हैं या कोई आपकी बात नहीं समझता, दिल को बहुत भारी कर देता है। "
                "लेकिन भले ही इस पल ऐसा महसूस हो रहा हो, आप वास्तव में अकेले नहीं हैं। "
                "पूरे भारत में एक ऐसा समुदाय है जो आपकी भावनाओं को समझता है और आपकी गरिमा का सम्मान करता है। "
                "गौरी सावंत जी ने गरिमा गृह शेल्टर बनाए ताकि किसी को अकेलेपन में भटकना न पड़े। "
                "अगर आप किसी संवेदनशील काउंसलर से बात करना चाहें, तो Tele-MANAS (14416) और कम्युनिटी हेल्पलाइन (868989330) 24/7 उपलब्ध हैं। क्या आप अपने मन की बात साझा करना चाहेंगे?"
            )
            prompts = ["Watch Gauri Sawant's Story", "Call Tele-MANAS: 14416", "Helpline: 868989330"]
        else:
            reply = (
                "Feeling alone and believing that nobody understands what you are going through is one of the hardest emotional burdens to carry. "
                "Please take a deep breath and know: even when it feels dark, you are not alone. "
                "There is an entire vibrant community and many allies across India who share your journey and care about your well-being. "
                "Pioneering trans mother Gauri Sawant built shelter homes specifically so that no youth would ever have to face the world alone. "
                "You can also speak with compassionate counsellors at Tele-MANAS on **14416** or our community line **868989330** anytime. What is weighing most heavily on your mind right now?"
            )
            prompts = ["Watch Gauri Sawant's Interview", "Call Tele-MANAS: 14416", "Helpline: 868989330"]
        interviews = get_interviews_for_emotion_or_topic("feeling_alone", top_k=2)
        return (intent, reply, prompts, interviews)

    # 4. What will my family think? / Family Acceptance Worries
    if any(p in q_norm for p in [
        "what will my family think", "what will my parents think", "will my family accept me",
        "will my parents accept me", "afraid to tell my family", "scared to tell my parents",
        "gharwale kya sochenge", "parivar accept karega", "mummy papa kya sochenge"
    ]):
        intent = "emotional_family_acceptance"
        if lang == "hi":
            reply = (
                "परिवार की प्रतिक्रिया और स्वीकार्यता की चिंता सबसे संवेदनशील और भावुक चिंताओं में से एक है। "
                "अपने प्रियजनों का प्यार और समझ चाहना पूरी तरह स्वाभाविक है। "
                "सबसे पहले आपकी भावनात्मक और शारीरिक सुरक्षा आती है—जल्दबाजी करने की कोई आवश्यकता नहीं है। "
                "हमारी वेबसाइट पर LGBTQ+ पैरेंट एडवोकेट चित्रा पालेकर जी अपने साक्षात्कार में बताती हैं: "
                "\"Acceptance begins at home. When parents stand with pride, no child has to face the world alone.\" "
                "वे समझाती हैं कि माता-पिता को भी सामाजिक पूर्वाग्रहों को भूलने में समय और सही जानकारी की जरूरत होती है। क्या आपके पास कोई ऐसा दोस्त है जो आपकी बात समझता हो?"
            )
            prompts = ["Watch Chitra Palekar's Story", "Tips for Family Discussion", "Support Groups"]
        else:
            reply = (
                "Worrying about what your family will think or whether they will accept you is deeply emotional and frightening. "
                "It is natural to want the love and blessing of the people closest to you. "
                "Your physical and emotional safety must always come first; there is never any deadline or obligation to come out before you feel secure. "
                "In her moving interview on Beyond Identity, pioneering parent advocate Chitra Palekar reminds us: "
                "*\"Acceptance begins at home. When parents stand with pride, no child has to face the world alone.\"* "
                "She shares how families often need time, empathy, and education to unlearn societal biases. Do you have a trusted confidant or friend beside you right now?"
            )
            prompts = ["Watch Chitra Palekar's Interview", "Family Guidance Resources", "Tele-MANAS: 14416"]
        interviews = get_interviews_for_emotion_or_topic("family_acceptance", top_k=2)
        return (intent, reply, prompts, interviews)

    # 5. Shame or Embarrassment About Identity
    if any(p in q_norm for p in [
        "embarrassed about my identity", "embarrassed of who i am", "i feel ashamed",
        "feel shame", "ashamed of who i am", "shame about my gender", "sharm aati hai",
        "sharminda hu", "sharmindagi"
    ]):
        intent = "emotional_shame_embarrassment"
        if lang == "hi":
            reply = (
                "अपनी पहचान को लेकर शर्म या झिझक महसूस होना अक्सर समाज द्वारा दी गई गलत सोच और पूर्वाग्रहों का परिणाम होता है, "
                "आपकी असली पहचान का नहीं। "
                "आप जैसे हैं, पूरी तरह से सम्मानीय, सच्चे और गरिमापूर्ण हैं। "
                "डॉ. प्रसाद राज दांडेकर हमारे मंच पर बताते हैं कि कैसे 'माइनॉरिटी स्ट्रेस' आत्म-ग्लानि पैदा करता है, और सही थेरेपी व प्यार से कैसे हौसला मिलता है: "
                "\"Affirmative mental healthcare saves lives by honoring identity rather than pathologizing love.\" "
                "आपको अपनी पहचान के लिए कभी भी शर्मिंदा होने की जरूरत नहीं है। क्या आप बताना चाहेंगे कि इस भावना की शुरुआत कैसे हुई?"
            )
            prompts = ["Watch Dr. Prasad Dandekar's Story", "Tele-MANAS: 14416", "Learn About Minority Stress"]
        else:
            reply = (
                "Feeling embarrassed or ashamed of your identity is an experience many queer and trans individuals go through—not because anything about you is wrong, but because society has unfairly conditioned people to hide. "
                "Please hear this clearly: there is zero reason for shame. Who you are is authentic, valuable, and worthy of dignity. "
                "On our website, Dr. Prasad Raj Dandekar speaks on overcoming internalized stigma and minority stress: "
                "*\"Affirmative mental healthcare saves lives by honoring identity rather than pathologizing love.\"* "
                "You deserve to walk with your head held high. If you're open to it, what has been making you feel embarrassed recently?"
            )
            prompts = ["Watch Dr. Prasad Dandekar's Interview", "Tele-MANAS: 14416", "Affirmative Mental Health"]
        interviews = get_interviews_for_emotion_or_topic("shame_or_embarrassment", top_k=2)
        return (intent, reply, prompts, interviews)

    # 6. Will People Ever Accept Me? / Social Acceptance
    if any(p in q_norm for p in [
        "will people ever accept me", "will anyone accept me", "will society accept me",
        "will i ever find acceptance", "kya log accept karenge", "kya samaj accept karega"
    ]):
        intent = "emotional_social_acceptance"
        if lang == "hi":
            reply = (
                "यह सवाल बहुत गहरा और संवेदनशील है। सामाजिक बदलाव में समय लगता है, लेकिन यह सच है कि दुनिया में ऐसे बहुत से लोग, संगठन और समुदाय हैं जो आपको तहे दिल से स्वीकार और प्यार करेंगे। "
                "कोलकाता की अन्वेषा और मेघा का उदाहरण देखें, जिन्होंने शादी करके समाज को दिखाया: "
                "\"Love needs no societal validation to be sacred, joyful, and eternal.\" "
                "स्वीकार्यता सबसे पहले आत्म-स्वीकृति से शुरू होती है, और जैसे-जैसे आप अपने प्रति सच्चे होते हैं, आपको सही लोग भी मिलते हैं।"
            )
            prompts = ["Watch Anwesa & Megha's Story", "Find Affirming Communities", "Tele-MANAS: 14416"]
        else:
            reply = (
                "Asking whether people will ever accept you is a very honest and touching question. "
                "While societal change can feel slow, there are countless communities, loving allies, and inclusive workplaces across India that embrace transgender and queer individuals with open arms. "
                "Consider Anwesa & Megha, whose wedding in Kolkata is featured on our platform: "
                "*\"Love needs no societal validation to be sacred, joyful, and eternal.\"* "
                "Or Aryan Pasha, who won national medals and respect as an out trans athlete. You will find people who cherish you for who you are. What does feeling accepted mean most to you right now?"
            )
            prompts = ["Watch Anwesa & Megha's Interview", "Watch Aryan Pasha's Interview", "Community Groups"]
        interviews = get_interviews_for_emotion_or_topic("social_acceptance", top_k=2)
        return (intent, reply, prompts, interviews)

    # 7. Interview Relatability
    if any(p in q_norm for p in [
        "watched an interview", "saw an interview", "interview and realized",
        "interview similar to mine", "interview resonated"
    ]):
        intent = "emotional_interview_relatability"
        if lang == "hi":
            reply = (
                "यह सुनना बहुत ही खूबसूरत और प्रेरणादायक है। जब हम किसी और को अपने जैसे अनुभवों और संघर्षों से गुजरते हुए देखते हैं, "
                "तो दिल को बहुत सुकून मिलता है कि हम अकेले नहीं हैं। "
                "यही Beyond Identity के साक्षात्कारों का मुख्य उद्देश्य है—समुदाय को शक्ति और मार्गदर्शन देना। "
                "आपने कौन सा इंटरव्यू देखा, और उसके किस हिस्से ने आपके दिल को सबसे ज्यादा छुआ?"
            )
            prompts = ["Explore All 13 Interviews", "Talk to the Assistant", "Share Your Thoughts"]
        else:
            reply = (
                "That is such a profound and heartening moment. Realizing that someone else has walked a similar path and felt the exact emotions you feel can be immensely validating and comforting. "
                "That is the core mission of Beyond Identity's real-life community interviews—to help you realize your truth is shared, resilient, and deeply valuable. "
                "Which interview did you watch, and what part resonated most with your own story?"
            )
            prompts = ["Explore All 13 Interviews", "Talk Through Your Feelings", "Community Support"]
        return (intent, reply, prompts, COMMUNITY_INTERVIEWS[:2])

    # 8. Don't know whom to talk to
    if any(p in q_norm for p in [
        "i don't know whom to talk to", "i dont know who to talk to", "who to talk to",
        "kisse baat karu", "kisse baat karein", "whom should i talk to"
    ]):
        intent = "emotional_seeking_someone_to_talk_to"
        if lang == "hi":
            reply = (
                "जब मन में उलझनें हों और समझ न आए कि किससे बात करें, तो भारीपन महसूस होना स्वाभाविक है। "
                "आप यहाँ मुझसे बात कर सकते हैं—मैं धैर्य और सम्मान से सुनने के लिए तैयार हूँ। "
                "यदि आप किसी वास्तविक व्यक्ति से गोपनीय बातचीत करना चाहते हैं: "
                "1. **Tele-MANAS:** **14416** (मुफ़्त, 24/7 मानसिक स्वास्थ्य हेल्पलाइन)। "
                "2. **कम्युनिटी हेल्पलाइन:** **868989330**। "
                "आप बिना किसी झिझक के यहाँ जो चाहें साझा कर सकते हैं। क्या आप कुछ बताना चाहेंगे?"
            )
            prompts = ["Call Tele-MANAS: 14416", "Call Helpline: 868989330", "Explore Interviews"]
        else:
            reply = (
                "When your mind is overwhelmed and you aren't sure who is safe to open up to, it can feel frightening. "
                "Please know you can talk to me right here—I am here to listen with patience, care, and zero judgment. "
                "If you would like to speak with a trained, compassionate human voice in confidence: "
                "1. **Tele-MANAS:** Call **14416** (free, 24/7 confidential mental health support). "
                "2. **Community Helpline:** Call **868989330** (24/7 direct peer and crisis guidance). "
                "You don't have to carry your thoughts alone. What's been on your mind lately?"
            )
            prompts = ["Call Tele-MANAS: 14416", "Call Helpline: 868989330", "Explore Interviews"]
        return (intent, reply, prompts, [])

    return None


def answer_chatbot_query(
    db: Session,
    request: schemas.ChatbotQueryRequest,
    current_user: Optional[models.User] = None,
) -> schemas.ChatbotQueryResponse:
    """
    Main Chatbot processing logic.
    Analyzes intent, searches live database listings, consults legal repository or Claude,
    and returns a structured response conforming to friendly chatbot rules.
    """
    query = request.query.strip()
    lang = (request.language or "en").lower().strip()
    if lang not in ("en", "hi"):
        lang = "en"

    # Detect language of current query to prompt language switch if mismatch occurs
    detected_lang = detect_query_language(query)
    lang_switch_prompt = None
    if detected_lang and detected_lang != lang:
        if lang == "en" and detected_lang == "hi":
            lang_switch_prompt = "Kya aap language badalna chahenge? (Switch to हिंदी?)"
        elif lang == "hi" and detected_lang == "en":
            lang_switch_prompt = "Would you like to switch to English? (English mein badalna chahenge?)"

    # Count total verified database records
    total_records = db.query(models.Listing).filter(
        models.Listing.status == models.VerificationStatus.verified
    ).count()

    # Check for User Cases if relevant
    user_cases: List[schemas.ChatbotCaseOut] = []
    if current_user and ("my case" in query.lower() or "my report" in query.lower() or "status" in query.lower()):
        cases = db.query(models.IncidentReport).filter(
            models.IncidentReport.user_id == current_user.id
        ).order_by(models.IncidentReport.created_at.desc()).limit(3).all()

        for c in cases:
            user_cases.append(
                schemas.ChatbotCaseOut(
                    id=c.id,
                    title=c.title,
                    incident_type=c.incident_type.value if hasattr(c.incident_type, "value") else str(c.incident_type),
                    status=c.status.value if hasattr(c.status, "value") else str(c.status),
                    urgency_level=c.urgency_level.value if hasattr(c.urgency_level, "value") else str(c.urgency_level),
                    location_city=c.location_city,
                    location_state=c.location_state,
                    assigned_ngo=c.assigned_ngo,
                    case_notes=c.case_notes,
                    created_at=c.created_at.strftime("%Y-%m-%d %H:%M"),
                )
            )

    # Step 0: Immediate Crisis & Distress Check (Safety First)
    from app.data import knowledge_base
    if knowledge_base.is_crisis_query(query):
        safety_ans = knowledge_base.CRISIS_SAFETY_ANSWER_HI if lang == "hi" else knowledge_base.CRISIS_SAFETY_ANSWER
        return schemas.ChatbotQueryResponse(
            reply=safety_ans,
            intent="emergency_crisis",
            suggestions=[],
            user_cases=user_cases,
            suggested_prompts=["Tele-MANAS: 14416", "Emergency: 112", "Helpline: 868989330"] if lang == "en" else ["Tele-MANAS: 14416", "आपातकालीन: 112", "हेल्पलाइन: 868989330"],
            total_database_records=total_records,
            language=lang,
            detected_language=detected_lang,
            language_switch_prompt=lang_switch_prompt,
            suggested_interviews=[],
        )

    # Step 1: Multi-Turn Context Continuity Check
    multiturn_res = detect_multiturn_context(query, request.history or [], lang=lang)
    if multiturn_res:
        mt_intent, mt_reply, mt_prompts, mt_interviews = multiturn_res
        return schemas.ChatbotQueryResponse(
            reply=mt_reply,
            intent=mt_intent,
            suggestions=[],
            user_cases=user_cases,
            suggested_prompts=mt_prompts,
            total_database_records=total_records,
            language=lang,
            detected_language=detected_lang,
            language_switch_prompt=lang_switch_prompt,
            suggested_interviews=mt_interviews,
        )

    # Step 2: Website Guide & Real Interview Q&A Check
    guide_res = detect_website_guide_or_interview(query, history=request.history or [], lang=lang)
    if guide_res:
        g_intent, g_reply, g_prompts, g_interviews = guide_res
        return schemas.ChatbotQueryResponse(
            reply=g_reply,
            intent=g_intent,
            suggestions=[],
            user_cases=user_cases,
            suggested_prompts=g_prompts,
            total_database_records=total_records,
            language=lang,
            detected_language=detected_lang,
            language_switch_prompt=lang_switch_prompt,
            suggested_interviews=g_interviews,
        )

    # Step 3: Emotional Support and Counselling-Style Companion Check
    emo_res = detect_emotional_support(query, lang=lang)
    if emo_res:
        e_intent, e_reply, e_prompts, e_interviews = emo_res
        return schemas.ChatbotQueryResponse(
            reply=e_reply,
            intent=e_intent,
            suggestions=[],
            user_cases=user_cases,
            suggested_prompts=e_prompts,
            total_database_records=total_records,
            language=lang,
            detected_language=detected_lang,
            language_switch_prompt=lang_switch_prompt,
            suggested_interviews=e_interviews,
        )

    # Step 4: Check Built-in Q&A Knowledge Base
    kb_match = knowledge_base.find_best_match(query, threshold=0.65, lang=lang)
    if kb_match:
        qid = kb_match.get("id")
        reply = kb_match["answer"]
        suggestions: List[schemas.ChatbotItemOut] = []
        suggested_interviews: List[Dict[str, Any]] = []

        tag = kb_match.get("tag") or kb_match.get("category")

        if qid == "crisis_safety" or tag in ("self_harm_support", "crisis_safety"):
            intent = "emergency_crisis"
            reply = (
                kb_match.get("answer") or
                "You are not alone. Call Tele-MANAS 14416 (free, 24/7 mental health support). "
                "If you are in immediate danger, call 112. "
                "Direct community crisis support is also available 24/7 at 868989330, and NALSA free legal aid at 15100."
            )
            suggested_prompts = ["Tele-MANAS: 14416", "Emergency: 112", "Helpline: 868989330"]

        elif tag == "greeting" or qid == 1:
            intent = "chitchat_greeting"
            suggested_prompts = []
        elif tag == "how_are_you" or qid == 2:
            intent = "chitchat_howareyou"
            suggested_prompts = []
        elif tag == "user_fine" or qid == 3:
            intent = "chitchat_user_good"
            suggested_prompts = []
        elif tag == "user_sad" or qid == 4:
            intent = "chitchat_mood_sad"
            suggested_prompts = ["Tele-MANAS: 14416", "Direct Helpline: 868989330"]
        elif tag == "who_are_you" or qid == 5:
            intent = "chitchat_identity"
            suggested_prompts = []
        elif qid == 6:
            intent = "chitchat_capabilities"
            suggested_prompts = []
        elif tag == "thanks" or qid == 7:
            intent = "chitchat_thanks"
            suggested_prompts = []
        elif tag in ("good_morning", "good_afternoon", "good_evening") or qid == 8:
            intent = "chitchat_time_greeting"
            suggested_prompts = []
        elif tag == "good_night":
            intent = "good_night"
            suggested_prompts = []
        elif tag == "goodbye" or qid == 9:
            intent = "chitchat_farewell"
            suggested_prompts = []
        elif qid == 10:
            intent = "chitchat_bot_identity"
            suggested_prompts = []
        elif qid == 11:
            intent = "chitchat_acknowledgment"
            suggested_prompts = []
        elif qid == 22:
            intent = "chitchat_doing"
            suggested_prompts = []
        elif qid == 23:
            intent = "confused_need_help"
            suggested_prompts = ["What rights do transgender persons have in India?", "Garima Greh Shelters"]
        elif qid == 24:
            intent = "basics_terminology"
            suggested_prompts = ["What rights do transgender persons have in India?", "How to get TG Certificate"]
        elif tag == "user_is_transgender":
            intent = "user_is_transgender"
            suggested_prompts = ["What are my legal rights in India?", "How to get TG Certificate", "Find Community Support"]
        elif tag == "just_realised_identity":
            intent = "just_realised_identity"
            suggested_prompts = ["Gender Identity Basics", "LGBTQIA+ Affirmative Counsellors", "Peer Support Groups"]
        elif tag == "afraid_to_come_out":
            intent = "afraid_to_come_out"
            suggested_prompts = ["Tips for Talking to Family", "Support Groups", "Tele-MANAS: 14416"]
        elif tag == "family_rejected":
            intent = "family_rejected"
            suggested_prompts = ["Garima Greh Shelters", "Emergency: 112", "Helpline: 868989330"]
            suggestions = search_listings_in_db(db=db, intent="housing", query=query, limit=3)
        elif tag == "bullied_discriminated":
            intent = "bullied_discriminated"
            suggested_prompts = ["Report Discrimination Tab", "Free Legal Aid: 15100", "Workplace Protections"]
        elif tag == "feeling_unsafe":
            intent = "emergency_crisis"
            suggested_prompts = ["Emergency: 112", "Tele-MANAS: 14416", "Helpline: 868989330"]
        elif tag == "mental_health_support":
            intent = "healthcare"
            suggested_prompts = ["Tele-MANAS: 14416", "Find Affirming Therapists", "Helpline: 868989330"]
            suggestions = search_listings_in_db(db=db, intent="healthcare", query="mental health counsellor therapy", limit=3)
        elif tag == "legal_rights" or qid in (12, 13, 16):
            intent = "legal_rights"
            suggested_prompts = ["Free Legal Aid: 15100", "TG Certificate Portal", "Report Discrimination"]
        elif tag == "id_certificate":
            intent = "legal_rights"
            suggested_prompts = ["National Portal Link", "Aadhaar / Document Update", "DM Certificate Steps"]
        elif tag == "job_support" or qid == 14:
            intent = "employment"
            suggested_prompts = ["Find Inclusive Jobs", "File Complaint with Complaints Officer"]
            suggestions = search_listings_in_db(db=db, intent="employment", query=query, limit=3)
        elif qid == 15:
            intent = "incident_report"
            suggested_prompts = ["Report Discrimination Tab", "Emergency: 112", "Free Legal Aid: 15100"]
        elif qid == 17:
            intent = "housing"
            suggested_prompts = ["Garima Greh Shelters", "Tenant Protections Section 12"]
            suggestions = search_listings_in_db(db=db, intent="housing", query=query, limit=3)
        elif tag == "healthcare_support" or qid in (18, 19):
            intent = "healthcare"
            suggested_prompts = ["Ayushman Bharat TG Plus", "HRT Medical Guidance"]
            suggestions = search_listings_in_db(db=db, intent="healthcare", query=query, limit=3)
        elif tag == "government_schemes" or qid == 20:
            intent = "scholarship_schemes"
            suggested_prompts = ["SMILE Scheme Portal", "Skill Training PM-DAKSH"]
            suggestions = search_listings_in_db(db=db, intent="scholarship_schemes", query=query, limit=3)
        elif tag == "ally_how_to_support":
            intent = "ally_how_to_support"
            suggested_prompts = ["Tips for Friends & Family", "Terminology Guide", "Why Pronouns Matter"]
        elif tag == "pronouns_name":
            intent = "pronouns_name"
            suggested_prompts = ["Why Pronouns Matter", "Name Change on Documents", "Deadnaming Explained"]
        elif tag == "community_support":
            intent = "community"
            suggested_prompts = ["Find NGO Partners", "Community Mentorship", "Volunteer Opportunities"]
            suggestions = search_listings_in_db(db=db, intent="community", query=query, limit=3)
        elif tag == "compliment_bot":
            intent = "chitchat_compliment"
            suggested_prompts = []
        elif qid == 21:
            intent = "emergency_crisis"
            reply = (
                "You are not alone. Call Tele-MANAS 14416 (free, 24/7 mental health support). "
                "If you are in immediate danger, call 112. "
                "Direct community crisis support is also available 24/7 at 868989330."
            )
            suggested_prompts = ["Call Tele-MANAS: 14416", "Emergency: 112"]
        elif tag in ("identity_gay", "user_is_gay") or qid == 25:
            intent = "user_is_gay"
            suggested_prompts = ["Section 377 Legal Rights", "Humsafar Trust Support", "Tele-MANAS: 14416"] if lang == "en" else ["धारा 377 और अधिकार", "हमसफ़र ट्रस्ट सहायता", "Tele-MANAS: 14416"]
        elif tag in ("identity_lesbian", "user_is_lesbian") or qid == 26:
            intent = "user_is_lesbian"
            suggested_prompts = ["Sappho for Equality & Support", "Legal Protections against Harassment", "Safe Housing"] if lang == "en" else ["सैफो फॉर इक्वैलिटी", "कानूनी अधिकार व सुरक्षा", "गरिमा गृह शेल्टर"]
        elif tag in ("identity_bisexual", "user_is_bisexual") or qid == 27:
            intent = "user_is_bisexual"
            suggested_prompts = ["LGBTQ+ Community Support", "Queer Affirmative Therapists", "Coming Out Advice"] if lang == "en" else ["कम्युनिटी सपोर्ट ग्रुप्स", "काउंसलिंग व मानसिक स्वास्थ्य", "परिवार से बात करने के टिप्स"]
        elif tag in ("identity_transgender", "user_is_transgender"):
            intent = "user_is_transgender"
            suggested_prompts = ["What are my legal rights in India?", "How to get TG Certificate", "Garima Greh Shelters"] if lang == "en" else ["भारत में मेरे क्या अधिकार हैं?", "TG सर्टिफिकेट कैसे बनवाएँ?", "गरिमा गृह शेल्टर"]
        elif tag in ("identity_other", "user_is_nonbinary_queer"):
            intent = "user_is_nonbinary_queer"
            suggested_prompts = ["Pronouns & Terminology Guide", "Transgender Persons Act 2019", "Affirming Doctors"] if lang == "en" else ["Pronouns और पहचान गाइड", "ट्रांसजेंडर कानून 2019", "सपोर्ट ग्रुप्स"]
        elif tag in ("identity_confused", "confused_need_help") or qid == 23:
            intent = "confused_need_help"
            suggested_prompts = ["Gender Identity Basics", "LGBTQ+ Affirmative Therapists", "Tele-MANAS: 14416"] if lang == "en" else ["जेंडर पहचान की बुनियादी बातें", "काउंसलर सहायता", "Tele-MANAS: 14416"]
        elif tag == "scared":
            intent = "scared"
            suggested_prompts = ["Tele-MANAS: 14416 (24/7)", "Crisis Support: 868989330", "Emergency: 112"] if lang == "en" else ["Tele-MANAS: 14416 (24/7)", "सपोर्ट लाइन: 868989330", "आपातकालीन: 112"]
        elif tag.startswith("family_"):
            intent = tag
            suggested_prompts = ["Tips for Friends & Family", "NGO Parents Support Groups", "Transgender Persons Act 2019"] if lang == "en" else ["माता-पिता के लिए टिप्स", "NGO सपोर्ट ग्रुप्स", "ट्रांसजेंडर कानून 2019"]
        elif tag in ("crisis_self_harm", "self_harm_support", "crisis_safety"):
            intent = "emergency_crisis"
            suggested_prompts = ["Tele-MANAS: 14416", "Emergency: 112", "Helpline: 868989330"]
        elif tag == "user_is_asexual" or qid == 28:
            intent = "user_is_asexual"
            suggested_prompts = ["Indian Aces Community", "Queer Support Groups", "Affirming Mental Health"]
        elif tag in ("user_is_nonbinary_queer", "user_is_intersex") or qid in (29, 30):
            intent = "user_is_nonbinary_queer"
            suggested_prompts = ["Transgender Persons Act 2019", "Pronouns & Identity Guide", "Affirming Doctors"]
        elif tag == "section_377_legal" or qid == 31:
            intent = "section_377_legal"
            suggested_prompts = ["NALSA Legal Aid: 15100", "High Court Protection Writs", "Police Protection Guidelines"]
        elif tag == "same_sex_marriage_relationships" or qid == 32:
            intent = "same_sex_marriage_relationships"
            suggested_prompts = ["Cohabitation Rights in India", "Supreme Court Supriyo Ruling", "High Court Protection"]
        elif tag == "coming_out_advice" or qid == 33:
            intent = "coming_out_advice"
            suggested_prompts = ["Coming Out Safely Guide", "Tele-MANAS: 14416", "Find Local Support Groups"]
        elif tag == "forced_marriage_protection" or qid == 34:
            intent = "forced_marriage_protection"
            suggested_prompts = ["Emergency: 112", "NALSA Free Legal Aid: 15100", "High Court Protection Writ"]
        elif tag == "conversion_therapy_ban" or qid == 35:
            intent = "conversion_therapy_ban"
            suggested_prompts = ["NMC Conversion Therapy Ban", "Report Unethical Doctors", "Tele-MANAS: 14416"]
        elif tag == "lgbtq_safe_sex_prep" or qid == 36:
            intent = "lgbtq_safe_sex_prep"
            suggested_prompts = ["NACO Helpline: 1097", "Free HIV Testing Centres", "Humsafar Trust Health Clinics"]
        elif tag == "lgbtq_community_groups" or qid in (37, 38, 39, 40):
            intent = "lgbtq_community_groups"
            suggested_prompts = ["Humsafar Trust (Mumbai/Delhi)", "Sappho for Equality (Kolkata)", "Queer Community Helplines"]
        else:
            intent = tag or kb_match.get("category", "general")
            suggested_prompts = []

        return schemas.ChatbotQueryResponse(
            reply=reply,
            intent=intent,
            suggestions=suggestions,
            user_cases=user_cases,
            suggested_prompts=suggested_prompts,
            total_database_records=total_records,
            language=lang,
            detected_language=detected_lang,
            language_switch_prompt=lang_switch_prompt,
            suggested_interviews=suggested_interviews,
        )

    # Step 1: Secondary Intent and Live Database Search Fallback
    intent = detect_intent(query)
    suggestions = []
    if intent in ("employment", "housing", "healthcare", "scholarship_schemes"):
        suggestions = search_listings_in_db(
            db=db,
            intent=intent,
            query=query,
            category_filter=request.category_filter,
            location_filter=request.location_filter,
            limit=4,
        )

    if intent == "out_of_scope":
        reply = "Sorry, I don't have a verified answer for that yet. You can try one of the topics above, or call the helpline for direct help."
        suggested_prompts = [
            "I am gay — what are my rights?",
            "What rights do transgender persons have in India?",
            "How do I get a Transgender Certificate / ID?",
            "24/7 Helpline: 868989330",
        ]
        return schemas.ChatbotQueryResponse(
            reply=reply,
            intent=intent,
            suggestions=[],
            user_cases=user_cases,
            suggested_prompts=suggested_prompts,
            total_database_records=total_records,
            language=lang,
            detected_language=detected_lang,
            language_switch_prompt=lang_switch_prompt,
            suggested_interviews=[],
        )

    # Curated Knowledge & Database Engine Fallback
    reply, suggested_prompts = generate_curated_reply(intent, query, suggestions)

    # If the response reached generic fallback, use the requested fallback message
    if intent == "general" and not suggestions:
        reply = "Sorry, I don't have a verified answer for that yet. You can try one of the topics above, or call the helpline for direct help."
        suggested_prompts = [
            "I am gay — what are my rights?",
            "What rights do transgender persons have in India?",
            "How do I get a Transgender Certificate / ID?",
            "24/7 Helpline: 868989330",
        ]

    return schemas.ChatbotQueryResponse(
        reply=reply,
        intent=intent,
        suggestions=suggestions,
        user_cases=user_cases,
        suggested_prompts=suggested_prompts,
        total_database_records=total_records,
        language=lang,
        detected_language=detected_lang,
        language_switch_prompt=lang_switch_prompt,
        suggested_interviews=[],
    )

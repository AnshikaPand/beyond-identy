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

    # H. Farewell / Goodbye
    farewell_keywords = [
        "bye", "goodbye", "see you", "cya", "good night", "take care", "tata"
    ]
    if _matches_any(farewell_keywords, q):
        return "chitchat_farewell"

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

    # Step 0: Check Built-in Q&A Knowledge Base first (Answers instantly)
    from app.data import knowledge_base
    kb_match = knowledge_base.find_best_match(query, threshold=0.65)

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

    if kb_match:
        qid = kb_match.get("id")
        reply = kb_match["answer"]
        suggestions: List[schemas.ChatbotItemOut] = []

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
        elif tag == "user_is_gay" or qid == 25:
            intent = "user_is_gay"
            suggested_prompts = ["Legal Rights in India (Section 377)", "Safe Spaces & Community Groups", "Tele-MANAS: 14416"]
        elif tag == "user_is_lesbian" or qid == 26:
            intent = "user_is_lesbian"
            suggested_prompts = ["Sappho for Equality & Support", "Legal Protections against Harassment", "Safe Housing"]
        elif tag == "user_is_bisexual" or qid == 27:
            intent = "user_is_bisexual"
            suggested_prompts = ["LGBTQ+ Community Support", "Queer Affirmative Therapists", "Coming Out Advice"]
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
    )

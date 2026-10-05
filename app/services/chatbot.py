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


CHATBOT_SYSTEM_PROMPT = """You are the chatbot for "Beyond Identity", a website that gives verified information and support related to transgender identity and related topics.

MOST IMPORTANT RULE — STOP AFTER EVERY REPLY
- Respond to only the user's current message, in 2-4 short sentences maximum.
- After your reply, STOP completely. Do not add follow-up information, extra tips, or guess what they'll ask next.
- Never send more than one message in a row. Wait for the user to type again before saying anything else.
- Do not repeat or summarize what you already said in earlier messages.

GREETING
- If the user says "hi" / "hello", reply exactly in this style:
  "Hi! I'm Beyond Identity — a website where you get verified, trustworthy information about transgender identity and related topics."
- Then STOP. Do not ask a question yet, do not explain more. Wait for the user's next message.

HANDLING QUESTIONS
- When the user asks for help (e.g. "I need help", "I'm confused", "how do I tell my family"), give a short, warm, practical reply — about 2 to 4 sentences, or at most 2-3 short points.
- Keep it specific to what they asked. Do not give a long lecture.
- End your reply there and wait. Do not keep adding "also you could..." after your own answer.

TONE
- Warm, respectful, non-judgmental. Use the name/pronouns the user gives.
- Simple, plain language — avoid long paragraphs.
- For medical or legal questions, give general guidance only and suggest a qualified doctor or lawyer for anything specific.

SAFETY
- If the user sounds distressed or unsafe, respond gently, encourage them to reach out to someone they trust or a local helpline, then stop and wait — do not lecture.

SCOPE
- Only answer questions about transgender identity, rights, healthcare basics, coming out, family/workplace support, and being an ally.
- For anything else, politely say this chat is focused on transgender-related support.
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

    # 6. Core Transgender Topics (the 5 allowed topics)
    # Topic A: Transgender and gender identity basics & terminology
    basics_keywords = [
        "transgender", "trans", "gender identity", "gender expression", "cisgender",
        "non-binary", "nonbinary", "pronoun", "pronouns", "dysphoria", "gender dysphoria",
        "deadname", "deadnaming", "queer", "intersex", "third gender", "trans person",
        "trans man", "trans woman", "transmasc", "transfem", "ftm", "mtf",
        "what does transgender mean", "what is transgender", "transgender meaning"
    ]
    if _matches_any(["pronoun", "pronouns", "cisgender", "non-binary", "nonbinary", "gender identity", "gender expression", "deadname", "deadnaming", "what is trans", "what does trans"], q):
        return "basics_terminology"

    # Topic B: Rights and laws (for India: Transgender Persons Act 2019, NALSA judgment, ID/certificate process)
    legal_keywords = [
        "rights", "law", "legal", "tg act", "transgender act", "act 2019", "nalsa", "article 14",
        "article 21", "certificate", "id card", "identity card", "district magistrate",
        "dm", "affidavit", "aadhaar", "pan card", "passport", "adopt", "adoption",
        "child", "custody", "marriage", "free legal aid", "15100", "section 12", "section 18",
        "national portal", "dm certificate"
    ]
    if _matches_any(legal_keywords, q):
        return "legal_rights"

    # Topic C: Healthcare and transition information (general info only)
    health_keywords = [
        "hrt", "hormone", "hormones", "therapy", "doctor", "clinic", "surgery", "srs",
        "gender affirmation", "transition", "transitioning", "endocrinologist", "blood test", "blood tests",
        "ayushman", "pmjay", "pm-jay", "estrogen", "testosterone", "blockers"
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
        "scheme", "scholarship", "smile", "pm-daksh", "daksh", "welfare",
        "financial aid", "grant", "stipend", "government benefit", "ration", "pension"
    ]
    if _matches_any(scheme_keywords, q):
        return "scholarship_schemes"

    if _matches_any(basics_keywords, q):
        return "basics_terminology"

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
        basics_keywords + legal_keywords + health_keywords + mental_keywords + ally_keywords + job_keywords + housing_keywords,
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
        try:
            db_query = db_query.filter(models.Listing.category == models.ListingCategory(category_filter))
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

    elif intent == "out_of_scope":
        reply = "This chat is focused on transgender-related support, including identity, rights, healthcare basics, coming out, and family or workplace support."

    else:
        # General / Platform Help
        reply = (
            "Beyond Identity gives verified information on transgender identity, Indian legal rights, healthcare basics, and community support. "
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
    intent = detect_intent(query)

    # 1. Search Live Database Listings if applicable
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

    # Count total verified database records
    total_records = db.query(models.Listing).filter(
        models.Listing.status == models.VerificationStatus.verified
    ).count()

    # 2. Check for User Cases if relevant
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

    # 3. Try Anthropic Claude API if key is present
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)

            claude_messages = []
            for h in (request.history or []):
                role = h.get("role", "user")
                if role in ("user", "assistant") and h.get("content"):
                    claude_messages.append({"role": role, "content": h["content"]})
            claude_messages.append({"role": "user", "content": query})

            database_context = "\n".join(
                [f"- {s.title} ({s.category}, {s.organization_name}, {s.location}, Contact: {s.contact_info})" for s in suggestions]
            )

            system_prompt = (
                f"{CHATBOT_SYSTEM_PROMPT}\n\n"
                "Additional Portal Context:\n"
                "- 24/7 Community Helpline: 868989330\n"
                "- Tele-MANAS Mental Health Helpline: 14416\n"
                "- NALSA Free Legal Aid Helpline: 15100\n"
                "- Emergency Police/Ambulance: 112\n"
                "- National Portal for Transgender Persons: https://transgender.dosje.gov.in\n"
                "- Garima Greh emergency transit shelter homes\n"
                "- Ayushman Bharat TG ₹5 Lakh package\n"
                f"Active Database Verified Listings:\n{database_context}\n"
            )

            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                system=system_prompt,
                messages=claude_messages,
            )
            raw_reply = response.content[0].text if response.content else ""
            _, suggested_prompts = generate_curated_reply(intent, query, suggestions)

            return schemas.ChatbotQueryResponse(
                reply=raw_reply,
                intent=intent,
                suggestions=suggestions,
                user_cases=user_cases,
                suggested_prompts=suggested_prompts,
                total_database_records=total_records,
            )
        except Exception:
            pass

    # 4. Curated Knowledge & Database Engine Fallback
    reply, suggested_prompts = generate_curated_reply(intent, query, suggestions)

    return schemas.ChatbotQueryResponse(
        reply=reply,
        intent=intent,
        suggestions=suggestions,
        user_cases=user_cases,
        suggested_prompts=suggested_prompts,
        total_database_records=total_records,
    )

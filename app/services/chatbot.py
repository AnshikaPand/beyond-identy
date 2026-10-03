"""
AI Chatbot Service for Beyond Identity.
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
    """Strip markdown symbols for smooth audio text-to-speech output."""
    clean = re.sub(r"(\*\*|\*|###|##|#|`|\[|\]|\(.*?\))", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _matches_any(keywords: List[str], text: str) -> bool:
    """Matches any keyword in text using word boundaries where appropriate."""
    for k in keywords:
        pattern = r"\b" + re.escape(k) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def detect_intent(query: str) -> str:
    """Detect the primary conversational intent from the user query."""
    q = query.lower()

    # 1. Emergency / Crisis SOS
    emergency_keywords = [
        "suicide", "kill myself", "harm", "crisis", "sos", "emergency", "danger",
        "attacked", "beaten", "threatened", "police violence", "immediate help",
        "save me", "depressed", "mental breakdown", "helpline", "call helpline"
    ]
    if _matches_any(emergency_keywords, q):
        return "emergency_crisis"

    # 2. Healthcare & HRT
    health_keywords = [
        "hrt", "hormone", "hormones", "therapy", "doctor", "clinic", "surgery", "srs",
        "gender affirmation", "transition", "endocrinologist", "blood test",
        "ayushman", "pmjay", "pm-jay", "mental health", "counseling", "psychiatrist"
    ]
    if _matches_any(health_keywords, q):
        return "healthcare"

    # 3. Employment & Jobs
    job_keywords = [
        "job", "jobs", "employment", "work", "hiring", "vacancy", "career", "salary",
        "interview", "resume", "cv", "retail", "tech", "customer support", "remote"
    ]
    if _matches_any(job_keywords, q):
        return "employment"

    # 4. Housing & Shelters (using word boundaries to prevent 'rent' matching 'parents')
    housing_keywords = [
        "housing", "house", "rent", "room", "flat", "apartment", "landlord",
        "evict", "eviction", "shelter", "garima greh", "pg", "transit shelter",
        "kicked out", "homeless"
    ]
    if _matches_any(housing_keywords, q):
        return "housing"

    # 5. Incident & Discrimination Reporting
    incident_keywords = [
        "report", "incident", "harass", "harassment", "discrimination", "extort",
        "complaint", "file a complaint", "abuse", "fir", "police station", "bribe"
    ]
    if _matches_any(incident_keywords, q):
        return "incident_report"

    # 6. Welfare Schemes & Scholarships
    scheme_keywords = [
        "scheme", "scholarship", "smile", "pm-daksh", "daksh", "welfare",
        "financial aid", "grant", "stipend", "government benefit", "ration", "pension"
    ]
    if _matches_any(scheme_keywords, q):
        return "scholarship_schemes"

    # 7. Legal Rights & Identity Documentation
    legal_keywords = [
        "rights", "law", "legal", "tg act", "transgender act", "nalsa", "article 14",
        "article 21", "certificate", "id card", "identity card", "district magistrate",
        "dm", "affidavit", "aadhaar", "pan card", "passport", "adopt", "adoption",
        "child", "custody", "parents", "parenting", "marriage", "free legal aid", "15100"
    ]
    if _matches_any(legal_keywords, q):
        return "legal_rights"

    # 8. Conversational / Small Talk Intention Check
    # A. "What are you doing" / "What r u doing" / "wyd" (takes priority over plain hi)
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
        r"\bwhat\s+you\s+doing\b",
        r"\bwhat\s+u\s+doing\b",
    ]
    if any(re.search(p, q, re.IGNORECASE) for p in doing_patterns):
        return "chitchat_doing"

    # B. "How are you" / "How r u" / "How's it going"
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

    # C. "Who are you" / "What can you do" / "What is this"
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

    # D. "Thank you" / "Thanks"
    thanks_keywords = [
        "thank you", "thanks", "thank u", "thx", "thank you so much",
        "dhanyawad", "shukriya", "much appreciated"
    ]
    if _matches_any(thanks_keywords, q):
        return "chitchat_thanks"

    # E. Compliments & Positive feedback
    compliment_keywords = [
        "awesome", "great job", "nice work", "you are great", "you're great",
        "love you", "cool", "superb", "brilliant", "amazing", "wonderful", "good bot"
    ]
    if _matches_any(compliment_keywords, q):
        return "chitchat_compliment"

    # F. Farewell / Goodbye
    farewell_keywords = [
        "bye", "goodbye", "see you", "cya", "good night", "take care", "tata"
    ]
    if _matches_any(farewell_keywords, q):
        return "chitchat_farewell"

    # G. Greetings: "hi", "hii", "hello", "hey", "namaste", etc.
    greeting_keywords = [
        "hi", "hii", "hiii", "hello", "helo", "hey", "heyy", "heyyy", "hey there",
        "hola", "namaste", "namaskar", "vanakkam", "pranam", "greetings", "good morning", "good evening", "good afternoon"
    ]
    if _matches_any(greeting_keywords, q):
        return "chitchat_greeting"

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
    """Generates empathetic, authoritative legal & platform guidance grounded in Indian statutes."""
    suggested_prompts: List[str] = []

    if intent == "emergency_crisis":
        suggested_prompts = [
            "Connect me to free legal counsel (NALSA)",
            "Find nearest Garima Greh emergency shelter",
            "How to file a confidential police complaint",
            "Talk to a peer counselor",
        ]
        reply = (
            "### 🚨 Immediate Crisis & Safety Support\n\n"
            "If you are in immediate danger or facing acute emotional distress, please reach out right away. "
            "You are not alone, and help is available 24/7:\n\n"
            "- 📞 **24/7 Community Support Helpline:** [**868989330**](tel:868989330) *(Confidential & trans-affirming)*\n"
            "- 🧠 **National Tele-MANAS Helpline:** [**14416**](tel:14416) *(Toll-free 24x7 mental health triage)*\n"
            "- ⚖️ **NALSA Free Legal Aid Helpline:** [**15100**](tel:15100) *(Free legal defense under Section 12)*\n"
            "- 🚨 **National Emergency Response (Police/Ambulance):** [**112**](tel:112)\n\n"
            "**Your Safety First:**\n"
            "1. If facing immediate physical threat, move to a well-lit public space or contact 112.\n"
            "2. Under **Section 18 of the Transgender Persons Act, 2019**, violence, physical abuse, or extortion "
            "against transgender persons carries imprisonment up to 2 years with non-bailable clauses.\n"
            "3. If you have been evicted or separated from your family, emergency stay is provided at **Garima Greh** transit shelters."
        )

    elif intent == "employment":
        suggested_prompts = [
            "What should a company Equal Opportunity Policy contain?",
            "What if my company fires me for transitioning?",
            "View all verified corporate job openings",
            "Skill training under PM-DAKSH",
        ]
        listings_text = ""
        if suggestions:
            listings_text = "\n\n**Verified Opportunities from our Database:**\n" + "\n".join(
                [f"- **{s.title}** ({s.organization_name}, {s.location}) — Contact: `{s.contact_info}`" for s in suggestions]
            )

        reply = (
            "### 💼 Transgender Inclusive Employment & Workplace Rights\n\n"
            "Under Indian law, discrimination in hiring, promotions, wages, or office amenities based on gender identity is strictly prohibited:\n\n"
            "1. **Sections 9 & 10 of TG Act 2019:** Every establishment (private and public) is mandated to provide equal opportunities and publish an **Equal Opportunity Policy**.\n"
            "2. **Complaints Officer (Section 11):** Every company with 20+ employees must appoint a designated Complaints Officer to resolve discrimination grievances within 15 days.\n"
            "3. **SMILE & PM-DAKSH Skilling:** The Ministry of Social Justice provides free market-oriented skill training with monthly stipends for trans individuals aged 18–45.\n"
            f"{listings_text}\n\n"
            "💡 *Tip: If you faced workplace discrimination, you can lodge an incident report through our portal to receive free NGO advocacy and legal assistance.*"
        )

    elif intent == "housing":
        suggested_prompts = [
            "Can a landlord evict me without notice?",
            "How do I apply for a Garima Greh shelter stay?",
            "Find verified inclusive rental apartments",
            "Housing rights under Section 12",
        ]
        shelters_text = ""
        if suggestions:
            shelters_text = "\n\n**Verified Housing & Transit Shelters from our Database:**\n" + "\n".join(
                [f"- **{s.title}** ({s.organization_name}, {s.location}) — `{s.contact_info}`" for s in suggestions]
            )

        reply = (
            "### 🏠 Safe Housing & Landlord Non-Discrimination Protections\n\n"
            "Your right to shelter and safe residence is guaranteed under Indian constitutional jurisprudence and statutory mandates:\n\n"
            "1. **Section 12 of the Transgender Persons Act, 2019:** Explicitly protects the right to residence. No family or landlord can arbitrarily separate or evict a transgender individual.\n"
            "2. **Arbitrary Eviction is Illegal:** A landlord cannot terminate a tenancy or demand sudden eviction based on gender identity or gender expression.\n"
            "3. **Garima Greh Shelter Homes:** The Central Government runs Garima Greh transit homes across 15+ Indian states providing safe shelter, meals, medical care, and skill training for up to 1 year.\n"
            f"{shelters_text}\n\n"
            "📞 Need emergency transit housing? Call our community helpline at [**868989330**](tel:868989330) or approach NALSA at 15100."
        )

    elif intent == "healthcare":
        suggested_prompts = [
            "What blood tests are needed before starting HRT?",
            "How does Ayushman Bharat ₹5 Lakh TG package work?",
            "Find queer-affirmative endocrinologists",
            "Free mental health tele-consultation (14416)",
        ]
        clinics_text = ""
        if suggestions:
            clinics_text = "\n\n**Verified Affirmative Healthcare Providers in our Database:**\n" + "\n".join(
                [f"- **{s.title}** ({s.organization_name}, {s.location}) — `{s.contact_info}`" for s in suggestions]
            )

        reply = (
            "### 🩺 Safe Gender-Affirming Healthcare & Clinical Navigation\n\n"
            "Accessing healthcare should be affirmative, safe, and clinically guided:\n\n"
            "1. **Ayushman Bharat TG Package (AB-PMJAY):** Provides up to **₹5,00,000/year** health insurance coverage specifically for transgender persons. It covers gender-affirming surgeries, hormone therapy, and hospitalization across empanelled hospitals.\n"
            "2. **Safe HRT Roadmap (WPATH SOC v8):** Self-medicating hormones poses high thromboembolic and hepatic risks. Always consult a qualified endocrinologist. Baseline tests include CBC, Lipid Profile, Liver & Kidney Function (LFT/KFT), and baseline hormone levels (Total Testosterone & Estradiol).\n"
            "3. **Mental Health Triage:** If experiencing dysphoria or emotional distress, call **Tele-MANAS** toll-free at [**14416**](tel:14416) for 24/7 psychologist consultation.\n"
            f"{clinics_text}\n\n"
            "✨ *Explore our interactive 'AI Health Assistant' tab for a step-by-step clinical decision tree!*"
        )

    elif intent == "scholarship_schemes":
        suggested_prompts = [
            "How to apply for SMILE scheme?",
            "National Portal Transgender scholarship",
            "PM-DAKSH vocational training eligibility",
            "Chandigarh education fee-waiver scheme",
        ]
        schemes_text = ""
        if suggestions:
            schemes_text = "\n\n**Verified Government Schemes & Grants:**\n" + "\n".join(
                [f"- **{s.title}** ({s.organization_name}) — Details: `{s.contact_info}`" for s in suggestions]
            )

        reply = (
            "### 🎓 Government Schemes, Scholarships & Economic Empowerment\n\n"
            "Multiple welfare schemes are actively operational under the Ministry of Social Justice and Empowerment (MoSJE):\n\n"
            "1. **SMILE (Support for Marginalized Individuals for Livelihood and Enterprise):** Central umbrella scheme providing medical care, skill development, and financial assistance.\n"
            "2. **National Post-Matric Scholarships:** Financial assistance covering full tuition and ₹2,000/month maintenance allowance for degree, diploma, and higher education courses.\n"
            "3. **PM-DAKSH Yojana:** Skill training across IT, hospitality, handicrafts, and entrepreneurship with toolkits and stipend.\n"
            f"{schemes_text}\n\n"
            "Apply online through the **National Portal for Transgender Persons** ([transgender.dosje.gov.in](https://transgender.dosje.gov.in)) or call helpline **14566**."
        )

    elif intent == "incident_report":
        suggested_prompts = [
            "How do I file an anonymous discrimination report?",
            "What happens after I report an incident?",
            "Section 18 penalties against harassment",
            "Call 24/7 Community Helpline (868989330)",
        ]
        reply = (
            "### 🛡️ Incident Redressal & Legal Protection\n\n"
            "If you or someone in your community has faced discrimination, harassment, or unlawful eviction, Beyond Identity can help you seek redress:\n\n"
            "1. **Confidential & Anonymous Filing:** You can report an incident via our **Report Discrimination** tab. You may choose to stay completely anonymous.\n"
            "2. **Automated Matching:** Our system immediately matches your case to relevant **Indian Government Welfare Schemes** and verified **Local NGO Response Cells**.\n"
            "3. **Statutory Penalties (Section 18):** Under Central Act No. 40 of 2019, physical, verbal, emotional, or sexual abuse of a transgender person is punishable by up to 2 years imprisonment plus fines.\n"
            "4. **Emergency Escalation:** For urgent legal intervention, contact the **NALSA Free Legal Aid Helpline at 15100** or call our 24/7 community helpline at [**868989330**](tel:868989330)."
        )

    elif intent == "legal_rights":
        qa_matches = search_qa(query, limit=2)
        qa_text = ""
        if qa_matches:
            qa_text = "\n\n**Relevant Legal Knowledge:**\n" + "\n".join(
                [f"**Q: {q_item['question']}**\n- {q_item['answer']}\n*(Law: {q_item['applicable_law']})*" for q_item in qa_matches]
            )

        suggested_prompts = [
            "Can trans parents legally adopt in India under CARA?",
            "What is the 30-day DM certificate timeline?",
            "How to change gender marker to Male/Female on Aadhaar?",
            "Free Legal Aid under NALSA Section 12",
        ]
        reply = (
            "### ⚖️ Know Your Rights Under Indian Law\n\n"
            "Your identity and dignity are constitutionally and statutorily protected in India:\n\n"
            "- **NALSA vs. Union of India (2014):** Supreme Court declared the right to self-perceived gender identity as fundamental under Articles 14, 15, 19(1)(a), and 21. Medical or surgical interventions are **NOT** required for legal identity recognition.\n"
            "- **Transgender Persons Act, 2019 & Rules 2020:** The District Magistrate must issue a Certificate of Identity within **30 days** of an online application at `transgender.dosje.gov.in`.\n"
            "- **Free Legal Aid:** Under Section 12 of the Legal Services Authorities Act, all transgender citizens are entitled to **100% free legal representation** via the High Court / District Legal Services Authority.\n"
            f"{qa_text}\n\n"
            "📞 For free legal counsel, dial NALSA helpline [**15100**](tel:15100) or National TG Helpline [**14566**](tel:14566)."
        )

    elif intent == "chitchat_doing":
        suggested_prompts = [
            "💼 Show me verified inclusive jobs",
            "🏠 Find safe housing & Garima Greh shelters",
            "What are my rights against landlord eviction?",
            "How to get free legal aid under NALSA?",
            "Safe HRT & gender-affirming healthcare",
        ]
        reply = (
            "### 👋 Hey there! I'm doing great, thank you for asking! 😊\n\n"
            "Right now, I am right here on **Beyond Identity** assisting community members across India:\n\n"
            "- 💼 **Searching live verified jobs & internships** with transgender-affirmative employers\n"
            "- 🏠 **Finding safe housing** & Garima Greh emergency transit shelter beds\n"
            "- 🩺 **Guiding on safe HRT protocols** and Ayushman Bharat ₹5 Lakh medical coverage\n"
            "- ⚖️ **Explaining statutory legal rights** under the Transgender Persons Act 2019 & NALSA ruling\n"
            "- 🚨 **Connecting to 24/7 crisis helplines** whenever someone is in distress\n\n"
            "How are you doing today? What's on your mind? Feel free to ask me anything or click one of the suggestions below!"
        )

    elif intent == "chitchat_howareyou":
        suggested_prompts = [
            "Find verified trans-inclusive jobs",
            "Safe housing & transit shelters",
            "Gender-affirming healthcare guidance",
            "Know my legal rights under TG Act 2019",
        ]
        reply = (
            "### 😊 I'm doing wonderful, thank you for checking in!\n\n"
            "I am fully operational and ready to assist you today. Whether you're exploring verified inclusive jobs, "
            "looking for safe housing, checking your legal rights under Indian law, or just exploring the platform, "
            "I'm right here with you.\n\n"
            "How are you feeling today? How can I help you out?"
        )

    elif intent == "chitchat_greeting":
        suggested_prompts = [
            "💼 Find verified jobs in Mumbai or Remote",
            "🏠 Safe housing & Garima Greh shelters",
            "🩺 Safe HRT roadmap & clinical tests",
            "⚖️ What are my rights against workplace harassment?",
            "🚨 24/7 Community Crisis Helpline (868989330)",
        ]
        reply = (
            "### 👋 Hello & Namaste! Wonderful to connect with you! 😊\n\n"
            "Welcome to **Beyond Identity**. I am your dedicated 24/7 AI companion, here to help you navigate:\n\n"
            "- 💼 **Verified Inclusive Opportunities:** Jobs, scholarships, and skill programs\n"
            "- 🏠 **Safe Housing:** Verified rental apartments and Garima Greh emergency transit shelters\n"
            "- 🩺 **Healthcare Triage:** Safe HRT guidance, endocrinologists, and Ayushman Bharat ₹5L cover\n"
            "- ⚖️ **Legal Protections:** TG Act 2019, NALSA 2014, Section 12 Free Legal Aid (15100)\n"
            "- 🚨 **Crisis Support:** 24/7 Helpline at [**868989330**](tel:868989330)\n\n"
            "How can I assist you today? Feel free to ask any question!"
        )

    elif intent == "chitchat_identity":
        suggested_prompts = [
            "How does Beyond Identity verify employers?",
            "Tell me about the Transgender Persons Act 2019",
            "Find verified inclusive jobs",
            "Emergency crisis contacts",
        ]
        reply = (
            "### 🤖 About Me: Beyond Identity AI Assistant\n\n"
            "I am the official 24/7 AI guide for the **Beyond Identity** portal, designed specifically to champion the rights, "
            "dignity, and welfare of transgender and gender-diverse individuals across India. Aligning with UN SDGs 3, 10, and 16.\n\n"
            "**What I can do for you:**\n"
            "1. 💼 **Live Database Search:** Instantly look up vetted inclusive employers, shelters, clinics, and government grants.\n"
            "2. ⚖️ **Indian Statutory Legal Rights:** Break down legal rights under the Transgender Persons Act 2019, Supreme Court NALSA judgment, and 30-day DM certificate process.\n"
            "3. 🩺 **Clinical Health Guidance:** Provide evidence-based clinical roadmaps aligned with WPATH SOC v8 and Ayushman Bharat ₹5 Lakh packages.\n"
            "4. 🛡️ **Incident Redressal:** Guide you through filing confidential discrimination reports matched to local NGOs.\n"
            "5. 🚨 **Emergency Crisis SOS:** Direct, immediate connection to verified helplines (868989330, 14416, 15100, 112).\n\n"
            "Feel free to ask me anything in simple, natural English, Hindi, or Tamil!"
        )

    elif intent == "chitchat_thanks":
        suggested_prompts = [
            "Explore verified jobs",
            "Know my legal rights",
            "Safe housing options",
        ]
        reply = (
            "### 💖 You're most welcome! 😊\n\n"
            "I'm always here to support you. Never hesitate to reach out whenever you need legal advice, safe housing, "
            "healthcare guidance, or crisis assistance.\n\n"
            "Stay safe, proud, and empowered! ✨ Let me know if you need anything else."
        )

    elif intent == "chitchat_compliment":
        suggested_prompts = [
            "Find verified jobs",
            "Safe housing & shelters",
            "Legal rights Q&A",
        ]
        reply = (
            "### ✨ Thank you so much! That really means a lot! 😊\n\n"
            "Our team at Beyond Identity works hard to ensure every individual has access to safe opportunities and legal protection. "
            "Let me know if there's anything else I can assist you with today!"
        )

    elif intent == "chitchat_farewell":
        suggested_prompts = [
            "24/7 Helpline: 868989330",
            "Explore verified opportunities",
        ]
        reply = (
            "### 👋 Goodbye & Take Care! 🌈\n\n"
            "It was a pleasure assisting you today. Remember that Beyond Identity and our 24/7 community helpline "
            "([**868989330**](tel:868989330)) are always here for you whenever you need us.\n\n"
            "Have a wonderful day ahead! ✨"
        )

    else:
        # General / Platform Help
        suggested_prompts = [
            "Find verified trans-inclusive jobs",
            "Safe housing & transit shelters",
            "Gender affirming healthcare & HRT guide",
            "Know my legal rights under TG Act 2019",
            "24/7 Community Crisis Helplines",
        ]
        reply = (
            "### 🏳️‍⚧️ Welcome to the Beyond Identity AI Assistant!\n\n"
            "I am your 24/7 companion for navigating transgender rights, inclusive opportunities, and healthcare across India. "
            "Here is how I can assist you today:\n\n"
            "- 💼 **Verified Opportunities:** Browse inclusive employment, scholarships, and skill programs.\n"
            "- 🏠 **Safe Housing:** Discover verified rental listings and Garima Greh transit shelters.\n"
            "- 🩺 **Health Navigation:** Guidance on safe HRT protocols, endocrinologists, and PM-JAY ₹5L coverage.\n"
            "- ⚖️ **Legal Awareness:** Get clear answers on the TG Act 2019, NALSA judgment, ID cards, and free legal aid.\n"
            "- 🚨 **24/7 Crisis Support:** Quick access to verified helplines ([868989330](tel:868989330), Tele-MANAS 14416, NALSA 15100).\n\n"
            "How can I help you right now? Feel free to ask any question or click a suggestion below!"
        )

    return reply, suggested_prompts


def answer_chatbot_query(
    db: Session,
    request: schemas.ChatbotQueryRequest,
    current_user: Optional[models.User] = None,
) -> schemas.ChatbotQueryResponse:
    """
    Main AI Chatbot processing logic.
    Analyzes intent, searches live database listings, consults legal repository or Claude,
    and returns a structured response.
    """
    query = request.query.strip()
    intent = detect_intent(query)

    # 1. Search Live Database Listings
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
                "You are the Beyond Identity AI Assistant — an empathetic, authoritative, and supportive guide for "
                "transgender, intersex, and gender-diverse individuals across India. Aligning with UN SDGs 3, 10, and 16.\n\n"
                "Ground all legal answers in Indian law:\n"
                "- Transgender Persons (Protection of Rights) Act 2019 (Sections 3, 4, 9, 10, 11, 12, 18)\n"
                "- NALSA vs Union of India (2014) Supreme Court verdict\n"
                "- Free legal aid under Section 12 of Legal Services Authorities Act (NALSA Helpline: 15100)\n"
                "- National Transgender Helpline: 14566 | Tele-MANAS: 14416 | 24/7 Helpline: 868989330 | Emergency: 112\n"
                "- Ayushman Bharat TG ₹5 Lakh package for gender-affirming care\n"
                "- Garima Greh shelter homes for trans transit stay\n"
                "- Conversational Small Talk: If the user greets you or asks casual questions like 'hii', 'what are you doing', 'how are you', or 'who are you', reply in a warm, conversational, friendly English tone. Explain what you are doing (assisting community members with verified jobs, safe shelters, healthcare triage, and legal rights on Beyond Identity), ask how their day is going, and invite them to ask questions or explore resources.\n\n"
                f"Active Database Verified Listings available in portal:\n{database_context}\n\n"
                "Provide an empathetic, structured answer using clean markdown headers, bullet points, and direct helpline numbers."
            )

            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=900,
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
            # Fallback to curated knowledge base on any API exception
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

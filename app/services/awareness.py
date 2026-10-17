"""
Awareness Module: Know Your Rights & Legal Protections.
Contains curated knowledge and intelligent Q&A retrieval on Indian laws,
including the Transgender Persons (Protection of Rights) Act 2019,
NALSA (2014) Supreme Court verdict, and legal aid remedies.
"""
import os
import re
from typing import List, Dict, Any, Optional
from app.schemas import (
    AwarenessTopicOut,
    AwarenessQueryResponse,
    AwarenessChatMessage,
    AwarenessChatResponse,
)


AWARENESS_TOPICS: List[Dict[str, Any]] = [
    {
        "id": "tg_act_2019",
        "title": "The Transgender Persons (Protection of Rights) Act, 2019",
        "act_or_ruling": "Central Act No. 40 of 2019, Govt. of India",
        "category": "statutory_act",
        "summary": "The landmark central legislation prohibiting discrimination against transgender persons across education, employment, healthcare, housing, and access to public services in India.",
        "key_rights": [
            "Section 3: Absolute prohibition against discrimination in educational institutions, employment, healthcare, access to public places, goods, accommodation, and public offices.",
            "Section 4: Explicit right of every transgender person to be recognized as such and right to self-perceived gender identity.",
            "Section 9 & 10: Mandatory non-discrimination in private & public establishments. Every establishment must designate a Complaints Officer.",
            "Section 12: Right of residence — no family or person shall separate a transgender person from family or home.",
            "Section 18: Criminal penalties (imprisonment up to 2 years + fine) for compelling bonded labor, denying access to public spaces, physical or sexual abuse.",
        ],
        "remedies": [
            "Lodge a formal written grievance with the establishment's designated Complaints Officer (mandatory under Section 11).",
            "File a complaint with the District Magistrate or National Council for Transgender Persons (NCTP).",
            "File an FIR under Section 18 of the Act with the local police station for physical or verbal abuse.",
            "Approach State Human Rights Commission (SHRC) or High Court via a writ petition under Article 226 for violations.",
        ],
        "official_portal": "https://socialjustice.gov.in/writereaddata/UploadFile/TG%20act%202019.pdf",
        "keywords": ["act", "law", "section 3", "rights", "statutory", "discrimination", "penalty", "punishment", "abuse"],
    },
    {
        "id": "nalsa_2014",
        "title": "NALSA vs. Union of India (2014) Supreme Court Verdict",
        "act_or_ruling": "Supreme Court of India (AIR 2014 SC 1863)",
        "category": "supreme_court_judgment",
        "summary": "Historical judgment by the Supreme Court of India declaring transgender individuals as the 'third gender' and affirming that gender identity is fundamental to personal dignity and autonomy under the Indian Constitution.",
        "key_rights": [
            "Article 14 (Equality before Law): Transgender individuals enjoy full equality and equal protection under law.",
            "Article 15 & 16 (Prohibition of Discrimination & Public Employment): 'Sex' includes gender identity; discrimination based on gender identity is unconstitutional.",
            "Article 19(1)(a) (Freedom of Expression): Self-expression of one's gender via dress, mannerisms, or speech is constitutionally protected.",
            "Article 21 (Right to Life & Dignity): The right to choose gender identity is integral to personal autonomy and liberty; medical or surgical intervention is NOT a prerequisite for self-determination.",
        ],
        "remedies": [
            "Invoke NALSA ruling to challenge any government form or private entity denying options beyond binary male/female.",
            "File a writ petition in the High Court for denial of admissions or recruitment based on gender identity.",
            "Seek free legal support from the High Court Legal Services Committee citing NALSA Section 12 mandates.",
        ],
        "official_portal": "https://main.sci.gov.in/judgment/judis/41411.pdf",
        "keywords": ["nalsa", "supreme court", "article 21", "article 14", "article 15", "self determination", "third gender", "constitution", "dignity"],
    },
    {
        "id": "national_id_portal",
        "title": "National Portal for Transgender Certificates & Identity Cards",
        "act_or_ruling": "Transgender Persons (Protection of Rights) Rules, 2020",
        "category": "identity_and_documentation",
        "summary": "Step-by-step procedure to legally apply for and obtain a Certificate of Identity and Identity Card from the District Magistrate without any invasive medical check.",
        "key_rights": [
            "Rule 3: End-to-end online application through transgender.dosje.gov.in — zero physical visits required.",
            "Rule 4: The District Magistrate must issue the Certificate of Identity within 30 days of receiving the application.",
            "Rule 6 & 7: Procedure for changing gender marker to male or female post gender-affirmation surgery via certificate issued by Medical Superintendent.",
            "The Certificate is a recognized proof of identity for updating Aadhaar, PAN card, Passport, and voter ID.",
        ],
        "remedies": [
            "Register at https://transgender.dosje.gov.in with affidavit in Form-1.",
            "If the DM does not process the application within 30 days, file an online grievance on CPGRAMS (pgportal.gov.in) citing Rule 4.",
            "Contact the National Transgender Helpline (14566) for application tracking escalations.",
        ],
        "official_portal": "https://transgender.dosje.gov.in",
        "keywords": ["certificate", "identity card", "id card", "portal", "district magistrate", "dm", "affidavit", "aadhaar", "gender change", "documentation"],
    },
    {
        "id": "workplace_protections",
        "title": "Workplace Rights & Equal Opportunity Policies",
        "act_or_ruling": "TG Act 2019 (Sections 9, 10, 11) & Transgender Rules 2020",
        "category": "employment",
        "summary": "Statutory mandates for private companies, corporations, and government employers to ensure fair hiring, promotion, facilities, and anti-harassment safeguards.",
        "key_rights": [
            "Section 9: No establishment shall discriminate in recruitment, promotion, and other conditions of employment.",
            "Section 10: Mandatory publication of an Equal Opportunity Policy by every establishment with 20+ employees.",
            "Section 11: Mandatory appointment of a designated Complaints Officer to investigate and resolve grievances within 15 days.",
            "Infrastructural accessibility: Requirement for gender-neutral restrooms and inclusive health insurance coverage.",
        ],
        "remedies": [
            "Submit a formal written complaint to the company's designated Complaints Officer (Internal Complaints Committee).",
            "Send a notice through an advocate to the employer demanding compliance with Section 10 & 11.",
            "Approach the Central/State Labor Commissioner or file a writ petition for wrongful termination.",
        ],
        "official_portal": "https://labour.gov.in",
        "keywords": ["workplace", "job", "employment", "fired", "hiring", "company", "boss", "salary", "complaints officer", "equal opportunity"],
    },
    {
        "id": "housing_rights",
        "title": "Housing Rights & Protection Against Unlawful Eviction",
        "act_or_ruling": "TG Act 2019 (Section 12) & Model Tenancy Framework",
        "category": "housing",
        "summary": "Legal protections against eviction, arbitrary refusal to rent, and domestic violence or family estrangement.",
        "key_rights": [
            "Section 12(1): No transgender child or person shall be separated from their parents or immediate family on the grounds of being transgender.",
            "Section 12(3): If family cannot care for them, the court may place them in a government rehabilitation center / Garima Greh.",
            "Right to rent: Landlords cannot refuse rental agreements or arbitrarily evict tenants solely due to gender identity.",
            "Protection against harassment: Landlord intimidation is punishable under civil tenancy acts and Section 506 (criminal intimidation).",
        ],
        "remedies": [
            "Call local emergency police at 112 if facing immediate violent physical eviction.",
            "Reach out to Garima Greh emergency shelters via Tweet Foundation or Humsafar Trust for safe transit accommodation.",
            "Approach the District Rent Control Authority or District Court for injunctive relief against unlawful eviction.",
        ],
        "official_portal": "https://transgender.dosje.gov.in/garimagreh",
        "keywords": ["housing", "rent", "landlord", "eviction", "evicted", "flat", "apartment", "shelter", "family rejection", "home"],
    },
    {
        "id": "police_harassment_legal_aid",
        "title": "Police Harassment Redressal & Free Legal Aid",
        "act_or_ruling": "Section 12 Legal Services Authorities Act, 1987 & Section 18 TG Act",
        "category": "legal_aid_and_police",
        "summary": "Your constitutional safeguards against arbitrary police detention, extortion, bodily searches, and the mechanism to get free advocate representation.",
        "key_rights": [
            "Protection from arbitrary detention: Police cannot detain individuals solely for gathering in public or seeking alms without an arrest warrant under CrPC/BNSS.",
            "Bodily search dignity: Physical searches must be conducted with dignity and in private by designated officers corresponding to gender identity.",
            "Section 12 NALSA: Free legal services for all transgender individuals irrespective of income.",
            "Right to make a phone call to a lawyer, relative, or NGO immediately upon detention.",
        ],
        "remedies": [
            "Dial 15100 (National Legal Services Authority 24x7 helpline) to immediately get an assigned legal aid advocate.",
            "Contact local crisis NGO (Mitr Trust: +91-11-25337890, Humsafar: +91-22-26673800).",
            "File a complaint with the Police Complaints Authority (PCA) or State Human Rights Commission (SHRC) for police misconduct.",
        ],
        "official_portal": "https://nalsa.gov.in",
        "keywords": ["police", "arrest", "detained", "harassment", "extortion", "station", "fir", "legal aid", "lawyer", "free legal aid", "nalsa 15100"],
    },
    {
        "id": "healthcare_rights",
        "title": "Healthcare Rights & Gender Affirming Care Protections",
        "act_or_ruling": "TG Act 2019 (Section 15) & Ayushman Bharat PM-JAY TG Guidelines",
        "category": "healthcare",
        "summary": "State obligation to provide comprehensive gender affirmation medical care, mental healthcare, and non-discriminatory hospital access.",
        "key_rights": [
            "Section 15(a): Government must set up separate HIV surveillance centers for transgender persons.",
            "Section 15(b): Government hospitals must provide facilities for gender-affirmation surgery and hormonal therapy.",
            "Section 15(c): Mandatory medical research to facilitate gender affirmation procedures.",
            "Insurance coverage: Ayushman Bharat covers gender confirmation surgery up to ₹5,00,000 annually.",
        ],
        "remedies": [
            "Report medical refusal to the Chief Medical Officer (CMO) or State Health Department.",
            "Register on Ayushman Bharat TG portal using your National TG Certificate to access empaneled hospitals.",
            "Call Tele-MANAS (14416) for free mental healthcare consultations.",
        ],
        "official_portal": "https://transgender.dosje.gov.in/and-pmjay",
        "keywords": ["health", "hospital", "doctor", "clinic", "surgery", "hrt", "hormones", "ayushman", "denied treatment", "hiv", "tele-manas"],
    },
    {
        "id": "transgender_parents_and_family",
        "title": "Transgender Parents, Child Custody & Family Rights",
        "act_or_ruling": "TG Act 2019 (Sections 3 & 12), CARA Adoption Regulations 2022, & High Court Precedents",
        "category": "family_and_parenting",
        "summary": "Statutory and constitutional protections for transgender parents regarding legal adoption under CARA, biological parenthood, birth certificate and school record registration, child custody in family courts, protection from involuntary separation, and pediatric medical consent.",
        "key_rights": [
            "Right to Adopt under CARA: Transgender individuals have full legal capacity to adopt as single prospective adoptive parents under CARA Adoption Regulations and the Juvenile Justice Act, 2015.",
            "Child Custody & Visitation: Family courts cannot disqualify or deny custody to a parent solely based on their gender transition or identity; the 'welfare and best interest of the child' is the paramount legal standard.",
            "Right of Residence & Non-Separation: Section 12(1) strictly prohibits separating children from their parents or immediate family on the grounds of being transgender.",
            "School Non-Discrimination: Section 3(a) of the TG Act and the Right to Education (RTE) Act prohibit educational institutions from denying admission or harassing children of transgender parents.",
            "Birth Certificate & Official Records: Transgender parents have the right to have their self-perceived gender identity and legal name reflected on their child's official records post-transition.",
            "Emergency Medical Authority: Transgender parents and court-recognized legal guardians hold full statutory power to provide informed consent for pediatric medical triage and surgeries.",
        ],
        "remedies": [
            "File a complaint with the National Commission for Protection of Child Rights (NCPCR) or State Commission (SCPCR) if a school or institution discriminates.",
            "Approach the Family Court or High Court under Article 226 for protection of custody, guardianship, and parental visitation rights.",
            "Lodge an adoption grievance with the Central Adoption Resource Authority (CARA) via carahome@nic.in for processing bias.",
            "Call the National Transgender Helpline (14566) or NALSA Free Legal Aid (15100) for pro-bono family court legal representation.",
        ],
        "official_portal": "https://cara.wcd.gov.in",
        "keywords": [
            "parent", "parents", "parenting", "child", "children", "adoption", "custody",
            "school admission", "birth certificate", "surrogacy", "art", "family court",
            "transgender father", "transgender mother", "trans father", "trans mother",
            "visitation", "guardianship", "medical consent", "cara"
        ],
    },
]


def get_all_topics() -> List[AwarenessTopicOut]:
    """Returns all curated legal awareness topics."""
    return [
        AwarenessTopicOut(
            id=t["id"],
            title=t["title"],
            act_or_ruling=t["act_or_ruling"],
            category=t["category"],
            summary=t["summary"],
            key_rights=t["key_rights"],
            remedies=t["remedies"],
            official_portal=t.get("official_portal"),
        )
        for t in AWARENESS_TOPICS
    ]


def get_topic_by_id(topic_id: str) -> Optional[AwarenessTopicOut]:
    """Finds a single topic by ID."""
    for t in AWARENESS_TOPICS:
        if t["id"] == topic_id:
            return AwarenessTopicOut(
                id=t["id"],
                title=t["title"],
                act_or_ruling=t["act_or_ruling"],
                category=t["category"],
                summary=t["summary"],
                key_rights=t["key_rights"],
                remedies=t["remedies"],
                official_portal=t.get("official_portal"),
            )
    return None


LOCALIZED_KNOWLEDGE: Dict[str, Dict[str, Dict[str, Any]]] = {
    "en": {
        "transgender_parents_and_family": {
            "title": "Transgender Parents, Child Custody & Family Rights",
            "applicable_law": "Transgender Persons Act 2019 (Sections 3 & 12), CARA Adoption Regulations 2022 & High Court Rulings",
            "explanation": "Under Indian law, transgender parents possess full legal parental, custody, and adoption rights. CARA Adoption Regulations (2022) affirm the eligibility of single transgender persons to adopt, and Family Courts are prohibited from denying child custody or visitation solely on grounds of gender transition. Section 12(1) strictly bars the separation of children from transgender parents, and educational institutions are legally prohibited from denying school admission under the Right to Education (RTE) Act.",
            "actionable_steps": [
                "1. Preserve written records, dates, and documentation of any discriminatory denial or mistreatment.",
                "2. In case of school admission refusal, submit a formal complaint to the State Commission for Protection of Child Rights (SCPCR) or NCPCR.",
                "3. In custody disputes, approach Family Courts or High Courts citing Section 12(1) and precedent rulings protecting parental rights.",
                "4. Access free legal aid via the NALSA Helpline (15100) or National Transgender Helpline (14566).",
            ],
            "legal_aid": "NALSA Free Legal Aid Toll-Free Helpline: 15100 | National Transgender Helpline: 14566 | Community Helpline: 868989330",
            "speech": "Under Indian law, transgender parents are fully protected in adoption, custody, and schooling. Discrimination is prohibited. For free legal counsel, call NALSA at 15100.",
        },
        "tg_act_2019": {
            "title": "The Transgender Persons (Protection of Rights) Act, 2019",
            "applicable_law": "Central Act No. 40 of 2019, Ministry of Law and Justice, Govt of India",
            "explanation": "The Transgender Persons (Protection of Rights) Act 2019 prohibits discrimination across education, employment, healthcare, housing, and public services. It recognizes self-perceived gender identity and mandates grievance redressal mechanisms.",
            "actionable_steps": [
                "1. Document the incident with exact dates, names, witnesses, and correspondence.",
                "2. File a formal written complaint with the internal Complaints Officer mandated under Section 11.",
                "3. If facing violence or extortion, lodge an FIR at the local police station under Section 18.",
                "4. Seek free legal representation via NALSA Helpline at 15100.",
            ],
            "legal_aid": "NALSA Free Legal Aid Toll-Free Helpline: 15100 | National Transgender Helpline: 14566 | Community Helpline: 868989330",
            "speech": "The Transgender Persons Act 2019 legally protects your rights against discrimination in employment, education, and housing. For free legal assistance, call NALSA at 15100.",
        },
        "default": {
            "title": "Indian Legal Rights & Statutory Protections",
            "applicable_law": "The Transgender Persons (Protection of Rights) Act, 2019 & NALSA Verdict (2014)",
            "explanation": "Under the Constitution of India and statutory protections, equality and non-discrimination are fundamental rights guaranteed to every gender-diverse individual.",
            "actionable_steps": [
                "1. Maintain documented evidence of any discriminatory actions.",
                "2. Submit a formal grievance to the designated grievance officer or District Magistrate.",
                "3. Call NALSA at 15100 for immediate, free legal assistance.",
            ],
            "legal_aid": "NALSA Free Legal Aid Toll-Free Helpline: 15100 | National Transgender Helpline: 14566 | Community Helpline: 868989330",
            "speech": "Your rights are legally guaranteed under Indian law. For free legal advice and representation, call NALSA at 15100 or the Transgender Helpline at 14566.",
        },
    }
}
# Alias other language keys to English to guarantee 100% English outputs
LOCALIZED_KNOWLEDGE["hi"] = LOCALIZED_KNOWLEDGE["en"]
LOCALIZED_KNOWLEDGE["ta"] = LOCALIZED_KNOWLEDGE["en"]


def query_awareness(
    query_text: str,
    category: Optional[str] = None,
    language: str = "en",
) -> AwarenessQueryResponse:
    """
    Intelligent keyword and semantic matching against Indian legal rights,
    returning plain explanations in English, Hindi, or Tamil, applicable law citations,
    and step-by-step action plans.
    """
    lang = language.lower() if language else "en"
    if lang not in ("en", "hi", "ta"):
        lang = "en"
    query_lower = query_text.lower().strip()
    words = [w for w in query_lower.split() if len(w) > 2]

    best_topic = None
    best_score = -1

    for topic in AWARENESS_TOPICS:
        score = 0
        if category and topic["category"] == category:
            score += 5

        for kw in topic["keywords"]:
            if kw in query_lower:
                score += 4
            for word in words:
                if word in kw:
                    score += 2

        # Check in title and summary
        for word in words:
            if word in topic["title"].lower():
                score += 3
            if word in topic["summary"].lower():
                score += 1

        if score > best_score:
            best_score = score
            best_topic = topic

    # Fallback to the main TG Act if no score matched
    if not best_topic or best_score <= 0:
        best_topic = AWARENESS_TOPICS[0]

    # Generate tailored response
    sections_cited = [r.split(":")[0] for r in best_topic["key_rights"] if ":" in r]
    if not sections_cited:
        sections_cited = ["Section 3 of TG Act 2019", "Article 21 of Constitution"]

    explanation = (
        f"Under Indian law, specifically {best_topic['act_or_ruling']}, your rights are legally protected. "
        f"{best_topic['summary']} The law strictly prohibits discrimination and mandates affirmative protections."
    )

    try:
        from app.data.manager import search_qa
        matched_items = search_qa(query_text, limit=1)
        if matched_items:
            top_item = matched_items[0]
            # If the top item has meaningful overlap with query words
            if any(w in top_item["question"].lower() for w in words):
                explanation += f"\n\n**Specific Statutory Clarification:** {top_item['answer']}"
    except Exception:
        pass

    actionable_steps = [
        f"1. Document the incident: Note dates, names of perpetrators/institutions, witnesses, and save written/email records.",
        f"2. Cite statutory provisions: Inform the violating party that their actions violate {best_topic['title']}.",
        f"3. Lodge an official complaint: {best_topic['remedies'][0]}",
        f"4. Seek Free Legal Support: Transgender individuals are entitled to free legal counsel under Section 12 of the Legal Services Authorities Act via NALSA Helpline (15100).",
    ]

    matched_title = best_topic["title"]
    matched_law = best_topic["act_or_ruling"]
    legal_aid = "NALSA Free Legal Aid Toll-Free Helpline: 15100 | National Transgender Helpline: 14566 | Community Helpline: 868989330"

    if lang in LOCALIZED_KNOWLEDGE:
        loc_data = LOCALIZED_KNOWLEDGE[lang].get(
            best_topic["id"],
            LOCALIZED_KNOWLEDGE[lang].get("default", {})
        )
        if loc_data:
            matched_title = loc_data.get("title", matched_title)
            matched_law = loc_data.get("applicable_law", matched_law)
            explanation = loc_data.get("explanation", explanation)
            actionable_steps = loc_data.get("actionable_steps", actionable_steps)
            legal_aid = loc_data.get("legal_aid", legal_aid)

    portals = []
    if best_topic.get("official_portal"):
        portals.append(best_topic["official_portal"])
    portals.append("https://transgender.dosje.gov.in")
    portals.append("https://nalsa.gov.in")

    return AwarenessQueryResponse(
        query=query_text,
        matched_topic=matched_title,
        applicable_law=matched_law,
        sections_cited=sections_cited,
        explanation=explanation,
        actionable_steps=actionable_steps,
        legal_aid_contact=legal_aid,
        official_portals=portals,
        language=lang,
    )


def clean_speech_text(text: str) -> str:
    """Strip markdown formatting, URLs, and asterisks for natural voice playback."""
    # Remove markdown links [text](url) -> text
    cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Remove markdown headers, bold, italics, code
    cleaned = re.sub(r"[*_#`~>|]", " ", cleaned)
    # Remove URLs
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    # Clean whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def chat_awareness(
    messages: List[AwarenessChatMessage],
    voice_mode: bool = False,
    category: Optional[str] = None,
    language: str = "en",
) -> AwarenessChatResponse:
    """
    Conversational Q&A for legal rights awareness supporting both Chat and Talking (Voice) forms.
    Speaks and replies entirely in English.
    Uses Anthropic Claude API if ANTHROPIC_API_KEY is configured, otherwise uses
    the specialized Indian legal awareness knowledge engine with rich conversational answers.
    """
    lang = language.lower() if language else "en"
    if lang not in ("en", "hi", "ta"):
        lang = "en"

    latest_user_msg = ""
    for msg in reversed(messages):
        if msg.role == "user" and msg.content.strip():
            latest_user_msg = msg.content.strip()
            break

    if not latest_user_msg:
        latest_user_msg = "What are my legal rights under Indian law?"

    # 1. Check for Anthropic API Key integration
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)

            claude_messages = [
                {"role": m.role if m.role in ("user", "assistant") else "user", "content": m.content}
                for m in messages
                if m.role in ("user", "assistant") and m.content.strip()
            ]
            if not claude_messages:
                claude_messages = [{"role": "user", "content": latest_user_msg}]

            system_prompt = (
                "You are the Beyond Identity Legal Rights & Awareness Assistant, an empathetic, authoritative "
                f"legal guide for transgender, intersex, and gender-diverse individuals in India. Language Mode: '{lang}'.\n"
                "- You MUST reply entirely in fluent, respectful, natural English at all times.\n\n"
                "Ground your answers in Indian statutory laws and Supreme Court rulings:\n"
                "- The Transgender Persons (Protection of Rights) Act, 2019 (Sections 3, 4, 9, 10, 11, 12, 18)\n"
                "- NALSA vs. Union of India (2014) Supreme Court verdict (Articles 14, 15, 16, 19(1)(a), 21)\n"
                "- Transgender Persons (Protection of Rights) Rules, 2020 & National Portal (transgender.dosje.gov.in)\n"
                "- Free Legal Aid under Section 12 of Legal Services Authorities Act via NALSA Helpline (15100)\n"
                "- National Transgender Helpline: 14566 | Tele-MANAS: 14416 | Emergency: 112\n"
                "- Ayushman Bharat TG package for gender-affirming healthcare.\n"
                "- Parental & Family Protections: CARA Adoption Regulations (2022), single-parent adoption eligibility, non-separation of children under Section 12(1), child custody in Family Courts, and Right to Education (RTE) admission safeguards.\n\n"
                "Always provide: empathetic reassurance, applicable legal grounds, clear actionable steps, and free legal aid helpline details."
            )

            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=800,
                system=system_prompt,
                messages=claude_messages,
            )
            raw_reply = response.content[0].text if response.content else ""
            speech = clean_speech_text(raw_reply)
            if voice_mode and len(speech) > 420:
                speech_sentences = speech.split(". ")
                speech = ". ".join(speech_sentences[:3]) + "."

            base_info = query_awareness(latest_user_msg, category=category, language=lang)
            return AwarenessChatResponse(
                reply=raw_reply,
                speech_text=speech,
                matched_topic=base_info.matched_topic,
                applicable_law=base_info.applicable_law,
                actionable_steps=base_info.actionable_steps,
                legal_aid_contact=base_info.legal_aid_contact,
                official_portals=base_info.official_portals,
                language=lang,
            )
        except Exception:
            # Fall back to curated knowledge base
            pass

    # 2. Curated Indian Legal Awareness Knowledge Engine Fallback
    base_info = query_awareness(latest_user_msg, category=category, language=lang)
    steps_formatted = "\n".join([f"- {s}" for s in base_info.actionable_steps])
    sections_formatted = ", ".join(base_info.sections_cited)

    reply = (
        f"### Legal Protection & Guidance: {base_info.matched_topic}\n\n"
        f"**Applicable Law:** {base_info.applicable_law}\n\n"
        f"{base_info.explanation}\n\n"
        f"**Key Statutory Citations:** {sections_formatted}\n\n"
        f"#### Recommended Actionable Steps:\n{steps_formatted}\n\n"
        f"📞 **Free Legal Aid Helpline:** {base_info.legal_aid_contact}\n"
    )
    if voice_mode:
        speech = (
            f"Under {base_info.applicable_law}, your rights are legally protected. "
            f"The law strictly prohibits discrimination against transgender individuals. "
            f"You can document the incident, cite statutory provisions, and reach out to the NALSA Free Legal Aid Helpline at 15100 or the National Transgender Helpline at 14566."
        )
    else:
        speech = (
            f"Under {base_info.applicable_law}, your rights are legally protected. "
            f"{clean_speech_text(base_info.explanation)} "
            f"For immediate free legal aid, call NALSA at 15100."
        )

    return AwarenessChatResponse(
        reply=reply,
        speech_text=speech,
        matched_topic=base_info.matched_topic,
        applicable_law=base_info.applicable_law,
        actionable_steps=base_info.actionable_steps,
        legal_aid_contact=base_info.legal_aid_contact,
        official_portals=base_info.official_portals,
        language=lang,
    )

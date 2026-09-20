"""
AI Awareness Module: Know Your Rights & Legal Protections.
Contains curated knowledge and intelligent Q&A retrieval on Indian laws,
including the Transgender Persons (Protection of Rights) Act 2019,
NALSA (2014) Supreme Court verdict, and legal aid remedies.
"""
from typing import List, Dict, Any, Optional
from app.schemas import AwarenessTopicOut, AwarenessQueryResponse


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


def 
query_awareness(query_text: str, category: Optional[str] = None) -> AwarenessQueryResponse:
    """
    Intelligent keyword and semantic matching against Indian legal rights,
    returning plain-English explanations, applicable law citations, and step-by-step action plans.
    """
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

    actionable_steps = [
        f"1. Document the incident: Note dates, names of perpetrators/institutions, witnesses, and save written/email records.",
        f"2. Cite statutory provisions: Inform the violating party that their actions violate {best_topic['title']}.",
        f"3. Lodge an official complaint: {best_topic['remedies'][0]}",
        f"4. Seek Free Legal Support: Transgender individuals are entitled to free legal counsel under Section 12 of the Legal Services Authorities Act via NALSA Helpline (15100).",
    ]

    portals = []
    if best_topic.get("official_portal"):
        portals.append(best_topic["official_portal"])
    portals.append("https://transgender.dosje.gov.in")
    portals.append("https://nalsa.gov.in")

    return AwarenessQueryResponse(
        query=query_text,
        matched_topic=best_topic["title"],
        applicable_law=best_topic["act_or_ruling"],
        sections_cited=sections_cited,
        explanation=explanation,
        actionable_steps=actionable_steps,
        legal_aid_contact="NALSA Free Legal Aid Toll-Free Helpline: 15100 | National Transgender Helpline: 14566",
        official_portals=portals,
    )

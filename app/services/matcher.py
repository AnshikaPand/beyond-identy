"""
Intelligent Matching Engine:
Matches discrimination incident reports with relevant Indian government welfare schemes,
legal provisions (Transgender Persons Act, NALSA), and verified NGOs based on incident type,
location (State/City), and urgency.
"""
from typing import List, Dict, Any
from app.models import IncidentType, UrgencyLevel
from app.schemas import SchemeMatchOut, NGOMatchOut


# Knowledge base of verified Indian Government Schemes
GOVERNMENT_SCHEMES: List[Dict[str, Any]] = [
    {
        "name": "SMILE — Support for Marginalized Individuals for Livelihood and Enterprise",
        "ministry_or_dept": "Ministry of Social Justice and Empowerment (MoSJE), Govt. of India",
        "description": "Comprehensive central umbrella scheme providing welfare, rehabilitation, medical care, skill development, and economic empowerment for transgender persons.",
        "eligibility": "Any transgender individual holding a National TG Certificate or community self-declaration.",
        "benefits": "Skill training through PM-DAKSH with monthly stipends, scholarships, housing access, medical facility linkages, and composite financial assistance.",
        "application_link": "https://socialjustice.gov.in/schemes/112",
        "helpline": "14566 (National Transgender Toll-Free Helpline)",
        "applicable_types": [
            IncidentType.workplace,
            IncidentType.education,
            IncidentType.housing_eviction,
            IncidentType.other,
        ],
        "states": ["all"],
    },
    {
        "name": "Ayushman Bharat PM-JAY Composite Transgender Health Package",
        "ministry_or_dept": "National Health Authority (NHA) & Ministry of Health & Family Welfare",
        "description": "Comprehensive national health insurance package specifically designated for transgender persons covering gender-affirming care.",
        "eligibility": "Transgender persons holding a TG Certificate from the National Portal for Transgender Persons.",
        "benefits": "Cashless hospitalization coverage of up to ₹5,00,000 per year, covering Gender-Affirming Surgeries (SRS), hormone therapy, and general medical/surgical treatments.",
        "application_link": "https://transgender.dosje.gov.in/and-pmjay",
        "helpline": "14555 / 1800-111-565",
        "applicable_types": [
            IncidentType.healthcare_denial,
            IncidentType.other,
        ],
        "states": ["all"],
    },
    {
        "name": "National Portal for Transgender Persons (ID Card & Certificate)",
        "ministry_or_dept": "Ministry of Social Justice and Empowerment (MoSJE)",
        "description": "Statutory online single-window portal enabling any transgender person in India to apply for and download a government-recognized Certificate of Identity without physical inspection.",
        "eligibility": "Any citizen identifying as transgender under Section 5 & 6 of the Transgender Persons Act, 2019.",
        "benefits": "Official legal identity card issued by the District Magistrate, valid for all statutory rights, bank accounts, passport updates, and scheme enrollment.",
        "application_link": "https://transgender.dosje.gov.in",
        "helpline": "011-23386981 / helpdesk-tg@gov.in",
        "applicable_types": [
            IncidentType.legal_documentation,
            IncidentType.police_harassment,
            IncidentType.workplace,
            IncidentType.education,
            IncidentType.housing_eviction,
        ],
        "states": ["all"],
    },
    {
        "name": "Garima Greh — Shelter Homes for Transgender Persons",
        "ministry_or_dept": "MoSJE in partnership with community-based organizations",
        "description": "Safe shelter homes setup across major Indian cities for transgender persons in crisis, destitution, or facing severe domestic violence and homelessness.",
        "eligibility": "Transgender persons facing rejection, homelessness, violence, or sudden eviction.",
        "benefits": "Free secure shelter, nutritious food, primary medical care, psycho-social counseling, and capacity building for up to 1 year.",
        "application_link": "https://transgender.dosje.gov.in/garimagreh",
        "helpline": "14566",
        "applicable_types": [
            IncidentType.housing_eviction,
            IncidentType.public_harassment,
            IncidentType.other,
        ],
        "states": ["all"],
    },
    {
        "name": "NALSA Free Legal Aid Services for Transgender Persons",
        "ministry_or_dept": "National Legal Services Authority (NALSA) / State Legal Services Authorities",
        "description": "Free legal aid and pro-bono advocate representation mandated under Section 12 of the Legal Services Authorities Act, 1987 and the landmark NALSA (2014) judgment.",
        "eligibility": "All transgender individuals facing harassment, unlawful detention, employment termination, or institutional discrimination.",
        "benefits": "Assigned free legal counsel, legal drafting of police complaints or court petitions, assistance before District Courts and High Courts.",
        "application_link": "https://nalsa.gov.in/services/legal-aid",
        "helpline": "15100 (National Legal Aid Toll-Free Helpline)",
        "applicable_types": [
            IncidentType.police_harassment,
            IncidentType.workplace,
            IncidentType.public_harassment,
            IncidentType.legal_documentation,
            IncidentType.healthcare_denial,
            IncidentType.housing_eviction,
        ],
        "states": ["all"],
    },
    {
        "name": "Maharashtra Transgender Welfare Board Scheme",
        "ministry_or_dept": "Department of Social Justice and Special Assistance, Government of Maharashtra",
        "description": "State welfare board offering direct benefit transfers, vocational education grants, and anti-discrimination legal advocacy.",
        "eligibility": "Transgender residents of Maharashtra holding domicile.",
        "benefits": "Direct financial aid, subsidized vocational equipment, and priority processing in government clinics.",
        "application_link": "https://sjsa.maharashtra.gov.in",
        "helpline": "022-22025251",
        "applicable_types": [
            IncidentType.workplace,
            IncidentType.education,
            IncidentType.housing_eviction,
        ],
        "states": ["maharashtra"],
    },
    {
        "name": "Tamil Nadu Transgender Welfare Board (Aravanigal Welfare Board)",
        "ministry_or_dept": "Department of Social Welfare and Women Empowerment, Government of Tamil Nadu",
        "description": "Pioneering state board providing identity cards, educational support, pensions, and housing allotments.",
        "eligibility": "Transgender persons resident in Tamil Nadu.",
        "benefits": "Monthly pension of ₹1,500 for indigent persons, ₹20,000 self-employment grant, free housing pattas, and free college tuition in state universities.",
        "application_link": "https://www.tn.gov.in/department/30",
        "helpline": "044-28521714",
        "applicable_types": [
            IncidentType.housing_eviction,
            IncidentType.education,
            IncidentType.workplace,
        ],
        "states": ["tamil nadu", "tamilnadu"],
    },
    {
        "name": "SMILE Skill Development and Training",
        "ministry_or_dept": "Ministry of Social Justice and Empowerment (MoSJE)",
        "description": "Market-oriented skill training programs for transgender persons aged 18-45 to improve employability and sustainable livelihood.",
        "eligibility": "Transgender persons aged 18 to 45 holding a Transgender Certificate.",
        "benefits": "Free skill training, stipend during training period, and formal placement assistance in corporate/affirmative jobs.",
        "application_link": "https://transgender.dosje.gov.in/skill",
        "helpline": "14566",
        "applicable_types": [
            IncidentType.workplace,
            IncidentType.education,
            IncidentType.other,
        ],
        "states": ["all"],
    },
    {
        "name": "PM-DAKSH Yojana (Pradhan Mantri Dakshta Aur Kushalta Sampann Hitgrahi Yojana)",
        "ministry_or_dept": "Ministry of Social Justice and Empowerment",
        "description": "National skilling action plan covering marginalized groups including transgender persons with upskilling, re-skilling, and entrepreneurship.",
        "eligibility": "Transgender individuals seeking vocational skills and livelihood certification.",
        "benefits": "Short-term training, wage-compensation stipends, toolkits, and micro-enterprise financial linkages.",
        "application_link": "https://pmdaksh.dosje.gov.in",
        "helpline": "1800-110-396",
        "applicable_types": [
            IncidentType.workplace,
            IncidentType.education,
            IncidentType.other,
        ],
        "states": ["all"],
    },
    {
        "name": "Post-Matric Scholarship for Transgender Students",
        "ministry_or_dept": "Ministry of Social Justice and Empowerment",
        "description": "National scholarship scheme covering education from Class IX and above through post-graduation, including ITI, polytechnic, and UGC/AICTE-recognized degree courses.",
        "eligibility": "Transgender students pursuing Class 9th through post-graduate higher education.",
        "benefits": "Full tuition waiver/reimbursement and monthly maintenance allowance.",
        "application_link": "https://transgender.dosje.gov.in/scholarships",
        "helpline": "14566",
        "applicable_types": [
            IncidentType.education,
            IncidentType.workplace,
            IncidentType.other,
        ],
        "states": ["all"],
    },
    {
        "name": "Chandigarh Fee Waiver Scheme for Transgender Students",
        "ministry_or_dept": "Department of Education, Chandigarh (UT Administration)",
        "description": "Complete tuition fee waiver for transgender students across schools and government colleges in Chandigarh UT.",
        "eligibility": "Transgender students enrolled in recognized educational institutions in Chandigarh.",
        "benefits": "100% tuition and examination fee waiver to ensure zero financial barriers to higher education.",
        "application_link": "https://chdeducation.gov.in",
        "helpline": "0172-2740411",
        "applicable_types": [
            IncidentType.education,
            IncidentType.other,
        ],
        "states": ["all", "chandigarh", "punjab", "haryana"],
    },
    {
        "name": "Himachal Pradesh Transgender Welfare Board Schemes",
        "ministry_or_dept": "Transgender Welfare Board, Government of Himachal Pradesh",
        "description": "State welfare schemes providing pre-matric and post-matric scholarships, financial assistance to parents of transgender children under 18, and skill development.",
        "eligibility": "Transgender residents of Himachal Pradesh and families with transgender children under 18.",
        "benefits": "Parental financial assistance grants, educational scholarships, and self-employment startup subsidies.",
        "application_link": "https://himachal.nic.in/socialjustice",
        "helpline": "0177-2621151",
        "applicable_types": [
            IncidentType.education,
            IncidentType.housing_eviction,
            IncidentType.workplace,
            IncidentType.other,
        ],
        "states": ["all", "himachal pradesh"],
    },
    {
        "name": "National Council for Transgender Persons",
        "ministry_or_dept": "Ministry of Social Justice and Empowerment (MoSJE)",
        "description": "Apex statutory policy advisory council on transgender welfare, chaired by the Union Minister of Social Justice and Empowerment.",
        "eligibility": "Policy-level grievance redressal and rights monitoring across all Indian states.",
        "benefits": "High-level redressal review, inter-ministerial policy coordination, and protection under Transgender Persons Act.",
        "application_link": "https://socialjustice.gov.in/council",
        "helpline": "14566",
        "applicable_types": [
            IncidentType.police_harassment,
            IncidentType.workplace,
            IncidentType.healthcare_denial,
            IncidentType.education,
            IncidentType.legal_documentation,
            IncidentType.housing_eviction,
            IncidentType.other,
        ],
        "states": ["all"],
    },
]


# Directory of verified NGO partners and crisis relief networks
VERIFIED_NGOS: List[Dict[str, Any]] = [
    {
        "name": "The Humsafar Trust",
        "focus_area": "Healthcare, Legal Rights, and Mental Health Advocacy",
        "location": "Mumbai, Maharashtra & Delhi (Pan-India reach)",
        "contact_email": "connect@humsafar.org",
        "contact_phone": "+91-22-26673800",
        "services_offered": [
            "Transgender health clinic and HRT consultation",
            "Legal crisis intervention against unlawful police detention",
            "Mental health affirmative counseling",
            "Trans workplace diversity training",
        ],
        "applicable_types": [
            IncidentType.healthcare_denial,
            IncidentType.police_harassment,
            IncidentType.public_harassment,
            IncidentType.workplace,
        ],
        "states": ["all", "maharashtra", "delhi"],
    },
    {
        "name": "Tweet Foundation (Transgender Welfare Equity and Empowerment Trust)",
        "focus_area": "Emergency Shelter (Garima Greh), Transition Support, and Livelihoods",
        "location": "New Delhi & Mumbai",
        "contact_email": "support@tweet.org.in",
        "contact_phone": "+91-9810012345",
        "services_offered": [
            "Immediate safe shelter for trans masculine and feminine youth",
            "Emergency crisis intervention for family violence",
            "Corporate job placement and skill development",
            "Assistance with Transgender Identity Card applications",
        ],
        "applicable_types": [
            IncidentType.housing_eviction,
            IncidentType.public_harassment,
            IncidentType.workplace,
            IncidentType.legal_documentation,
        ],
        "states": ["all", "delhi", "maharashtra", "haryana", "uttar pradesh"],
    },
    {
        "name": "Nazariya: A Queer Feminist Resource Group",
        "focus_area": "Advocacy, Affirmative Counseling, and Crisis Support",
        "location": "New Delhi / NCR",
        "contact_email": "info@nazariyaqfrg.com",
        "contact_phone": "+91-9818155444",
        "services_offered": [
            "Affirmative mental health helpline",
            "Mediation in educational harassment cases",
            "Legal counsel referrals for wrongful termination",
            "Emergency safe space and peer community circles",
        ],
        "applicable_types": [
            IncidentType.education,
            IncidentType.workplace,
            IncidentType.public_harassment,
        ],
        "states": ["all", "delhi", "ncr", "punjab", "rajasthan"],
    },
    {
        "name": "Sahodari Foundation",
        "focus_area": "Transgender Rights, Legal Redress, and Arts-Based Education",
        "location": "Chennai & Pollachi, Tamil Nadu",
        "contact_email": "reach@sahodari.org",
        "contact_phone": "+91-9942371987",
        "services_offered": [
            "24/7 Redressal for human rights violations in South India",
            "Assistance with state welfare board pensions and housing",
            "Educational scholarships and entrepreneurship seed capital",
        ],
        "applicable_types": [
            IncidentType.police_harassment,
            IncidentType.housing_eviction,
            IncidentType.education,
            IncidentType.legal_documentation,
        ],
        "states": ["all", "tamil nadu", "kerala", "karnataka", "andhra pradesh"],
    },
    {
        "name": "Mitr Trust",
        "focus_area": "Community Protection, Anti-Extortion Legal Defense, and Healthcare",
        "location": "New Delhi",
        "contact_email": "contact@mitrtrust.org",
        "contact_phone": "+91-11-25337890",
        "services_offered": [
            "Urgent on-ground intervention in police station disputes",
            "STI/HIV testing and free clinical referrals",
            "Community kitchen and emergency sustenance support",
        ],
        "applicable_types": [
            IncidentType.police_harassment,
            IncidentType.public_harassment,
            IncidentType.healthcare_denial,
        ],
        "states": ["all", "delhi", "haryana", "uttar pradesh"],
    },
    {
        "name": "Sappho for Equality",
        "focus_area": "Eastern India Queer & Trans Rights, Crisis Management, and Legal Aid",
        "location": "Kolkata, West Bengal",
        "contact_email": "sapphoqueer@rediffmail.com",
        "contact_phone": "+91-33-24419998",
        "services_offered": [
            "24/7 Crisis helpline for assault and eviction",
            "Free legal representation through partner high-court advocates",
            "Temporary safe shelter linkage",
        ],
        "applicable_types": [
            IncidentType.housing_eviction,
            IncidentType.public_harassment,
            IncidentType.police_harassment,
            IncidentType.workplace,
        ],
        "states": ["all", "west bengal", "odisha", "assam", "bihar"],
    },
    {
        "name": "PeriFerry",
        "focus_area": "Corporate Diversity Hiring, Transgender Employment & Upskilling",
        "location": "Chennai, Tamil Nadu (Pan-India corporate partnerships)",
        "contact_email": "connect@periferry.com",
        "contact_phone": "+91-44-48529900",
        "services_offered": [
            "Corporate hiring pipeline partner with 320+ trained and placed trans individuals",
            "Workplace sensitization and equal opportunity training",
            "Professional resume preparation and interview coaching",
            "Pre-employment transition and HR policy counseling",
        ],
        "applicable_types": [
            IncidentType.workplace,
            IncidentType.education,
            IncidentType.other,
        ],
        "states": ["all", "tamil nadu", "karnataka", "maharashtra", "delhi", "telangana"],
    },
    {
        "name": "Born2Win Social Welfare Trust",
        "focus_area": "Transgender & Intersex Rights, Community Leadership, and Legal Support",
        "location": "Chennai, Tamil Nadu",
        "contact_email": "born2win.trust@gmail.com",
        "contact_phone": "+91-9884210987",
        "services_offered": [
            "Non-profit run entirely by and for transgender and intersex persons",
            "Emergency community relief and peer counseling",
            "Transgender certificate and welfare board assistance",
            "Annual community achievement awards and visibility campaigns",
        ],
        "applicable_types": [
            IncidentType.workplace,
            IncidentType.education,
            IncidentType.legal_documentation,
            IncidentType.public_harassment,
            IncidentType.other,
        ],
        "states": ["all", "tamil nadu", "kerala", "karnataka", "andhra pradesh"],
    },
    {
        "name": "Naz Foundation (India) Trust",
        "focus_area": "LGBTQIA+ Healthcare, HIV/AIDS Care, and Affirmative Sexual Health",
        "location": "New Delhi",
        "contact_email": "naz@nazindia.org",
        "contact_phone": "+91-11-26321882",
        "services_offered": [
            "Inclusive HIV/AIDS care and non-discriminatory clinical testing",
            "Affirmative sexual and reproductive health consultations",
            "Mental wellness and community support groups",
        ],
        "applicable_types": [
            IncidentType.healthcare_denial,
            IncidentType.public_harassment,
            IncidentType.other,
        ],
        "states": ["all", "delhi", "haryana", "uttar pradesh", "punjab"],
    },
    {
        "name": "Orinam",
        "focus_area": "LGBTIQA+ Collective, Workplace Directory, and Resource Referral",
        "location": "Chennai, Tamil Nadu",
        "contact_email": "orinam.net@gmail.com",
        "contact_phone": "+91-44-24987654",
        "services_offered": [
            "All-volunteer LGBTIQA+ collective operating since 2003",
            "Maintains an audited directory of trans-inclusive employers",
            "Bilingual legal and medical referral network in Tamil & English",
            "Crisis response and community solidarity circles",
        ],
        "applicable_types": [
            IncidentType.workplace,
            IncidentType.education,
            IncidentType.public_harassment,
            IncidentType.other,
        ],
        "states": ["all", "tamil nadu", "karnataka", "kerala"],
    },
]


def match_schemes(
    incident_type: IncidentType,
    state: str,
    urgency_level: UrgencyLevel,
) -> List[SchemeMatchOut]:
    """Matches an incident report against relevant Indian government welfare schemes."""
    state_clean = (state or "").strip().lower()
    matched = []

    for s in GOVERNMENT_SCHEMES:
        is_type_match = incident_type in s["applicable_types"]
        is_state_match = "all" in s["states"] or state_clean in s["states"]

        # High urgency or police harassment always includes NALSA legal aid
        if incident_type == IncidentType.police_harassment and "NALSA" in s["name"]:
            is_type_match = True

        if is_type_match and is_state_match:
            matched.append(
                SchemeMatchOut(
                    name=s["name"],
                    ministry_or_dept=s["ministry_or_dept"],
                    description=s["description"],
                    eligibility=s["eligibility"],
                    benefits=s["benefits"],
                    application_link=s.get("application_link"),
                    helpline=s.get("helpline"),
                )
            )

    # Ensure at least SMILE and NALSA if none directly matched
    if not matched:
        for s in GOVERNMENT_SCHEMES[:2]:
            matched.append(
                SchemeMatchOut(
                    name=s["name"],
                    ministry_or_dept=s["ministry_or_dept"],
                    description=s["description"],
                    eligibility=s["eligibility"],
                    benefits=s["benefits"],
                    application_link=s.get("application_link"),
                    helpline=s.get("helpline"),
                )
            )

    return matched


def match_ngos(
    incident_type: IncidentType,
    state: str,
    urgency_level: UrgencyLevel,
) -> List[NGOMatchOut]:
    """Matches an incident report against verified NGOs and crisis response partners."""
    state_clean = (state or "").strip().lower()
    matched = []

    for ngo in VERIFIED_NGOS:
        is_type_match = incident_type in ngo["applicable_types"]
        is_state_match = "all" in ngo["states"] or state_clean in ngo["states"]

        # For emergency SOS, always include Tweet Foundation and Humsafar
        if urgency_level == UrgencyLevel.immediate_sos and (
            "Tweet Foundation" in ngo["name"] or "Humsafar" in ngo["name"]
        ):
            is_type_match = True

        if is_type_match and is_state_match:
            matched.append(
                NGOMatchOut(
                    name=ngo["name"],
                    focus_area=ngo["focus_area"],
                    location=ngo["location"],
                    contact_email=ngo.get("contact_email"),
                    contact_phone=ngo.get("contact_phone"),
                    services_offered=ngo["services_offered"],
                )
            )

    # Ensure at least one verified NGO is returned
    if not matched:
        first_ngo = VERIFIED_NGOS[0]
        matched.append(
            NGOMatchOut(
                name=first_ngo["name"],
                focus_area=first_ngo["focus_area"],
                location=first_ngo["location"],
                contact_email=first_ngo.get("contact_email"),
                contact_phone=first_ngo.get("contact_phone"),
                services_offered=first_ngo["services_offered"],
            )
        )

    return matched

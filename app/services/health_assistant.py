"""
AI Health Assistant Decision-Tree Prototype.
Provides an interactive, rule-based expert triage and guidance system
for transgender individuals navigating crisis support, safe hormone therapy (HRT),
gender-affirmation surgery protocols, and affirmative mental health care.
"""
from typing import Dict, Any, Optional
from app.schemas import DecisionNode, DecisionNodeOption, HealthTraverseResponse


HEALTH_DISCLAIMER = (
    "DISCLAIMER: This tool provides educational guidance and triage navigation based on "
    "WPATH Standards of Care and Indian clinical guidelines. It is NOT a substitute for "
    "professional medical advice, clinical diagnosis, or treatment. Always consult a qualified "
    "endocrinologist, psychiatrist, or medical professional before starting, altering, or stopping "
    "any medication."
)

DECISION_NODES: Dict[str, Dict[str, Any]] = {
    "root": {
        "node_id": "root",
        "title": "AI Health Assistant — Main Navigation",
        "category": "Triage",
        "message": (
            "Welcome to the Beyond Identity Health Assistant. We provide confidential, "
            "evidence-based guidance tailored for trans and gender-diverse individuals in India. "
            "What support or information are you seeking today?"
        ),
        "clinical_notes": "Triage entry point covering emergency mental health, safe transition, and general healthcare.",
        "warnings": None,
        "recommended_actions": None,
        "helpline_contacts": [
            "Tele-MANAS: 14416 (24x7 Free Mental Health)",
            "Kiran Mental Health Helpline: 1800-599-0019",
            "National Emergency: 112",
        ],
        "options": [
            {
                "option_id": "opt_crisis",
                "text": "1. I am in emotional distress or need immediate crisis/suicide prevention support",
                "next_node_id": "crisis_sos",
            },
            {
                "option_id": "opt_hrt",
                "text": "2. I want safe, clinical guidance on Hormone Replacement Therapy (HRT)",
                "next_node_id": "hrt_start",
            },
            {
                "option_id": "opt_surgery",
                "text": "3. I want information on Gender Affirmation Surgeries & Ayushman Bharat coverage",
                "next_node_id": "surgery_start",
            },
            {
                "option_id": "opt_mental_health",
                "text": "4. I need affirmative mental health support & dysphoria management",
                "next_node_id": "mental_health_start",
            },
            {
                "option_id": "opt_general_health",
                "text": "5. General healthcare, STI/HIV screening, and inclusive clinic referrals",
                "next_node_id": "general_health_start",
            },
        ],
        "is_leaf": False,
    },
    "crisis_sos": {
        "node_id": "crisis_sos",
        "title": "Immediate Crisis & Emotional Support",
        "category": "Emergency SOS",
        "message": (
            "You are not alone. There is compassionate, non-judgmental support available right now. "
            "If you or someone you know is feeling overwhelmed, hopeless, or unsafe, please reach out "
            "to these free 24x7 helplines immediately."
        ),
        "clinical_notes": "Immediate safety protocol: connect with active tele-counseling immediately.",
        "warnings": [
            "If you are in immediate physical danger, call 112 immediately or reach the nearest hospital emergency room.",
        ],
        "recommended_actions": [
            "Dial Tele-MANAS (14416) — Govt of India's 24x7 multi-lingual tele-mental health service.",
            "Dial Kiran Helpline (1800-599-0019) for psychiatric triage and distress relief.",
            "If you are facing domestic violence or homelessness, contact Tweet Foundation emergency transit shelter at +91-9810012345.",
        ],
        "helpline_contacts": [
            "Tele-MANAS: 14416 (Toll-Free, 24x7)",
            "Kiran Mental Health: 1800-599-0019 (24x7)",
            "Vandrevala Foundation: +91-9999666555",
            "Tweet Foundation Shelter SOS: +91-9810012345",
        ],
        "options": [
            {
                "option_id": "opt_back_root",
                "text": "Return to Main Health Menu",
                "next_node_id": "root",
            }
        ],
        "is_leaf": True,
    },
    "hrt_start": {
        "node_id": "hrt_start",
        "title": "Hormone Replacement Therapy (HRT) Guidance",
        "category": "Gender-Affirming Care",
        "message": (
            "Hormone Replacement Therapy (HRT) is an essential component of gender-affirming care for "
            "many individuals. To ensure your long-term health, hormone regimens MUST be individualized, "
            "clinically supervised by an endocrinologist, and monitored with regular lab blood panels."
        ),
        "clinical_notes": "WPATH SoC 8 guidelines require informed consent or comprehensive diagnostic evaluation before initiating endocrinological regimens.",
        "warnings": [
            "Never purchase prescription hormones from unverified online stores or unauthorized local vendors.",
            "Self-medication without blood tests can cause life-threatening complications like pulmonary embolism, stroke, or liver damage.",
        ],
        "recommended_actions": [
            "Consult a registered endocrinologist or queer-affirmative physician.",
            "Review the essential baseline blood tests required before starting.",
        ],
        "helpline_contacts": [
            "The Humsafar Trust Gender Clinic: +91-22-26673800",
            "National Transgender Helpline: 14566",
        ],
        "options": [
            {
                "option_id": "opt_hrt_protocol",
                "text": "What blood tests and medical evaluations are needed before starting HRT?",
                "next_node_id": "hrt_protocol",
            },
            {
                "option_id": "opt_hrt_diy",
                "text": "I was thinking of starting hormones on my own (DIY). What are the specific risks?",
                "next_node_id": "hrt_diy_warning",
            },
            {
                "option_id": "opt_hrt_monitoring",
                "text": "How often do I need follow-up tests once on HRT?",
                "next_node_id": "hrt_monitoring",
            },
            {
                "option_id": "opt_back_root",
                "text": "Return to Main Health Menu",
                "next_node_id": "root",
            },
        ],
        "is_leaf": False,
    },
    "hrt_diy_warning": {
        "node_id": "hrt_diy_warning",
        "title": "Medical Advisory: Risks of Unsupervised (DIY) Hormone Self-Medication",
        "category": "Safety Alert",
        "message": (
            "We understand that accessing doctors can be intimidating due to fear of gatekeeping or judgment. "
            "However, taking hormones without medical supervision carries severe health hazards that can cause permanent damage."
        ),
        "clinical_notes": "High doses do not speed up feminization or masculinization; they saturate receptors and elevate thromboembolic/hepatic risks.",
        "warnings": [
            "Deep Vein Thrombosis (DVT) & Pulmonary Embolism: Excess estrogens dramatically increase blood clot risk.",
            "Liver & Kidney Toxicity: High or incorrect oral doses cause acute elevation in liver enzymes (AST/ALT).",
            "Polycythemia: Unmonitored testosterone can cause excessive red blood cell count, thickening blood and risking heart attacks.",
            "Endocrine Shutdown: Inappropriate dosages disrupt natural pituitary axis function and bone mineral density.",
        ],
        "recommended_actions": [
            "Reach out to Beyond Identity's directory of verified queer-affirmative doctors who practice without gatekeeping.",
            "If cost is a barrier, access government hospital endocrinology departments (e.g. AIIMS, KEM, Lokmanya Tilak) where hormone therapy consultations are free/nominal.",
        ],
        "helpline_contacts": [
            "Humsafar Trust Medical Team: +91-22-26673800",
        ],
        "options": [
            {
                "option_id": "opt_see_protocol",
                "text": "Learn the safe, doctor-approved blood testing protocol",
                "next_node_id": "hrt_protocol",
            },
            {
                "option_id": "opt_back_root",
                "text": "Return to Main Health Menu",
                "next_node_id": "root",
            },
        ],
        "is_leaf": False,
    },
    "hrt_protocol": {
        "node_id": "hrt_protocol",
        "title": "Clinical HRT Roadmap & Required Blood Panels",
        "category": "Clinical Protocols",
        "message": (
            "Prior to prescribing hormones, standard Indian endocrinological practice requires baseline blood work "
            "to establish normal organ function and hormone reference levels."
        ),
        "clinical_notes": "Key lab panels must be reviewed by the treating physician prior to dosage titration.",
        "warnings": None,
        "recommended_actions": [
            "1. Complete Blood Count (CBC) with Hematocrit / Hemoglobin",
            "2. Liver Function Test (LFT: Bilirubin, SGOT/AST, SGPT/ALT, Alkaline Phosphatase)",
            "3. Renal Function Test (KFT: Serum Creatinine, Blood Urea Nitrogen, Electrolytes)",
            "4. Fasting Blood Glucose & HbA1c",
            "5. Lipid Profile (Total Cholesterol, Triglycerides, HDL, LDL)",
            "6. Baseline Hormone Panel: Total Testosterone, Serum Estradiol (E2), Serum Prolactin",
            "7. Baseline Blood Pressure and Cardiovascular screening",
        ],
        "helpline_contacts": [
            "National TG Portal Helpline: 14566",
        ],
        "options": [
            {
                "option_id": "opt_hrt_monitoring",
                "text": "What does the follow-up monitoring schedule look like?",
                "next_node_id": "hrt_monitoring",
            },
            {
                "option_id": "opt_back_root",
                "text": "Return to Main Health Menu",
                "next_node_id": "root",
            },
        ],
        "is_leaf": False,
    },
    "hrt_monitoring": {
        "node_id": "hrt_monitoring",
        "title": "Long-term Monitoring Schedule on HRT",
        "category": "Maintenance Care",
        "message": (
            "Once started on HRT, follow-up tests are typically scheduled at 3 months, 6 months, 12 months, "
            "and annually thereafter to titrate hormone levels into target physiological ranges safely."
        ),
        "clinical_notes": "Monitor serum testosterone and estradiol at trough levels (just prior to next injection/dose).",
        "warnings": [
            "Report sudden leg swelling, persistent severe calf pain, shortness of breath, or yellowing of eyes/skin immediately to emergency care.",
        ],
        "recommended_actions": [
            "Keep an organized file of all historical lab results to track your hormonal progression.",
            "Schedule annual bone mineral density (DEXA) scans if taking gonadotropin-releasing hormone (GnRH) analogs.",
        ],
        "helpline_contacts": None,
        "options": [
            {
                "option_id": "opt_back_root",
                "text": "Return to Main Health Menu",
                "next_node_id": "root",
            }
        ],
        "is_leaf": True,
    },
    "surgery_start": {
        "node_id": "surgery_start",
        "title": "Gender Affirmation Surgeries & Ayushman Bharat Coverage",
        "category": "Surgical Care",
        "message": (
            "Gender Affirmation Surgeries (GAS) represent a significant step in physiological alignment. "
            "In India, surgeries are now covered under government health insurance and recognized by the Supreme Court and TG Act 2019."
        ),
        "clinical_notes": "Surgeries should only be performed by board-certified Plastic Surgeons (MCh) or Urologists with specific training in gender-affirming reconstruction.",
        "warnings": [
            "Never undergo uncertified procedures in non-hospital setups or unverified clinics.",
        ],
        "recommended_actions": [
            "Review the eligibility criteria for Ayushman Bharat PM-JAY coverage (up to ₹5 lakh/year).",
            "Learn about WPATH Standards of Care prerequisites and psychiatric clearance letters.",
        ],
        "helpline_contacts": [
            "Ayushman Bharat National Helpline: 14555",
            "National Portal Helpdesk: 011-23386981",
        ],
        "options": [
            {
                "option_id": "opt_surgery_ayushman",
                "text": "How does Ayushman Bharat PM-JAY cover gender-affirming surgeries?",
                "next_node_id": "surgery_ayushman",
            },
            {
                "option_id": "opt_surgery_prereq",
                "text": "What psychological and medical clearances are needed before surgery?",
                "next_node_id": "surgery_prereq",
            },
            {
                "option_id": "opt_back_root",
                "text": "Return to Main Health Menu",
                "next_node_id": "root",
            },
        ],
        "is_leaf": False,
    },
    "surgery_ayushman": {
        "node_id": "surgery_ayushman",
        "title": "Ayushman Bharat PM-JAY Transgender Beneficiary Package",
        "category": "Government Healthcare Schemes",
        "message": (
            "Under the historic MoU between the Ministry of Social Justice and Empowerment (MoSJE) and the National Health Authority (NHA), "
            "every transgender individual registered on the National Portal for Transgender Persons is eligible for the PM-JAY Composite TG Package."
        ),
        "clinical_notes": "Package covers pre-hospitalization, surgery, hospital stay, medications, and post-operative follow-up up to ₹5,00,000 per annum.",
        "warnings": [
            "You MUST hold a Certificate of Identity issued from the National Portal for Transgender Persons to activate the Ayushman TG card.",
        ],
        "recommended_actions": [
            "Step 1: Download your TG Certificate and Identity Card from https://transgender.dosje.gov.in.",
            "Step 2: Generate your Ayushman Bharat Health Account (ABHA) and TG PM-JAY card.",
            "Step 3: Approach an empaneled government or private tertiary hospital offering plastic surgery & reconstructive services.",
        ],
        "helpline_contacts": [
            "PM-JAY Toll-Free Helpline: 14555",
            "MoSJE Transgender Helpline: 14566",
        ],
        "options": [
            {
                "option_id": "opt_surgery_prereq",
                "text": "What clearances do surgeons require before booking surgery?",
                "next_node_id": "surgery_prereq",
            },
            {
                "option_id": "opt_back_root",
                "text": "Return to Main Health Menu",
                "next_node_id": "root",
            },
        ],
        "is_leaf": False,
    },
    "surgery_prereq": {
        "node_id": "surgery_prereq",
        "title": "Surgical Prerequisites & Clearance Process",
        "category": "Clinical Protocols",
        "message": (
            "In accordance with WPATH SoC v8 and ethical guidelines in India, reconstructive surgeries require "
            "documented informed consent, stability, and evaluation."
        ),
        "clinical_notes": "Psychiatric clearance is required to rule out coercive factors and confirm enduring gender incongruence, NOT to treat identity as an illness.",
        "warnings": None,
        "recommended_actions": [
            "1. Mental Health Clearance: An evaluation letter from a licensed clinical psychologist or psychiatrist (MD/DPM).",
            "2. Living experience / Hormone duration: For genital surgeries, typically 12 months of continuous HRT is recommended unless medically contraindicated.",
            "3. Pre-anesthesia Fitness: Cardiac clearance (ECG/ECHO), chest X-ray, and comprehensive coagulation profile.",
            "4. Post-operative Support Plan: Ensure you have a caregiver and safe recovery environment for 2-4 weeks post-op.",
        ],
        "helpline_contacts": [
            "Humsafar Trust Referral Desk: +91-22-26673800",
        ],
        "options": [
            {
                "option_id": "opt_back_root",
                "text": "Return to Main Health Menu",
                "next_node_id": "root",
            }
        ],
        "is_leaf": True,
    },
    "mental_health_start": {
        "node_id": "mental_health_start",
        "title": "Affirmative Mental Health & Dysphoria Support",
        "category": "Mental Wellness",
        "message": (
            "Gender dysphoria, minority stress, and societal prejudice can take a heavy emotional toll. "
            "Affirmative therapy recognizes that your gender identity is valid and focuses on self-actualization, resilience, and healing."
        ),
        "clinical_notes": "Conversion therapy is strictly prohibited and illegal under the National Medical Commission (NMC) directives.",
        "warnings": [
            "Avoid any practitioner suggesting 'curing', 'changing', or suppressing your gender identity; conversion therapy is banned by NMC and Indian Courts.",
        ],
        "recommended_actions": [
            "Consult verified queer-affirmative counselors listed on Varta Trust or SAATHII directories.",
            "Participate in community support circles and peer mentorship programs.",
        ],
        "helpline_contacts": [
            "Tele-MANAS: 14416 (24x7 Free Mental Health)",
            "Nazariya Affirmative Support: +91-9818155444",
        ],
        "options": [
            {
                "option_id": "opt_back_root",
                "text": "Return to Main Health Menu",
                "next_node_id": "root",
            }
        ],
        "is_leaf": True,
    },
    "general_health_start": {
        "node_id": "general_health_start",
        "title": "General Health, STI/HIV Screening & Inclusive Clinics",
        "category": "General Wellness",
        "message": (
            "Transgender individuals deserve respectful, dignified primary healthcare without intrusive questions "
            "unrelated to their medical concern."
        ),
        "clinical_notes": "Routine preventive care (cardiovascular health, cancer screenings based on present anatomy) is vital.",
        "warnings": None,
        "recommended_actions": [
            "Access free STI and HIV testing at NACO (National AIDS Control Organisation) designated Suraksha Clinics and NGO centers.",
            "Undergo anatomy-specific preventive screenings (e.g. breast/chest tissue checks, pelvic screenings, prostate checks).",
            "Report any instance of healthcare discrimination to Beyond Identity's Incident Reporting portal for escalation.",
        ],
        "helpline_contacts": [
            "NACO Toll-Free Helpline: 1097",
            "Humsafar Healthcare Center: +91-22-26673800",
        ],
        "options": [
            {
                "option_id": "opt_back_root",
                "text": "Return to Main Health Menu",
                "next_node_id": "root",
            }
        ],
        "is_leaf": True,
    },
}


def get_decision_tree() -> DecisionNode:
    """Returns the root node of the decision tree, containing options to explore."""
    root_data = DECISION_NODES["root"]
    return _build_node_schema(root_data)


def traverse_decision_tree(current_node_id: str, option_id: str) -> HealthTraverseResponse:
    """Navigates to the next node in the decision tree based on the user's selected option."""
    current_data = DECISION_NODES.get(current_node_id)
    if not current_data:
        # If node not found, fallback to root
        return HealthTraverseResponse(
            node=_build_node_schema(DECISION_NODES["root"]),
            disclaimer=HEALTH_DISCLAIMER,
        )

    # Find matching option
    next_node_id = "root"
    for opt in current_data.get("options", []):
        if opt["option_id"] == option_id:
            next_node_id = opt["next_node_id"]
            break

    target_data = DECISION_NODES.get(next_node_id, DECISION_NODES["root"])
    return HealthTraverseResponse(
        node=_build_node_schema(target_data),
        disclaimer=HEALTH_DISCLAIMER,
    )


def _build_node_schema(data: Dict[str, Any]) -> DecisionNode:
    """Helper to convert node dictionary to Pydantic DecisionNode."""
    options = [
        DecisionNodeOption(
            option_id=o["option_id"],
            text=o["text"],
            next_node_id=o["next_node_id"],
        )
        for o in data.get("options", [])
    ]

    return DecisionNode(
        node_id=data["node_id"],
        title=data["title"],
        category=data["category"],
        message=data["message"],
        clinical_notes=data.get("clinical_notes"),
        warnings=data.get("warnings"),
        recommended_actions=data.get("recommended_actions"),
        helpline_contacts=data.get("helpline_contacts"),
        options=options,
        is_leaf=data.get("is_leaf", False),
    )

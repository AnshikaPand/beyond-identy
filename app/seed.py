"""
Seed script — populates the database with realistic mock data for the demo phase
(per your project timeline: "Week 2-3: Build components with mock data").

Run with:
    python -m app.seed
"""
from app.database import SessionLocal, Base, engine
from app import models, auth

Base.metadata.create_all(bind=engine)

db = SessionLocal()


def get_or_create_user(name, email, password, role):
    user = db.query(models.User).filter(models.User.email == email).first()
    if user:
        return user
    user = models.User(
        name=name,
        email=email,
        hashed_password=auth.hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def seed():
    print("Seeding users...")
    admin = get_or_create_user("Admin User", "admin@beyondidentity.org", "admin123", models.UserRole.admin)
    verifier = get_or_create_user(
        "Shree Education Trust NGO", "ngo@shreetrust.org", "verifier123", models.UserRole.verifier
    )
    regular_user = get_or_create_user("Demo User", "user@example.com", "user123", models.UserRole.user)

    print("Seeding listings...")
    listings_data = [
        # --- Education ---
        dict(
            category=models.ListingCategory.education,
            title="Shree Education Trust — Distance Learning Program",
            description="Affordable distance education with gender-neutral admission process. "
                        "₹1,000 registration fee, free textbooks included.",
            organization_name="Shree Education Trust",
            location="Mumbai, Maharashtra",
            contact_info="admissions@shreetrust.org",
            status=models.VerificationStatus.verified,
            verification_notes="Verified via NGO partnership, on-site visit completed.",
        ),
        dict(
            category=models.ListingCategory.education,
            title="Inclusive Bridge Course — Class 10 Equivalency",
            description="Bridge course for students who dropped out due to unsafe school environments. "
                        "Evening batches, gender-neutral facilities on campus.",
            organization_name="Nazariya Learning Center",
            location="Pune, Maharashtra",
            contact_info="info@nazariya.edu.in",
            status=models.VerificationStatus.verified,
        ),
        # --- Employment ---
        dict(
            category=models.ListingCategory.employment,
            title="Customer Support Associate",
            description="Entry-level remote role. Inclusive hiring policy, verified diversity training for managers.",
            organization_name="TechServe Solutions",
            location="Remote (India)",
            contact_info="careers@techserve.in",
            status=models.VerificationStatus.verified,
        ),
        dict(
            category=models.ListingCategory.employment,
            title="Retail Associate — Flagship Store",
            description="Full-time retail position. Employer completed community verification and sensitization training.",
            organization_name="Fabindia",
            location="Delhi",
            contact_info="hr@fabindia-careers.com",
            status=models.VerificationStatus.pending,
        ),
        # --- Housing ---
        dict(
            category=models.ListingCategory.housing,
            title="1BHK Shared Apartment — Verified Inclusive Building",
            description="Landlord verified through community feedback, no history of discriminatory rejections.",
            organization_name="Individual Landlord",
            location="Bengaluru, Karnataka",
            contact_info="housing.blr@beyondidentity.org (relay)",
            status=models.VerificationStatus.verified,
        ),
        dict(
            category=models.ListingCategory.housing,
            title="Transit Shelter — Short Term Stay",
            description="Emergency shelter for individuals facing family rejection. Up to 30-day stay, meals included.",
            organization_name="Sakhi Char Chowghi Trust",
            location="Mumbai, Maharashtra",
            contact_info="shelter@sakhichar.org",
            status=models.VerificationStatus.verified,
        ),
        # --- Healthcare ---
        dict(
            category=models.ListingCategory.healthcare,
            title="Gender-Affirming Care Clinic",
            description="Hormone therapy consultation, mental health support, staff trained in inclusive care.",
            organization_name="Humsafar Trust Clinic",
            location="Mumbai, Maharashtra",
            contact_info="clinic@humsafar.org",
            status=models.VerificationStatus.verified,
        ),
        # --- Scholarship ---
        dict(
            category=models.ListingCategory.scholarship,
            title="Transgender Welfare Scholarship 2026",
            description="Covers tuition + ₹2,000/month stipend for undergraduate students.",
            organization_name="State Social Welfare Department",
            location="Maharashtra (statewide)",
            contact_info="scholarships@maharashtra.gov.in",
            status=models.VerificationStatus.verified,
        ),
        # =========================================================================
        # REAL-WORLD GOVERNMENT SCHEMES & WELFARE PROGRAMS (MoSJE & NHA Verified)
        # =========================================================================
        dict(
            category=models.ListingCategory.scheme,
            title="SMILE — Support for Marginalized Individuals for Livelihood and Enterprise",
            description="National umbrella scheme for transgender welfare providing rehabilitation, medical care, and economic empowerment. Requires Transgender Certificate under Section 6 of the Transgender Persons Act.",
            organization_name="Ministry of Social Justice and Empowerment",
            location="Pan-India",
            contact_info="14566 / https://socialjustice.gov.in/schemes/112",
            status=models.VerificationStatus.verified,
            verification_notes="Official Central Government Umbrella Scheme under MoSJE.",
        ),
        dict(
            category=models.ListingCategory.scheme,
            title="SMILE Skill Development and Training",
            description="Market-oriented skill training for transgender persons aged 18-45 to improve employability and secure affirmative corporate roles.",
            organization_name="Ministry of Social Justice and Empowerment",
            location="Pan-India",
            contact_info="14566 / https://transgender.dosje.gov.in/skill",
            status=models.VerificationStatus.verified,
            verification_notes="Verified vocational program with monthly training stipends.",
        ),
        dict(
            category=models.ListingCategory.scheme,
            title="PM-DAKSH Yojana — Skilling Action Plan",
            description="National skilling action plan covering marginalized groups including transgender persons with short-term training, upskilling, and toolkits.",
            organization_name="Ministry of Social Justice and Empowerment",
            location="Pan-India",
            contact_info="1800-110-396 / https://pmdaksh.dosje.gov.in",
            status=models.VerificationStatus.verified,
            verification_notes="Verified national skilling action plan.",
        ),
        dict(
            category=models.ListingCategory.healthcare,
            title="AB-PMJAY Health Insurance (Transgender Welfare Scheme)",
            description="Free comprehensive health insurance coverage up to ₹5 lakh/year for transgender persons covering gender-affirming surgeries, hormone therapy, and hospitalization.",
            organization_name="National Health Authority (NHA) & Government of India",
            location="Pan-India",
            contact_info="14555 / 1800-111-565 / https://transgender.dosje.gov.in/and-pmjay",
            status=models.VerificationStatus.verified,
            verification_notes="Verified National Health Authority composite package.",
        ),
        dict(
            category=models.ListingCategory.scheme,
            title="National Council for Transgender Persons",
            description="Policy advisory council on transgender welfare, chaired by the Union Minister of Social Justice and Empowerment, monitoring rights implementation.",
            organization_name="Ministry of Social Justice and Empowerment",
            location="New Delhi / Pan-India",
            contact_info="14566 / https://socialjustice.gov.in/council",
            status=models.VerificationStatus.verified,
            verification_notes="Statutory policy advisory council under TG Persons Act 2019.",
        ),
        dict(
            category=models.ListingCategory.education,
            title="Chandigarh Fee Waiver Scheme for Transgender Students",
            description="Fee waiver for transgender students from the academic session onward across government schools and degree colleges.",
            organization_name="Department of Education, Chandigarh (UT)",
            location="Chandigarh (UT)",
            contact_info="0172-2740411 / https://chdeducation.gov.in",
            status=models.VerificationStatus.verified,
            verification_notes="Verified UT administration higher education fee-waiver scheme.",
        ),
        dict(
            category=models.ListingCategory.scheme,
            title="Himachal Pradesh Transgender Welfare Board Schemes",
            description="Pre-matric and post-matric scholarships, financial assistance to parents of transgender children under 18, and skill development schemes.",
            organization_name="Transgender Welfare Board, Himachal Pradesh",
            location="Himachal Pradesh (statewide)",
            contact_info="0177-2621151 / https://himachal.nic.in/socialjustice",
            status=models.VerificationStatus.verified,
            verification_notes="Verified state welfare board grants and scholarships.",
        ),

        # =========================================================================
        # SCHOLARSHIPS & PORTAL RESOURCES
        # =========================================================================
        dict(
            category=models.ListingCategory.scholarship,
            title="Post-Matric Scholarship for Transgender Students",
            description="Covers classes IX and above through post-graduation, including ITI, polytechnic, and UGC/AICTE-recognized degree courses with tuition and maintenance grants.",
            organization_name="Ministry of Social Justice and Empowerment",
            location="Pan-India",
            contact_info="14566 / https://transgender.dosje.gov.in/scholarships",
            status=models.VerificationStatus.verified,
            verification_notes="Verified Central Sector scholarship scheme.",
        ),
        dict(
            category=models.ListingCategory.scheme,
            title="National Portal for Transgender Persons (ID & Certificate)",
            description="Statutory digital single-window portal (transgender.dosje.gov.in) for obtaining government Transgender Certificate and Identity Card without physical inspection, and applying for scholarships/schemes.",
            organization_name="Ministry of Social Justice and Empowerment",
            location="transgender.dosje.gov.in (Online)",
            contact_info="helpdesk-tg@gov.in / 011-23386981",
            status=models.VerificationStatus.verified,
            verification_notes="Official statutory national identity issuance portal.",
        ),

        # =========================================================================
        # VERIFIED NON-GOVERNMENTAL ORGANIZATIONS (NGOs) & COMMUNITY TRUSTS
        # =========================================================================
        dict(
            category=models.ListingCategory.community,
            title="The Humsafar Trust — Community Advocacy & Health",
            description="India's first LGBTQ+ community-based organization; healthcare, legal rights advocacy, and mental wellness since 1994.",
            organization_name="The Humsafar Trust",
            location="Mumbai, Maharashtra",
            contact_info="connect@humsafar.org / +91-22-26673800",
            status=models.VerificationStatus.verified,
            verification_notes="Verified partner NGO operating primary health and legal advocacy cells.",
        ),
        dict(
            category=models.ListingCategory.community,
            title="Tweet Foundation — Transgender Shelter & Rights Desk",
            description="Runs a Garima Greh shelter home; provides legal aid, crisis support, and gender-affirming healthcare navigation.",
            organization_name="Tweet Foundation",
            location="New Delhi (shelter in Mumbai)",
            contact_info="support@tweet.org.in / +91-9810012345",
            status=models.VerificationStatus.verified,
            verification_notes="Verified partner NGO operating Garima Greh shelters.",
        ),
        dict(
            category=models.ListingCategory.employment,
            title="PeriFerry — Transgender Diversity Hiring & Upskilling",
            description="Employment-focused social enterprise; trained 320+ transgender individuals with corporate hiring pipeline partnerships.",
            organization_name="PeriFerry",
            location="Chennai, Tamil Nadu (Pan-India)",
            contact_info="connect@periferry.com / +91-44-48529900",
            status=models.VerificationStatus.verified,
            verification_notes="Verified corporate diversity hiring and skilling partner.",
        ),
        dict(
            category=models.ListingCategory.community,
            title="Born2Win Social Welfare Trust",
            description="Non-profit run by and for transgender and intersex persons providing leadership development, crisis relief, and legal rights support.",
            organization_name="Born2Win Social Welfare Trust",
            location="Chennai, Tamil Nadu",
            contact_info="born2win.trust@gmail.com / +91-9884210987",
            status=models.VerificationStatus.verified,
            verification_notes="Verified community-led welfare trust in Tamil Nadu.",
        ),
        dict(
            category=models.ListingCategory.healthcare,
            title="Naz Foundation (India) Trust — Sexual Health & Care",
            description="Works on HIV/AIDS prevention, sexual health, affirmative medical care, and mental health counseling for LGBTQ+ populations.",
            organization_name="Naz Foundation (India) Trust",
            location="New Delhi",
            contact_info="naz@nazindia.org / +91-11-26321882",
            status=models.VerificationStatus.verified,
            verification_notes="Verified public health and community counseling organization.",
        ),
        dict(
            category=models.ListingCategory.community,
            title="Sahodari Foundation — Transgender Empowerment",
            description="Pioneering transgender empowerment organization working in advocacy, crisis legal aid, education scholarships, and arts-based livelihoods.",
            organization_name="Sahodari Foundation",
            location="Tamil Nadu",
            contact_info="reach@sahodari.org / +91-9942371987",
            status=models.VerificationStatus.verified,
            verification_notes="Verified community foundation active since 2008.",
        ),
        dict(
            category=models.ListingCategory.community,
            title="Orinam — LGBTIQA+ Collective & Workplace Directory",
            description="All-volunteer LGBTIQA+ collective; maintains an audited directory of trans-inclusive employers and community referral network.",
            organization_name="Orinam",
            location="Chennai, Tamil Nadu",
            contact_info="orinam.net@gmail.com / +91-44-24987654",
            status=models.VerificationStatus.verified,
            verification_notes="Verified collective operating affirmative workplace registry.",
        ),

        # =========================================================================
        # INCLUSIVE & AFFIRMATIVE EMPLOYERS (Corporate Hiring Programs)
        # =========================================================================
        dict(
            category=models.ListingCategory.employment,
            title="Tata Steel — Transgender Affirmative Hiring Initiative",
            description="Hired 100+ transgender employees since 2021 initiative; inclusive HR policies, gender transition medical leave, and sensitization training.",
            organization_name="Tata Steel",
            location="Jamshedpur / Pan-India",
            contact_info="diversity@tatasteel.com",
            status=models.VerificationStatus.verified,
            verification_notes="Verified employer with comprehensive transition leave policies.",
        ),
        dict(
            category=models.ListingCategory.employment,
            title="Wells Fargo India — Transgender Persons Hiring Program",
            description="Transgender Persons Hiring Program in partnership with PeriFerry, sponsors 30+ individuals with professional skills training and technical roles.",
            organization_name="Wells Fargo India",
            location="Bengaluru & Hyderabad",
            contact_info="careers.india@wellsfargo.com",
            status=models.VerificationStatus.verified,
            verification_notes="Verified employer recognized for structured sponsorship pipeline.",
        ),
        dict(
            category=models.ListingCategory.employment,
            title="Accenture India — Pride at Accenture DEI Program",
            description="DEI hiring initiatives for transgender persons, medical insurance covering gender confirmation surgery, and affirmative employee networks.",
            organization_name="Accenture India",
            location="Bengaluru, Mumbai, Gurugram",
            contact_info="india.recruiting@accenture.com",
            status=models.VerificationStatus.verified,
            verification_notes="Verified equal-opportunity employer with gender affirmation healthcare.",
        ),
        dict(
            category=models.ListingCategory.employment,
            title="Infosys — Transgender Inclusion & Careers",
            description="DEI hiring initiatives for transgender persons, gender-neutral restrooms, and employee resource groups.",
            organization_name="Infosys",
            location="Bengaluru, Pune, Hyderabad",
            contact_info="diversity_careers@infosys.com",
            status=models.VerificationStatus.verified,
            verification_notes="Verified corporate equal opportunity employer.",
        ),
        dict(
            category=models.ListingCategory.employment,
            title="KPMG India — Transgender Affirmative Careers",
            description="DEI hiring initiatives for transgender persons, inclusive benefits, and partner-led sensitization training.",
            organization_name="KPMG India",
            location="Mumbai, Delhi NCR, Bengaluru",
            contact_info="dei@kpmg.com",
            status=models.VerificationStatus.verified,
            verification_notes="Verified professional services diversity employer.",
        ),
        dict(
            category=models.ListingCategory.employment,
            title="IBM India — Workplace Equality & Inclusion",
            description="Recognized in India Workplace Equality Index for transgender hiring, progressive gender-neutral parental leave, and medical transition cover.",
            organization_name="IBM India",
            location="Bengaluru, Pune, Delhi NCR",
            contact_info="careers@ibm.com",
            status=models.VerificationStatus.verified,
            verification_notes="Top-tier recognition in India Workplace Equality Index (IWEI).",
        ),
        dict(
            category=models.ListingCategory.employment,
            title="Godrej Properties — Transgender Workplace Inclusion",
            description="Grew transgender representation from 18 to 85+ employees; recognized in India Workplace Equality Index for inclusive work culture.",
            organization_name="Godrej Properties",
            location="Mumbai & Pan-India",
            contact_info="hr@godrejproperties.com",
            status=models.VerificationStatus.verified,
            verification_notes="Gold Employer recognition in India Workplace Equality Index.",
        ),
        dict(
            category=models.ListingCategory.employment,
            title="Walmart India — Diverse Talent Hiring Initiative",
            description="Recognized in India Workplace Equality Index for hiring transgender persons and inclusive supplier diversity initiatives.",
            organization_name="Walmart Global Tech India",
            location="Bengaluru & Chennai",
            contact_info="diversity@walmart.com",
            status=models.VerificationStatus.verified,
            verification_notes="Verified IWEI-recognized equal opportunity employer.",
        ),

        # =========================================================================
        # HOUSING & SHELTER HOMES
        # =========================================================================
        dict(
            category=models.ListingCategory.housing,
            title="Garima Greh Shelter Homes Network",
            description="Shelter homes for transgender persons providing food, medical care, recreational facilities, and vocational training under MoSJE (SMILE scheme).",
            organization_name="Ministry of Social Justice and Empowerment (MoSJE)",
            location="Mumbai, Delhi, and other rollout cities",
            contact_info="14566 / garimagreh-help@gov.in",
            status=models.VerificationStatus.verified,
            verification_notes="Verified national shelter home network funded under SMILE.",
        ),
        # --- One rejected + one flagged, for demo realism ---
        dict(
            category=models.ListingCategory.employment,
            title="Data Entry Operator",
            description="Listing rejected — employer could not be reached for verification after 3 attempts.",
            organization_name="Unverified Pvt Ltd",
            location="Nagpur, Maharashtra",
            status=models.VerificationStatus.rejected,
            verification_notes="Unreachable after 3 verification attempts.",
        ),
        dict(
            category=models.ListingCategory.housing,
            title="2BHK Flat for Rent",
            description="Multiple discrimination reports filed by users.",
            organization_name="Individual Landlord",
            location="Thane, Maharashtra",
            status=models.VerificationStatus.delisted,
            discrimination_reports=3,
            verification_notes="Auto-delisted after repeated discrimination reports.",
        ),
    ]

    for data in listings_data:
        exists = db.query(models.Listing).filter(models.Listing.title == data["title"]).first()
        if exists:
            continue
        listing = models.Listing(**data, submitted_by_id=regular_user.id, verified_by_id=verifier.id)
        db.add(listing)

    db.commit()

    print("Seeding sample discrimination incident reports...")
    import json
    from app.services import matcher

    sample_incidents = [
        dict(
            incident_type=models.IncidentType.workplace,
            title="Wrongful termination after gender transition disclosure",
            description="Terminated by management within one week of requesting name and pronoun update on company records. No performance issues were cited.",
            incident_date="2026-08-20",
            location_city="Pune",
            location_state="Maharashtra",
            perpetrator_details="Apex IT Solutions Pvt Ltd (HR Department)",
            urgency_level=models.UrgencyLevel.high,
            status=models.IncidentStatus.escalated_to_ngo,
            case_notes="Assigned to Nazariya QFRG legal desk for formal notice under Section 9 of TG Act 2019.",
            assigned_ngo="Nazariya: A Queer Feminist Resource Group",
            user_id=regular_user.id,
            is_anonymous=False,
            contact_email="user@example.com",
            contact_phone="+91-9876543210",
        ),
        dict(
            incident_type=models.IncidentType.healthcare_denial,
            title="Refusal of post-operative care at civil hospital",
            description="Medical staff refused admission and surgical dressing change citing lack of separate ward for transgender patients.",
            incident_date="2026-09-02",
            location_city="Lucknow",
            location_state="Uttar Pradesh",
            perpetrator_details="District Civil Hospital Casualty Department",
            urgency_level=models.UrgencyLevel.high,
            status=models.IncidentStatus.under_review,
            case_notes="Escalated to Chief Medical Officer citing Section 15 of Transgender Persons Act.",
            assigned_ngo="The Humsafar Trust",
            user_id=regular_user.id,
            is_anonymous=False,
            contact_email="user@example.com",
        ),
        dict(
            incident_type=models.IncidentType.housing_eviction,
            title="Landlord issuing 24-hour unlawful eviction notice",
            description="Landlord discovered gender identity through neighbors and demanded immediate vacation of rented apartment with forfeiture of deposit.",
            incident_date="2026-09-10",
            location_city="Bengaluru",
            location_state="Karnataka",
            perpetrator_details="Property Owner, Koramangala 4th Block",
            urgency_level=models.UrgencyLevel.immediate_sos,
            status=models.IncidentStatus.legal_aid_assigned,
            case_notes="Connected with Garima Greh shelter transit support and DLSA Bangalore free legal aid.",
            assigned_ngo="Tweet Foundation",
            user_id=None,
            is_anonymous=True,
            contact_email="anonymous.user@proton.me",
        ),
    ]

    for inc_data in sample_incidents:
        exists = db.query(models.IncidentReport).filter(models.IncidentReport.title == inc_data["title"]).first()
        if exists:
            continue

        matched_schemes = matcher.match_schemes(inc_data["incident_type"], inc_data["location_state"], inc_data["urgency_level"])
        matched_ngos = matcher.match_ngos(inc_data["incident_type"], inc_data["location_state"], inc_data["urgency_level"])

        report = models.IncidentReport(
            **inc_data,
            matched_schemes_json=json.dumps([s.dict() for s in matched_schemes]),
            matched_ngos_json=json.dumps([n.dict() for n in matched_ngos]),
        )
        db.add(report)

    db.commit()

    print(f"Done. Seeded listings, 3 sample incidents, and 3 users.")
    print("\nDemo logins:")
    print("  Admin:    admin@beyondidentity.org / admin123")
    print("  Verifier: ngo@shreetrust.org / verifier123")
    print("  User:     user@example.com / user123")


if __name__ == "__main__":
    seed()
    db.close()


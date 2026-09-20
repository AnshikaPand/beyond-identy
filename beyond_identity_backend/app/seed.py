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
        # --- Government Scheme ---
        dict(
            category=models.ListingCategory.scheme,
            title="SMILE Scheme — Support for Marginalized Individuals",
            description="Central government scheme covering shelter, healthcare, education, and skill development.",
            organization_name="Ministry of Social Justice and Empowerment",
            location="Pan-India",
            contact_info="smile-helpline@gov.in",
            status=models.VerificationStatus.verified,
        ),
        # --- Community ---
        dict(
            category=models.ListingCategory.community,
            title="Peer Mentorship Circle — Career Guidance",
            description="Monthly meetups connecting students with working professionals for mentorship.",
            organization_name="Beyond Identity Community Team",
            location="Pune, Maharashtra",
            contact_info="community@beyondidentity.org",
            status=models.VerificationStatus.verified,
        ),
        # --- Verified Indian Government Schemes & NGO Partners ---
        dict(
            category=models.ListingCategory.scheme,
            title="Ayushman Bharat PM-JAY Composite TG Package",
            description="National health insurance coverage up to ₹5 lakh per year covering gender-affirming surgeries (SRS) and medical treatments at empaneled hospitals.",
            organization_name="National Health Authority (NHA) & MoHFW",
            location="Pan-India",
            contact_info="14555 / https://transgender.dosje.gov.in/and-pmjay",
            status=models.VerificationStatus.verified,
            verification_notes="Verified official Central Government Scheme.",
        ),
        dict(
            category=models.ListingCategory.housing,
            title="Garima Greh — Safe Shelter for Transgender Youth",
            description="Secure emergency shelter with meals, medical care, counseling, and vocational training under MoSJE.",
            organization_name="Tweet Foundation & MoSJE",
            location="New Delhi & Mumbai",
            contact_info="support@tweet.org.in / +91-9810012345",
            status=models.VerificationStatus.verified,
            verification_notes="Verified Garima Greh partner facility.",
        ),
        dict(
            category=models.ListingCategory.healthcare,
            title="Humsafar Trust Comprehensive Trans Health Clinic",
            description="Endocrinology consultations, pre-HRT lab tests, mental health support, and STI screening with queer-affirmative clinicians.",
            organization_name="The Humsafar Trust",
            location="Mumbai, Maharashtra",
            contact_info="connect@humsafar.org / +91-22-26673800",
            status=models.VerificationStatus.verified,
            verification_notes="Verified NGO health facility with certified endocrinologists.",
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


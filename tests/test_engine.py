"""Unit tests for the risk scoring engine heuristics."""
from merchant_risk_scoring.models import (
    DigitalFootprint,
    DocumentSignal,
    FinancialProfile,
    MerchantApplication,
    PromoterProfile,
)
from merchant_risk_scoring.scoring.engine import RiskScoringEngine


def _base_application() -> MerchantApplication:
    return MerchantApplication(
        merchant_id="demo-123",
        business_name="Acme Retail",
        legal_name="Acme Retail Private Limited",
        registration_country="IN",
        industry_category="Retail",
        business_model="Card-present retail",
        documents=[
            DocumentSignal(document_type="GST", provided=True, verified=True),
            DocumentSignal(document_type="PAN", provided=True, verified=True),
        ],
        promoters=[
            PromoterProfile(
                full_name="Priya Singh",
                credit_score=760,
                years_of_experience=8,
                adverse_media=False,
            )
        ],
        digital_footprint=DigitalFootprint(
            website_quality="high",
            domain_age_months=36,
            social_presence="moderate",
            review_volume=120,
            average_review_rating=4.4,
            contact_email_domain_matches=True,
            ip_geolocation_match=True,
        ),
        financial_profile=FinancialProfile(
            years_in_business=5,
            average_monthly_balance=250000.0,
            projected_monthly_volume=500000.0,
            average_ticket_size=2500.0,
            bank_account_age_months=48,
            financial_documents_provided=True,
        ),
    )


def test_low_risk_application_scores_high() -> None:
    engine = RiskScoringEngine()
    result = engine.score(_base_application())

    assert result.risk_level.value == "low"
    assert result.composite_score >= 70
    assert result.decision.value == "approve"


def test_high_risk_flags_trigger_manual_review() -> None:
    engine = RiskScoringEngine()
    risky_application = _base_application().copy(update={
        "industry_category": "Crypto Exchange",
        "business_model": "Online card-not-present",
        "financial_profile": FinancialProfile(
            years_in_business=0.5,
            projected_monthly_volume=2500000,
            average_monthly_balance=100000,
            bank_account_age_months=2,
            financial_documents_provided=False,
        ),
        "digital_footprint": DigitalFootprint(
            website_quality="low",
            domain_age_months=1,
            social_presence="none",
            review_volume=0,
            contact_email_domain_matches=False,
            ip_geolocation_match=False,
        ),
    })

    result = engine.score(risky_application)

    assert result.risk_level.value in {"medium", "high"}
    assert result.decision.value in {"manual_review", "reject"}
    assert any(
        finding.rule_name == "manual_review_high_risk_industry" for finding in result.rule_findings
    )

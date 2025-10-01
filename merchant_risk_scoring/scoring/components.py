"""Component scoring logic derived from domain heuristics."""
from __future__ import annotations

from typing import List, Tuple

from merchant_risk_scoring.models import (
    ComponentScore,
    DigitalFootprint,
    DocumentSignal,
    FinancialProfile,
    MerchantApplication,
    PromoterProfile,
)
from merchant_risk_scoring.scoring.weights import RiskWeights


def _score_kyc(documents: List[DocumentSignal], weight: float) -> ComponentScore:
    score = 100.0
    reasons: List[str] = []

    if not documents:
        score = 40.0
        reasons.append("No verification documents supplied.")
    else:
        verified_docs = sum(1 for doc in documents if doc.verified)
        provided_docs = sum(1 for doc in documents if doc.provided)
        mismatches = [doc for doc in documents if doc.mismatch]
        watchlist_hits = [doc for doc in documents if doc.watchlist_hit]

        if provided_docs < len(documents):
            reasons.append("Some required documents missing from submission.")
            score -= 15

        if verified_docs < provided_docs:
            reasons.append("Not all submitted documents could be verified against registries.")
            score -= 20

        if mismatches:
            mismatch_types = ", ".join(doc.document_type for doc in mismatches)
            reasons.append(f"Data mismatch for: {mismatch_types}.")
            score -= 25

        if watchlist_hits:
            watchlist_types = ", ".join(doc.document_type for doc in watchlist_hits)
            reasons.append(f"Watchlist hits detected for {watchlist_types}.")
            score = min(score, 10)

    score = max(0.0, min(score, 100.0))
    return ComponentScore(name="Business Identity & KYC", score=score, weight=weight, reasons=reasons)


def _score_promoters(promoters: List[PromoterProfile], weight: float) -> ComponentScore:
    if not promoters:
        return ComponentScore(
            name="Promoter Risk",
            score=30.0,
            weight=weight,
            reasons=["No promoter or UBO information supplied."],
        )

    aggregate_score = 0.0
    reasons: List[str] = []

    for promoter in promoters:
        promoter_score = 80.0

        if promoter.credit_score is not None:
            if promoter.credit_score < 600:
                promoter_score -= 25
                reasons.append(
                    f"Promoter {promoter.full_name} credit score below 600 ({promoter.credit_score})."
                )
            elif promoter.credit_score < 700:
                promoter_score -= 10
        else:
            promoter_score -= 15
            reasons.append(f"No credit score data for promoter {promoter.full_name}.")

        if promoter.adverse_media:
            promoter_score -= 30
            reasons.append(f"Adverse media detected for promoter {promoter.full_name}.")

        if promoter.watchlist_hit:
            promoter_score = min(promoter_score, 5)
            reasons.append(f"Sanctions/PEP match for promoter {promoter.full_name}.")

        if promoter.previous_business_failures:
            deduction = min(20, promoter.previous_business_failures * 5)
            promoter_score -= deduction
            reasons.append(
                f"Promoter {promoter.full_name} linked to {promoter.previous_business_failures} failed businesses."
            )

        if promoter.years_of_experience is not None and promoter.years_of_experience < 1:
            promoter_score -= 10
            reasons.append(f"Promoter {promoter.full_name} has <1 year of experience in the domain.")

        aggregate_score += max(0.0, promoter_score)

    score = aggregate_score / len(promoters)
    score = max(0.0, min(score, 100.0))

    return ComponentScore(name="Promoter Risk", score=score, weight=weight, reasons=reasons)


_HIGH_RISK_INDUSTRIES = {
    "gambling",
    "adult",
    "crypto",
    "forex",
    "travel",
    "gaming",
    "nutraceuticals",
    "pharmaceuticals",
    "escort",
}

_MEDIUM_RISK_INDUSTRIES = {
    "electronics",
    "ecommerce",
    "subscription",
    "education",
    "marketplace",
    "software",
}


def _score_industry(category: str, business_model: str | None, risk_region: str | None, weight: float) -> ComponentScore:
    normalized = category.lower()
    score = 80.0
    reasons: List[str] = []

    if any(keyword in normalized for keyword in _HIGH_RISK_INDUSTRIES):
        score = 30.0
        reasons.append("Merchant operates in an inherently high-risk industry segment.")
    elif any(keyword in normalized for keyword in _MEDIUM_RISK_INDUSTRIES):
        score = 60.0
        reasons.append("Merchant operates in a moderately risky industry segment.")

    if business_model:
        model = business_model.lower()
        if "card-not-present" in model or "c-n-p" in model or "online" in model:
            score -= 10
            reasons.append("Card-not-present / online-only sales increase chargeback exposure.")
        if "subscription" in model:
            score -= 10
            reasons.append("Subscription business model has higher dispute propensity.")

    if risk_region:
        region = risk_region.lower()
        if region in {"high", "sanctioned", "enhanced"}:
            score -= 15
            reasons.append("Merchant operates in a high geopolitical / AML risk region.")

    score = max(0.0, min(score, 100.0))
    return ComponentScore(name="Industry & Category Risk", score=score, weight=weight, reasons=reasons)


def _score_financials(financial: FinancialProfile | None, weight: float) -> ComponentScore:
    if financial is None:
        return ComponentScore(
            name="Financial Stability",
            score=45.0,
            weight=weight,
            reasons=["Financial statements or projections not provided."],
        )

    score = 75.0
    reasons: List[str] = []

    if financial.years_in_business is not None:
        if financial.years_in_business < 1:
            score -= 20
            reasons.append("Business incorporated < 1 year ago.")
        elif financial.years_in_business < 3:
            score -= 10
            reasons.append("Business has limited operating history (<3 years).")
    else:
        score -= 10
        reasons.append("Years in business unknown.")

    if financial.average_monthly_balance is not None and financial.projected_monthly_volume is not None:
        buffer_ratio = financial.average_monthly_balance / max(financial.projected_monthly_volume, 1)
        if buffer_ratio < 0.1:
            score -= 20
            reasons.append("Low bank balance compared to projected processing volume (<10% buffer).")
        elif buffer_ratio < 0.25:
            score -= 10
            reasons.append("Limited liquidity relative to projected processing volume (<25% buffer).")
    elif financial.projected_monthly_volume is not None:
        score -= 5
        reasons.append("Projected volume provided without supporting bank balance data.")

    if financial.bank_account_age_months is not None and financial.bank_account_age_months < 6:
        score -= 10
        reasons.append("Settlement bank account is younger than 6 months.")

    if not financial.financial_documents_provided:
        score -= 10
        reasons.append("Financial documents could not be validated.")

    if financial.average_ticket_size and financial.average_ticket_size > 50000:
        score -= 10
        reasons.append("High average ticket size increases exposure for new merchant.")

    score = max(0.0, min(score, 100.0))
    return ComponentScore(name="Financial Stability", score=score, weight=weight, reasons=reasons)


_DIGITAL_QUALITY_SCORES = {
    "none": 10,
    "low": 40,
    "medium": 70,
    "high": 90,
}

_PRESENCE_SCORES = {
    "none": 20,
    "minimal": 45,
    "moderate": 70,
    "strong": 90,
}


def _score_digital(digital: DigitalFootprint | None, weight: float) -> ComponentScore:
    if digital is None:
        return ComponentScore(
            name="Digital Footprint",
            score=35.0,
            weight=weight,
            reasons=["No digital footprint data captured."],
        )

    score = 60.0
    reasons: List[str] = []

    if digital.website_quality:
        website_score = _DIGITAL_QUALITY_SCORES.get(digital.website_quality.lower(), 60)
        score = (score + website_score) / 2
        if website_score <= 40:
            reasons.append("Website quality appears weak or placeholder-like.")
    else:
        score -= 10
        reasons.append("Website quality not evaluated.")

    if digital.domain_age_months is not None:
        if digital.domain_age_months < 3:
            score -= 20
            reasons.append("Website domain registered within last 3 months.")
        elif digital.domain_age_months < 12:
            score -= 10
            reasons.append("Website domain younger than 1 year.")
    else:
        score -= 5
        reasons.append("Domain age unknown.")

    if digital.social_presence:
        presence_score = _PRESENCE_SCORES.get(digital.social_presence.lower(), 60)
        score = (score + presence_score) / 2
        if presence_score <= 45:
            reasons.append("Minimal or no social media / marketplace presence detected.")
    else:
        score -= 5
        reasons.append("Social presence not determined.")

    if digital.review_volume is not None and digital.review_volume < 5:
        score -= 5
        reasons.append("Limited third-party customer feedback available.")

    if digital.average_review_rating is not None and digital.average_review_rating < 3:
        score -= 10
        reasons.append("Average customer review rating below 3 stars.")

    if digital.contact_email_domain_matches is False:
        score -= 5
        reasons.append("Contact email domain does not match website domain.")

    if digital.ip_geolocation_match is False:
        score -= 10
        reasons.append("Application IP geolocation differs from declared business region.")

    score = max(0.0, min(score, 100.0))
    return ComponentScore(name="Digital Footprint", score=score, weight=weight, reasons=reasons)


def build_component_scores(application: MerchantApplication, weights: RiskWeights) -> List[ComponentScore]:
    """Calculate all configured component scores for the merchant."""

    weights.validate()

    components = [
        _score_kyc(application.documents, weights.kyc),
        _score_promoters(application.promoters, weights.promoter),
        _score_industry(
            application.industry_category,
            application.business_model,
            application.risk_region,
            weights.industry,
        ),
        _score_financials(application.financial_profile, weights.financial),
        _score_digital(application.digital_footprint, weights.digital),
    ]

    return components

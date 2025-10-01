"""Domain models and schemas for the merchant risk scoring engine."""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, conlist, confloat, validator


class RiskLevel(str, Enum):
    """Discrete risk tiers returned by the scoring engine."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Decision(str, Enum):
    """Top level recommendation from rule + score evaluation."""

    APPROVE = "approve"
    MANUAL_REVIEW = "manual_review"
    REJECT = "reject"


class DocumentSignal(BaseModel):
    """Represents verification results for a submitted document."""

    document_type: str = Field(..., description="Human readable name (e.g. GST, PAN, EIN).")
    provided: bool = Field(True, description="Whether the merchant supplied this document.")
    verified: bool = Field(
        False,
        description="True when the identifier matches the authoritative registry response.",
    )
    mismatch: bool = Field(
        False,
        description="Flag when the registry lookup returned data that does not match merchant claims.",
    )
    watchlist_hit: bool = Field(
        False,
        description="Indicates that the document identifier or associated entity appears on a watchlist.",
    )
    notes: Optional[str] = Field(None, description="Free-form details from the verification provider.")


class PromoterProfile(BaseModel):
    """Information about a promoter / owner / UBO of the merchant."""

    full_name: str
    ownership_percentage: Optional[confloat(ge=0, le=100)] = Field(
        None, description="Declared equity held by the promoter."
    )
    years_of_experience: Optional[confloat(ge=0)] = Field(
        None, description="Years of domain experience claimed by the promoter."
    )
    credit_score: Optional[confloat(ge=300, le=900)] = Field(
        None, description="Personal or business credit score when available."
    )
    adverse_media: bool = Field(
        False, description="True when negative news, litigation, or bankruptcy records were found."
    )
    watchlist_hit: bool = Field(
        False,
        description="True when the promoter matches any sanctions / PEP screening results.",
    )
    previous_business_failures: int = Field(
        0, description="Count of previously failed or blacklisted businesses linked to this promoter."
    )


class DigitalFootprint(BaseModel):
    """Signals related to the merchant's digital presence."""

    website_url: Optional[HttpUrl]
    website_quality: Optional[str] = Field(
        None,
        description="Qualitative rating from OCR or analysts (e.g. 'none', 'low', 'medium', 'high').",
    )
    domain_age_months: Optional[int] = Field(
        None, description="Months since the merchant's primary domain was registered."
    )
    social_presence: Optional[str] = Field(
        None, description="Level of social activity (none/minimal/moderate/strong)."
    )
    review_platforms: Optional[List[str]] = Field(
        None, description="List of third-party review or marketplace listings discovered."
    )
    average_review_rating: Optional[confloat(ge=0, le=5)] = Field(
        None, description="Average customer review rating when available."
    )
    review_volume: Optional[int] = Field(
        None, description="Approximate count of public reviews or ratings."
    )
    contact_email_domain_matches: Optional[bool] = Field(
        None, description="True when the contact email domain aligns with the website domain."
    )
    ip_geolocation_match: Optional[bool] = Field(
        None, description="True when the application IP is consistent with declared business geography."
    )


class FinancialProfile(BaseModel):
    """Financial stability markers supplied during underwriting."""

    years_in_business: Optional[confloat(ge=0)] = Field(
        None, description="Years since business incorporation or first operations."
    )
    paid_up_capital: Optional[float] = Field(
        None, description="Paid-up capital or funding available to the merchant (local currency)."
    )
    average_monthly_balance: Optional[float] = Field(
        None, description="Average monthly bank balance (local currency)."
    )
    projected_monthly_volume: Optional[float] = Field(
        None, description="Expected monthly processing volume with the PSP."
    )
    average_ticket_size: Optional[float] = Field(
        None, description="Average transaction value merchant expects to process."
    )
    bank_account_age_months: Optional[int] = Field(
        None, description="Age of the provided settlement bank account in months."
    )
    financial_documents_provided: Optional[bool] = Field(
        None, description="Whether bank statements or financial statements were supplied."
    )


class MerchantApplication(BaseModel):
    """Primary payload describing the merchant during onboarding."""

    merchant_id: Optional[str] = Field(None, description="Internal identifier for the merchant application.")
    business_name: str
    legal_name: Optional[str]
    registration_country: str
    business_address: Optional[str]
    industry_category: str = Field(..., description="MCC, NAICS code or descriptive industry segment.")
    business_model: Optional[str] = Field(
        None, description="Channel / business model details (e.g. ecommerce, card-present)."
    )
    risk_region: Optional[str] = Field(
        None, description="Country or region risk bucket derived from geopolitics / AML guidance."
    )
    documents: List[DocumentSignal] = Field(
        default_factory=list,
        description="Verification results for submitted KYC / KYB documents.",
    )
    promoters: conlist(PromoterProfile, min_items=1) = Field(
        ..., description="List of known owners / promoters linked to the business."
    )
    digital_footprint: Optional[DigitalFootprint]
    financial_profile: Optional[FinancialProfile]
    extra_attributes: Optional[Dict[str, str]] = Field(
        None, description="Any additional contextual information captured during onboarding."
    )

    @validator("industry_category")
    def _strip_industry(cls, value: str) -> str:
        return value.strip()


class ComponentScore(BaseModel):
    """Represents a single dimension of the risk scoring output."""

    name: str
    score: float = Field(..., ge=0, le=100)
    weight: float = Field(..., ge=0, le=1)
    reasons: List[str] = Field(default_factory=list, description="Notable drivers for this component's score.")


class RuleFinding(BaseModel):
    """Captures rule-based checks that fired for the application."""

    rule_name: str
    severity: str
    message: str


class RiskAssessmentResult(BaseModel):
    """Complete output of the scoring engine."""

    merchant_id: Optional[str]
    composite_score: float = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    decision: Decision
    component_scores: List[ComponentScore]
    rule_findings: List[RuleFinding] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

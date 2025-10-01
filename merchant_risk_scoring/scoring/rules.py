"""Rule-based gating logic for immediate red flags and manual review triggers."""
from __future__ import annotations

from typing import List

from merchant_risk_scoring.models import Decision, MerchantApplication, RuleFinding


def evaluate_rules(application: MerchantApplication) -> tuple[Decision, List[RuleFinding], List[str]]:
    """Apply deterministic rules before/after scoring to enforce policy constraints."""

    findings: List[RuleFinding] = []
    recommendations: List[str] = []
    decision = Decision.APPROVE

    # Hard fails: sanctions, watchlists, or document watchlist hits
    if any(doc.watchlist_hit for doc in application.documents):
        findings.append(
            RuleFinding(
                rule_name="sanctioned_document",
                severity="critical",
                message="At least one submitted document is linked to a sanctioned entity.",
            )
        )
        decision = Decision.REJECT
        recommendations.append("Reject application due to sanctions/watchlist hit.")

    if any(promoter.watchlist_hit for promoter in application.promoters):
        findings.append(
            RuleFinding(
                rule_name="sanctioned_promoter",
                severity="critical",
                message="Promoter flagged on sanctions/PEP watchlists.",
            )
        )
        decision = Decision.REJECT
        recommendations.append("Reject due to promoter sanctions match.")

    # High-risk industries requiring manual review even if pass other checks
    high_risk_keywords = {"gambling", "crypto", "adult", "escort", "forex"}
    normalized_industry = application.industry_category.lower()
    if any(keyword in normalized_industry for keyword in high_risk_keywords):
        findings.append(
            RuleFinding(
                rule_name="manual_review_high_risk_industry",
                severity="high",
                message="Merchant operates in a card-network high-risk vertical.",
            )
        )
        if decision != Decision.REJECT:
            decision = Decision.MANUAL_REVIEW
            recommendations.append("Manual review required for high-risk industry policies.")

    # Young business projecting large volume -> manual review
    financial = application.financial_profile
    if financial and financial.years_in_business is not None and financial.projected_monthly_volume is not None:
        if financial.years_in_business < 1 and financial.projected_monthly_volume > 1_000_000:
            findings.append(
                RuleFinding(
                    rule_name="new_business_high_volume",
                    severity="medium",
                    message="Business <1 year old with >1M projected monthly volume.",
                )
            )
            if decision == Decision.APPROVE:
                decision = Decision.MANUAL_REVIEW
                recommendations.append(
                    "Validate projected volumes and require rolling reserve for new high-volume merchant."
                )

    # Missing core documents -> manual review (unless already reject)
    if not application.documents:
        findings.append(
            RuleFinding(
                rule_name="missing_documents",
                severity="medium",
                message="No supporting documents were provided with the application.",
            )
        )
        if decision == Decision.APPROVE:
            decision = Decision.MANUAL_REVIEW
            recommendations.append("Collect KYB documents before activation.")

    return decision, findings, recommendations

"""High level orchestration for risk scoring."""
from __future__ import annotations

from typing import List

from merchant_risk_scoring.models import (
    ComponentScore,
    Decision,
    MerchantApplication,
    RiskAssessmentResult,
    RiskLevel,
)
from merchant_risk_scoring.scoring.components import build_component_scores
from merchant_risk_scoring.scoring.rules import evaluate_rules
from merchant_risk_scoring.scoring.weights import RiskWeights


def _determine_risk_level(score: float) -> RiskLevel:
    if score >= 75:
        return RiskLevel.LOW
    if score >= 45:
        return RiskLevel.MEDIUM
    return RiskLevel.HIGH


class RiskScoringEngine:
    """Coordinates rule-based and weighted scoring for underwriting decisions."""

    def __init__(self, weights: RiskWeights | None = None):
        self.weights = weights or RiskWeights()

    def score(self, application: MerchantApplication) -> RiskAssessmentResult:
        rule_decision, findings, recommendations = evaluate_rules(application)

        component_scores: List[ComponentScore] = build_component_scores(application, self.weights)
        weighted_sum = sum(component.score * component.weight for component in component_scores)

        composite_score = min(100.0, max(0.0, round(weighted_sum, 2)))
        risk_level = _determine_risk_level(composite_score)

        decision = rule_decision
        if decision == Decision.APPROVE:
            if risk_level == RiskLevel.HIGH:
                decision = Decision.MANUAL_REVIEW
                recommendations.append("High overall risk score: recommend enhanced due diligence.")
            elif risk_level == RiskLevel.MEDIUM:
                recommendations.append("Medium risk: apply rolling reserve or settlement delay during ramp-up.")
            else:
                recommendations.append("Low risk: eligible for straight-through onboarding.")

        return RiskAssessmentResult(
            merchant_id=application.merchant_id,
            composite_score=composite_score,
            risk_level=risk_level,
            decision=decision,
            component_scores=component_scores,
            rule_findings=findings,
            recommendations=recommendations,
        )

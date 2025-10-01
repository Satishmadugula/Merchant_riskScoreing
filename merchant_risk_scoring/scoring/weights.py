"""Weight configuration for the composite risk score."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskWeights:
    """Weights for each risk component (must sum to <= 1)."""

    kyc: float = 0.25
    promoter: float = 0.20
    industry: float = 0.15
    financial: float = 0.20
    digital: float = 0.10
    other: float = 0.10  # reserve bucket for future ML or behavioral signals

    def validate(self) -> None:
        total = self.kyc + self.promoter + self.industry + self.financial + self.digital + self.other
        if not 0.99 <= total <= 1.01:
            raise ValueError(f"Risk weights must sum to ~1.0, received {total:.2f}")

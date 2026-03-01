"""
Integrity Engine - computes integrity score and risk level.

Base score = 100.
Penalties: tab_switch × 10, paste × 15, ai_probability × 40, webcam_anomaly × 20.
Score cannot go below 0.
Risk: 80-100 Low, 50-79 Medium, <50 High.
"""

from typing import Any

from app.config import get_settings
from app.models.integrity_score import RiskLevel
from app.models.suspicious_event import EventType


class IntegrityEngine:
    """Calculates integrity score from event counts and AI probability."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def _penalty_weights(self) -> dict[str, int]:
        return {
            EventType.TAB_SWITCH.value: self.settings.penalty_tab_switch,
            EventType.PASTE.value: self.settings.penalty_paste,
            EventType.COPY.value: 5,
            EventType.DEVTOOLS.value: 15,
            EventType.IDLE.value: 2,
            EventType.BURST_TYPING.value: 5,
            EventType.INSTANT_LARGE_INPUT.value: 20,
            EventType.WEBCAM_ANOMALY.value: self.settings.penalty_webcam_anomaly,
        }

    def compute(
        self,
        event_counts: dict[str, int],
        ai_probability: float = 0.0,
    ) -> tuple[float, str, dict[str, Any]]:
        """
        Compute integrity score, risk level, and penalty breakdown.

        Returns:
            (score, risk_level, penalties_dict)
        """
        base = float(self.settings.integrity_base_score)
        penalties: dict[str, Any] = {}
        total_penalty = 0.0

        weights = self._penalty_weights()
        for event_type, count in event_counts.items():
            weight = weights.get(event_type, 5)
            p = count * weight
            penalties[event_type] = {"count": count, "penalty": p}
            total_penalty += p

        ai_penalty = ai_probability * self.settings.penalty_ai_probability
        penalties["ai_probability"] = {"value": ai_probability, "penalty": ai_penalty}
        total_penalty += ai_penalty

        score = max(0.0, base - total_penalty)
        risk = self._classify_risk(score)
        penalties["total"] = total_penalty
        return round(score, 2), risk, penalties

    def _classify_risk(self, score: float) -> str:
        """Classify risk: 80-100 Low, 50-79 Medium, <50 High."""
        if score >= 80:
            return RiskLevel.LOW.value
        if score >= 50:
            return RiskLevel.MEDIUM.value
        return RiskLevel.HIGH.value

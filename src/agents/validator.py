"""Validator agent - validates analyzer recommendations and enforces policies."""

from src.domain.models import (
    CampaignAnalysis,
    CampaignMetrics,
    RecommendedAction,
    ValidationResult,
)

# Confidence threshold below which human review is required
CONFIDENCE_THRESHOLD = 0.5

# Confidence threshold for conflict detection
CONFLICT_THRESHOLD = 0.3


class ValidatorAgent:
    """Agent that validates analyzer recommendations and applies policies."""

    def __init__(
        self,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
        conflict_threshold: float = CONFLICT_THRESHOLD,
    ):
        """Initialize validator agent.

        Args:
            confidence_threshold: Minimum confidence for automatic approval
            conflict_threshold: Threshold for detecting conflicts
        """
        self.confidence_threshold = confidence_threshold
        self.conflict_threshold = conflict_threshold

    def validate(
        self,
        analysis: CampaignAnalysis,
        metrics: CampaignMetrics,
    ) -> ValidationResult:
        """Validate analyzer recommendation and apply policies.

        Args:
            analysis: Analysis result from analyzer agent
            metrics: Original campaign metrics

        Returns:
            ValidationResult with final decision
        """
        # Check confidence threshold
        if analysis.confidence.overall_score < self.confidence_threshold:
            return ValidationResult(
                is_valid=True,
                requires_human_review=True,
                conflict_detected=False,
                conflict_details=f"Low confidence ({analysis.confidence.overall_score:.2f}) below threshold ({self.confidence_threshold})",
                final_recommendation=RecommendedAction.REQUIRES_HUMAN_REVIEW,
            )

        # Check for data quality issues
        if analysis.confidence.data_quality < self.conflict_threshold:
            return ValidationResult(
                is_valid=True,
                requires_human_review=True,
                conflict_detected=False,
                conflict_details=f"Poor data quality ({analysis.confidence.data_quality:.2f})",
                final_recommendation=RecommendedAction.REQUIRES_HUMAN_REVIEW,
            )

        # Check for rule conflicts between metrics and recommendation
        conflict = self._check_rule_conflicts(analysis, metrics)
        if conflict:
            return ValidationResult(
                is_valid=True,
                requires_human_review=True,
                conflict_detected=True,
                conflict_details=conflict,
                final_recommendation=RecommendedAction.REQUIRES_HUMAN_REVIEW,
            )

        # All checks passed - approve recommendation
        return ValidationResult(
            is_valid=True,
            requires_human_review=False,
            conflict_detected=False,
            final_recommendation=analysis.recommended_action,
        )

    def _check_rule_conflicts(
        self,
        analysis: CampaignAnalysis,
        metrics: CampaignMetrics,
    ) -> str | None:
        """Check for conflicts between metrics and recommendation.

        Args:
            analysis: Analysis result from analyzer
            metrics: Original campaign metrics

        Returns:
            Conflict description if conflict found, None otherwise
        """
        action = analysis.recommended_action
        cpa_trend = metrics.cpa_3d_trend
        ctr_ratio = metrics.ctr_current / max(metrics.ctr_7d_avg, 0.001)
        saturation = metrics.audience_saturation
        creative_age = metrics.creative_age_days
        conv_volume = metrics.conversion_volume_7d

        # Conflict: pause_campaign but high volume and improving CPA
        if action == RecommendedAction.PAUSE_CAMPAIGN:
            if cpa_trend < 1.0 and conv_volume > 50:
                return "Analyzer recommends pause but CPA is improving and volume is healthy"

        # Conflict: creative_refresh but fresh creative
        if action == RecommendedAction.CREATIVE_REFRESH:
            if creative_age <= 7:
                return f"Analyzer recommends creative refresh but creative is only {creative_age} days old"

        # Conflict: audience_expansion but already high saturation
        if action == RecommendedAction.AUDIENCE_EXPANSION:
            if saturation < 0.5:
                return f"Analyzer recommends audience expansion but saturation is only {saturation:.0%}"

        # Conflict: maintain but critical issues present
        if action == RecommendedAction.MAINTAIN:
            if cpa_trend > 3.0:
                return "Analyzer recommends maintain but CPA has tripled"
            if ctr_ratio < 0.3:
                return "Analyzer recommends maintain but CTR has dropped by 70%"

        # Conflict: bid_adjustment with extreme metrics
        if action == RecommendedAction.BID_ADJUSTMENT:
            if cpa_trend > 2.5:
                return "Analyzer recommends bid adjustment but CPA change is extreme"

        return None

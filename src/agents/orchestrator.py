"""Orchestration layer - coordinates analyzer and validator agents."""

from src.agents.analyzer import AnalyzerAgent
from src.agents.validator import ValidatorAgent
from src.domain.models import (
    AnalyzeResponse,
    CampaignMetrics,
    RecommendedAction,
)


class CampaignOrchestrator:
    """Orchestrates the multi-agent campaign analysis pipeline."""

    def __init__(
        self,
        analyzer: AnalyzerAgent,
        validator: ValidatorAgent | None = None,
    ):
        """Initialize orchestrator.

        Args:
            analyzer: Analyzer agent instance
            validator: Validator agent instance (optional, creates default if None)
        """
        self.analyzer = analyzer
        self.validator = validator or ValidatorAgent()

    def analyze(self, metrics: CampaignMetrics) -> AnalyzeResponse:
        """Run full analysis pipeline: analyzer -> validator.

        Args:
            metrics: Campaign metrics to analyze

        Returns:
            AnalyzeResponse with final recommendation and validation details
        """
        # Step 1: Analyzer generates recommendation
        analysis = self.analyzer.analyze(metrics)

        # Step 2: Validator checks recommendation
        validation = self.validator.validate(analysis, metrics)

        # Step 3: Build response
        if validation.requires_human_review:
            final_action = RecommendedAction.REQUIRES_HUMAN_REVIEW
            validation_notes = validation.conflict_details or "Low confidence or data quality"
        else:
            final_action = validation.final_recommendation
            validation_notes = "Passed all validation checks"

        return AnalyzeResponse(
            campaign_id=metrics.campaign_id,
            recommended_action=final_action,
            requires_human_review=validation.requires_human_review,
            reasoning=analysis.reasoning,
            confidence=analysis.confidence,
            key_factors=analysis.key_factors,
            validation_notes=validation_notes,
        )

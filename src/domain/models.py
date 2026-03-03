"""Domain models and contracts for Campaign Analyst."""

from enum import StrEnum

from pydantic import BaseModel, Field


class RecommendedAction(StrEnum):
    """Valid recommended actions for a campaign."""

    MAINTAIN = "maintain"
    PAUSE_CAMPAIGN = "pause_campaign"
    CREATIVE_REFRESH = "creative_refresh"
    AUDIENCE_EXPANSION = "audience_expansion"
    BID_ADJUSTMENT = "bid_adjustment"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"


class CampaignMetrics(BaseModel):
    """Input campaign metrics for analysis."""

    campaign_id: str = Field(..., description="Unique campaign identifier")
    cpa_3d_trend: float = Field(..., description="CPA trend over last 3 days (ratio)")
    ctr_current: float = Field(..., ge=0.0, le=1.0, description="Current click-through rate (0-1)")
    ctr_7d_avg: float = Field(..., ge=0.0, le=1.0, description="7-day average CTR (0-1)")
    audience_saturation: float = Field(..., ge=0.0, le=1.0, description="Audience saturation level (0-1)")
    creative_age_days: int = Field(..., ge=0, description="Age of current creative in days")
    conversion_volume_7d: int = Field(..., ge=0, description="Conversions in last 7 days")
    spend_7d: float = Field(..., ge=0.0, description="Total spend in last 7 days")


class AnalysisConfidence(BaseModel):
    """Confidence scoring for the analysis."""

    overall_score: float = Field(..., ge=0.0, le=1.0)
    data_quality: float = Field(..., ge=0.0, le=1.0)
    recommendation_strength: float = Field(..., ge=0.0, le=1.0)


class CampaignAnalysis(BaseModel):
    """Output from the analyzer agent."""

    campaign_id: str
    recommended_action: RecommendedAction
    reasoning: str = Field(..., max_length=500)
    confidence: AnalysisConfidence
    key_factors: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """Output from the validator agent."""

    is_valid: bool
    requires_human_review: bool
    conflict_detected: bool = False
    conflict_details: str | None = None
    final_recommendation: RecommendedAction


class AnalyzeRequest(BaseModel):
    """API request body for /analyze endpoint."""

    campaign_metrics: CampaignMetrics


class AnalyzeResponse(BaseModel):
    """API response from /analyze endpoint."""

    campaign_id: str
    recommended_action: RecommendedAction
    requires_human_review: bool
    reasoning: str
    confidence: AnalysisConfidence
    key_factors: list[str]
    validation_notes: str | None = None

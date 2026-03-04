"""FastAPI application for Campaign Analyst API.

Provides REST endpoints for campaign analysis with multi-agent orchestration.
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.agents import Orchestrator
from src.domain.models import CampaignAnalysis, CampaignMetrics, RecommendedAction


# Global orchestrator instance
orchestrator: Orchestrator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global orchestrator
    # Startup: Initialize orchestrator
    orchestrator = Orchestrator()
    yield
    # Shutdown: Cleanup (if needed)
    orchestrator = None


app = FastAPI(
    title="Campaign Analyst API",
    description="Multi-agent campaign analysis with LLM-powered recommendations",
    version="0.2.0",
    lifespan=lifespan,
)


# Request/Response models
class AnalyzeRequest(BaseModel):
    """Request to analyze a campaign."""

    campaign_id: str = Field(..., description="Unique campaign identifier")
    cpa_3d_trend: float = Field(..., ge=0, description="3-day CPA trend multiplier")
    ctr_current: float = Field(..., ge=0, le=1, description="Current CTR")
    ctr_7d_avg: float = Field(..., ge=0, le=1, description="7-day average CTR")
    audience_saturation: float = Field(..., ge=0, le=1, description="Audience saturation")
    creative_age_days: int = Field(..., ge=0, description="Creative age in days")
    conversion_volume_7d: int = Field(..., ge=0, description="7-day conversion volume")
    spend_7d: float = Field(..., ge=0, description="7-day spend in USD")

    class Config:
        json_schema_extra = {
            "example": {
                "campaign_id": "camp_001",
                "cpa_3d_trend": 2.5,
                "ctr_current": 0.02,
                "ctr_7d_avg": 0.04,
                "audience_saturation": 0.8,
                "creative_age_days": 21,
                "conversion_volume_7d": 50,
                "spend_7d": 5000.0,
            }
        }


class AnalyzeResponse(BaseModel):
    """Response from campaign analysis."""

    campaign_id: str
    recommended_action: str
    reasoning: str
    confidence: dict[str, float]
    key_factors: list[str]
    validation: dict[str, Any] | None
    _metadata: dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    models: dict[str, str]


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for Cloud Run."""
    from src.providers import get_default_analyzer_model, get_default_validator_model

    return HealthResponse(
        status="healthy",
        version="0.2.0",
        models={
            "analyzer": get_default_analyzer_model(),
            "validator": get_default_validator_model(),
        },
    )


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Campaign Analyst API",
        "version": "0.2.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_campaign(request: AnalyzeRequest):
    """Analyze a campaign and return recommendations.

    This endpoint uses a multi-agent system:
    1. Analyzer Agent (LLM) generates recommendations
    2. Validator Agent (LLM) validates the analysis
    3. Full traceability via session persistence
    """
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        # Convert request to domain model
        metrics = CampaignMetrics(
            campaign_id=request.campaign_id,
            cpa_3d_trend=request.cpa_3d_trend,
            ctr_current=request.ctr_current,
            ctr_7d_avg=request.ctr_7d_avg,
            audience_saturation=request.audience_saturation,
            creative_age_days=request.creative_age_days,
            conversion_volume_7d=request.conversion_volume_7d,
            spend_7d=request.spend_7d,
        )

        # Run analysis
        response = orchestrator.analyze(
            metrics=metrics,
            enable_validation=True,
            enable_thinking=False,
        )

        return response.to_dict()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/models")
async def list_models():
    """List available models and providers."""
    from src.providers import MODEL_REGISTRY
    from src.providers import get_default_analyzer_model, get_default_validator_model

    return {
        "available_models": {
            model: {"provider": provider}
            for model, (provider, _) in MODEL_REGISTRY.items()
        },
        "defaults": {
            "analyzer": get_default_analyzer_model(),
            "validator": get_default_validator_model(),
        },
    }


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session history by ID."""
    if orchestrator is None or orchestrator.session_manager is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    session = orchestrator.session_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.id,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "message_count": len(session.messages),
        "messages": [
            {
                "role": msg.role,
                "content": msg.to_text() if hasattr(msg, "to_text") else str(msg.content),
                "timestamp": msg.timestamp,
            }
            for msg in session.messages
        ],
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )

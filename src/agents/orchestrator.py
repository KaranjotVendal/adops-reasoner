"""Orchestrator for multi-step agent workflow.

Coordinates Analyzer → Validator → Tools → Response flow.
"""

import logging
import time
import uuid
from typing import Any

from src.agents.analyzer import AnalyzerAgent
from src.agents.validator import ValidationResult, ValidatorAgent
from src.domain.models import CampaignAnalysis, CampaignMetrics
from src.providers import AnthropicStyleProvider, get_provider
from src.schema import LLMResponse, Message, TextContent
from src.session import SessionManager
from src.tools import ReadFileTool, ToolRegistry, WriteFileTool

logger = logging.getLogger(__name__)


class AnalysisResponse:
    """Complete analysis response with metadata."""

    def __init__(
        self,
        campaign_id: str,
        analysis: CampaignAnalysis,
        validation: ValidationResult | None,
        metadata: dict[str, Any],
    ):
        self.campaign_id = campaign_id
        self.analysis = analysis
        self.validation = validation
        self.metadata = metadata

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        result = {
            "campaign_id": self.campaign_id,
            "recommended_action": self.analysis.recommended_action.value,
            "reasoning": self.analysis.reasoning,
            "confidence": {
                "overall_score": self.analysis.confidence.overall_score,
                "data_quality": self.analysis.confidence.data_quality,
                "recommendation_strength": self.analysis.confidence.recommendation_strength,
            },
            "key_factors": self.analysis.key_factors,
            "validation": self.validation.to_dict() if self.validation else None,
            "_metadata": self.metadata,
        }
        return result


class Orchestrator:
    """Orchestrates multi-step campaign analysis workflow.

    Flow:
    1. Analyzer generates recommendation
    2. Validator reviews and approves/rejects
    3. (Optional) Tools for additional info
    4. Return final response with full metadata
    """

    def __init__(
        self,
        session_manager: SessionManager | None = None,
        tool_registry: ToolRegistry | None = None,
        analyzer_model: str | None = None,
        validator_model: str | None = None,
    ):
        """Initialize orchestrator.

        Args:
            session_manager: Optional session manager for persistence
            tool_registry: Optional tools for agents
            analyzer_model: Model ID for analyzer (default from env)
            validator_model: Model ID for validator (default from env)
        """
        self.session_manager = session_manager or SessionManager()
        self.tool_registry = tool_registry or self._create_default_tools()

        # Get models from env or defaults
        from src.providers import get_default_analyzer_model, get_default_validator_model
        self.analyzer_model = analyzer_model or get_default_analyzer_model()
        self.validator_model = validator_model or get_default_validator_model()

    def _create_default_tools(self) -> ToolRegistry:
        """Create default tool registry with read/write tools."""
        return ToolRegistry().register_all([
            ReadFileTool(),
            WriteFileTool(),
        ])

    def analyze(
        self,
        metrics: CampaignMetrics,
        session_id: str | None = None,
        enable_validation: bool = True,
        enable_thinking: bool = False,
    ) -> AnalysisResponse:
        """Run full analysis workflow.

        Args:
            metrics: Campaign metrics to analyze
            session_id: Optional existing session ID
            enable_validation: Whether to run validator
            enable_thinking: Whether to capture model thinking

        Returns:
            AnalysisResponse with full results and metadata
        """
        trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        start_time = time.time()

        # Get or create session
        if session_id:
            session = self.session_manager.get(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found, creating new")
                session = self._create_session()
        else:
            session = self._create_session()

        # Create analyzer
        analyzer_provider = get_provider(self.analyzer_model)
        analyzer = AnalyzerAgent(
            provider=analyzer_provider,
            enable_thinking=enable_thinking,
        )

        # Step 1: Analyze
        logger.info(f"[{trace_id}] Starting analysis with {self.analyzer_model}")
        analysis = analyzer.analyze(metrics, tools=self.tool_registry.get_schemas())

        # Record analyzer metrics
        analyzer_metadata = getattr(analysis, "_metadata", {}) or {}

        # Add to session
        self.session_manager.add_message(
            session.id,
            Message.user(f"Analyze campaign: {metrics.campaign_id}"),
        )
        self.session_manager.add_message(
            session.id,
            Message.assistant([
                TextContent(text=f"Action: {analysis.recommended_action.value}"),
                TextContent(text=f"Reasoning: {analysis.reasoning}"),
            ]),
        )

        # Step 2: Validate (if enabled)
        validation: ValidationResult | None = None
        validator_metadata = {}

        if enable_validation:
            logger.info(f"[{trace_id}] Starting validation with {self.validator_model}")
            validator_provider = get_provider(self.validator_model)
            validator = ValidatorAgent(
                provider=validator_provider,
                tool_registry=self.tool_registry,
            )

            validation = validator.validate(
                campaign_id=metrics.campaign_id,
                analysis_result={
                    "recommended_action": analysis.recommended_action.value,
                    "reasoning": analysis.reasoning,
                    "confidence": analysis.confidence.model_dump(),
                    "key_factors": analysis.key_factors,
                },
                original_metrics=metrics.model_dump(),
            )

            # Record validator metrics
            if validation.llm_response:
                validator_metadata = {
                    "model": validation.llm_response.model,
                    "provider": validation.llm_response.provider,
                    "latency_ms": validation.llm_response.latency_ms,
                    "tokens": validation.llm_response.usage.model_dump() if validation.llm_response.usage else None,
                    "cost": validation.llm_response.cost.model_dump() if validation.llm_response.cost else None,
                }

            # Add validation to session
            self.session_manager.add_message(
                session.id,
                Message.user(f"Validation: {validation.decision}"),
            )

        # Build response
        total_latency = (time.time() - start_time) * 1000
        total_cost = (
            (analyzer_metadata.get("cost", {}) or {}).get("total_cost", 0)
            + (validator_metadata.get("cost") or {}).get("total_cost", 0)
        )

        metadata = {
            "session_id": session.id,
            "trace_id": trace_id,
            "analyzer": {
                "model": analyzer_metadata.get("model", self.analyzer_model),
                "provider": analyzer_metadata.get("provider", "unknown"),
                "latency_ms": analyzer_metadata.get("latency_ms", 0),
                "tokens": analyzer_metadata.get("usage"),
                "cost": analyzer_metadata.get("cost"),
                "thinking": analyzer_metadata.get("thinking"),
            },
            "validator": validator_metadata if enable_validation else None,
            "total_latency_ms": round(total_latency, 2),
            "estimated_cost_usd": round(total_cost, 6),
        }

        return AnalysisResponse(
            campaign_id=metrics.campaign_id,
            analysis=analysis,
            validation=validation,
            metadata=metadata,
        )

    def _create_session(self):
        """Create new session with analyzer system prompt."""
        from src.agents import DEFAULT_ANALYZER_SYSTEM_PROMPT
        return self.session_manager.create(
            system_prompt=DEFAULT_ANALYZER_SYSTEM_PROMPT,
            metadata={"type": "campaign_analysis"},
        )

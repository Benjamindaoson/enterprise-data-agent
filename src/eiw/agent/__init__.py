"""Enterprise Data Agent - Agent Runtime Package.

This package provides the P0-D agent runtime with:
- Model Provider abstraction
- Intent Resolution
- Analysis Planning
- Supervisor Runtime
- Durable State Management
- Tool Registry
- RBAC/Governance
"""

from eiw.agent.provider import (
    ModelProvider,
    DeterministicProvider,
    AnthropicProvider,
    ProviderConfig,
    ProviderType,
    create_provider,
    get_default_provider,
)

from eiw.agent.intent import (
    IntentResolver,
    ResolvedBusinessIntent,
    AnalysisType,
    AmbiguityType,
    ClarificationQuestion,
    IntentResolutionResult,
    create_intent_resolver,
)

from eiw.agent.planner import (
    AnalysisPlanner,
    AnalysisPlan,
    AnalysisStep,
    StepStatus,
    ToolType,
    create_analysis_planner,
)

from eiw.agent.supervisor import (
    Supervisor,
    SupervisorDecision,
    AnalysisTask,
    TaskStatus,
    Hypothesis,
    HypothesisStatus,
    Observation,
    Claim,
    create_supervisor,
)

from eiw.agent.state import (
    DurableStateManager,
    StateStorageType,
    Checkpoint,
    TaskStateBuilder,
    create_state_manager,
)

from eiw.agent.tools import (
    ToolRegistry,
    ToolCategory,
    ToolSignature,
    ToolExecutionContext,
    ToolResult,
    create_tool_registry,
)

from eiw.agent.governance import (
    Role,
    Permission,
    User,
    Session,
    AccessControl,
    AuditEventType,
    create_demo_personas,
    create_demo_session,
    create_governance_config,
    GovernanceConfig,
)

from eiw.agent.runtime import (
    AgentRuntime,
    AgentResult,
    AnalysisStatus,
    create_agent_runtime,
)

__version__ = "2.0.0"

__all__ = [
    # Provider
    "ModelProvider",
    "DeterministicProvider",
    "AnthropicProvider",
    "ProviderConfig",
    "ProviderType",
    "create_provider",
    "get_default_provider",
    # Intent
    "IntentResolver",
    "ResolvedBusinessIntent",
    "AnalysisType",
    "AmbiguityType",
    "ClarificationQuestion",
    "IntentResolutionResult",
    "create_intent_resolver",
    # Planner
    "AnalysisPlanner",
    "AnalysisPlan",
    "AnalysisStep",
    "StepStatus",
    "ToolType",
    "create_analysis_planner",
    # Supervisor
    "Supervisor",
    "SupervisorDecision",
    "AnalysisTask",
    "TaskStatus",
    "Hypothesis",
    "HypothesisStatus",
    "Observation",
    "Claim",
    "create_supervisor",
    # State
    "DurableStateManager",
    "StateStorageType",
    "Checkpoint",
    "TaskStateBuilder",
    "create_state_manager",
    # Tools
    "ToolRegistry",
    "ToolCategory",
    "ToolSignature",
    "ToolExecutionContext",
    "ToolResult",
    "create_tool_registry",
    # Governance
    "Role",
    "Permission",
    "User",
    "Session",
    "AccessControl",
    "AuditEventType",
    "create_demo_personas",
    "create_demo_session",
    "create_governance_config",
    "GovernanceConfig",
    # Runtime
    "AgentRuntime",
    "AgentResult",
    "AnalysisStatus",
    "create_agent_runtime",
]

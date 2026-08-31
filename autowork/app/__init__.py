# Copyright 2026 AutoWork Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""AutoWork — Autonomous Goal-to-Action Agent (Phases 1, 2, 3, & 4)."""

import os

from dotenv import load_dotenv

# Load local environment variables before module imports
load_dotenv()

# Graceful Google Cloud ADC discovery
try:
    import google.auth
    import google.auth.exceptions

    try:
        _, project_id = google.auth.default()
        if project_id:
            os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
    except (google.auth.exceptions.DefaultCredentialsError, Exception):
        pass
except ImportError:
    pass

os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")

from .agent import app, root_agent  # noqa: E402
from .approval_service import (  # noqa: E402
    ApprovalError,
    ApprovalService,
    InvalidStateTransitionError,
    PlanNotFoundError,
    PlanValidationError,
    approval_service,
)
from .cloud import (  # noqa: E402
    CloudConfig,
    ExecutionDispatcher,
    ExecutionRepository,
    ExecutionWorker,
    FirestoreExecutionRepository,
    InMemoryExecutionRepository,
    LocalAsyncDispatcher,
    PubSubDispatcher,
    cloud_config,
    default_dispatcher,
    default_execution_repository,
    default_worker,
    worker_app,
)
from .config import config  # noqa: E402
from .execution_manager import (  # noqa: E402
    ExecutionAuthorizationError,
    ExecutionManager,
    execution_manager,
)
from .models import (  # noqa: E402
    ActionableResult,
    ActionLevel,
    ActionPlan,
    ApprovalStatus,
    ApprovalSummary,
    CriticDecision,
    CriticEvaluation,
    Evidence,
    ExecutionAuthorization,
    ExecutionState,
    ExecutionStatus,
    GoalAnalysis,
    PlanApproval,
    PlanStatus,
    PlanTask,
    Priority,
    TaskType,
    VerificationResult,
)
from .planner import (  # noqa: E402
    autowork_sequential_pipeline,
    create_autowork_pipeline,
    create_goal_analyzer_agent,
    create_plan_generator_agent,
    goal_analyzer_agent,
    plan_generator_agent,
)
from .repository import (  # noqa: E402
    InMemoryPlanRepository,
    PlanRepository,
    default_repository,
)
from .research import EvidenceStore, ResearchEngine  # noqa: E402
from .server import api_app  # noqa: E402
from .specialists import (  # noqa: E402
    AnalysisAgent,
    CriticAgent,
    FinalizerAgent,
    VerificationAgent,
)
from .utils import (  # noqa: E402
    export_plan_json,
    format_plan_markdown,
    validate_plan_graph,
)

__all__ = [
    "ActionLevel",
    "ActionPlan",
    "ActionableResult",
    "AnalysisAgent",
    "ApprovalError",
    "ApprovalService",
    "ApprovalStatus",
    "ApprovalSummary",
    "CloudConfig",
    "CriticAgent",
    "CriticDecision",
    "CriticEvaluation",
    "Evidence",
    "EvidenceStore",
    "ExecutionAuthorization",
    "ExecutionAuthorizationError",
    "ExecutionDispatcher",
    "ExecutionManager",
    "ExecutionRepository",
    "ExecutionState",
    "ExecutionStatus",
    "ExecutionWorker",
    "FinalizerAgent",
    "FirestoreExecutionRepository",
    "GoalAnalysis",
    "InMemoryExecutionRepository",
    "InMemoryPlanRepository",
    "InvalidStateTransitionError",
    "LocalAsyncDispatcher",
    "PlanApproval",
    "PlanNotFoundError",
    "PlanRepository",
    "PlanStatus",
    "PlanTask",
    "PlanValidationError",
    "Priority",
    "PubSubDispatcher",
    "ResearchEngine",
    "TaskType",
    "VerificationAgent",
    "VerificationResult",
    "api_app",
    "app",
    "approval_service",
    "autowork_sequential_pipeline",
    "cloud_config",
    "config",
    "create_autowork_pipeline",
    "create_goal_analyzer_agent",
    "create_plan_generator_agent",
    "default_dispatcher",
    "default_execution_repository",
    "default_repository",
    "default_worker",
    "execution_manager",
    "export_plan_json",
    "format_plan_markdown",
    "goal_analyzer_agent",
    "plan_generator_agent",
    "root_agent",
    "validate_plan_graph",
    "worker_app",
]

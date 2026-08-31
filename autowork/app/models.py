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

"""Pydantic data models and schemas for AutoWork (Phases 1, 2, & 3)."""

from __future__ import annotations

import datetime
import uuid
from enum import Enum

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Controlled vocabulary for task classifications."""

    RESEARCH = "RESEARCH"
    ANALYSIS = "ANALYSIS"
    TRANSFORM = "TRANSFORM"
    GENERATE = "GENERATE"
    VERIFY = "VERIFY"
    DECISION = "DECISION"
    ACTION = "ACTION"


class Priority(str, Enum):
    """Priority levels for decomposed plan tasks."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionLevel(str, Enum):
    """Safety taxonomy and external impact classification for tasks."""

    READ = "READ"
    ANALYZE = "ANALYZE"
    GENERATE = "GENERATE"
    WRITE = "WRITE"
    EXTERNAL_ACTION = "EXTERNAL_ACTION"
    DESTRUCTIVE = "DESTRUCTIVE"


class PlanStatus(str, Enum):
    """Lifecycle state machine for ActionPlan execution authorization."""

    PLANNING = "planning"
    PLAN_READY = "plan_ready"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    EXECUTION_AUTHORIZED = "execution_authorized"


class ApprovalStatus(str, Enum):
    """Status of human review decision."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"


class ExecutionStatus(str, Enum):
    """Execution state machine status for autonomous runtime."""

    AUTHORIZED = "authorized"
    QUEUED = "queued"
    RUNNING = "running"
    RESEARCHING = "researching"
    ANALYZING = "analyzing"
    CRITIQUING = "critiquing"
    REFINING = "refining"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    COMPLETED_WITH_LIMITATIONS = "completed_with_limitations"
    FAILED = "failed"
    HALTED = "halted"


class CriticDecision(str, Enum):
    """Structured quality decision from Critic Agent."""

    READY = "READY"
    NEEDS_REFINEMENT = "NEEDS_REFINEMENT"
    HALT = "HALT"


# -----------------------------------------------------------------------------
# Phase 1 & 2 Planning & Approval Models
# -----------------------------------------------------------------------------


class GoalAnalysis(BaseModel):
    """Structured understanding of a natural-language user goal."""

    objective: str = Field(
        description="The primary objective the user wants to accomplish."
    )
    desired_outcome: str = Field(
        description="What concrete artifact or state should exist upon successful completion."
    )
    context: str | None = Field(
        default=None,
        description="Relevant background information, domain specifics, or user persona.",
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Explicit or implicit constraints (budget, deadlines, tech stack, format, limitations).",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Explicit assumptions made by the analyzer to resolve ambiguity.",
    )
    success_criteria: list[str] = Field(
        default_factory=list,
        description="Measurable conditions determining that the goal was successfully achieved.",
    )
    required_capabilities: list[str] = Field(
        default_factory=list,
        description="Required capabilities/tools needed downstream (e.g., web_search, code_execution, data_analysis).",
    )


class PlanTask(BaseModel):
    """An atomic, actionable step in the decomposed action plan."""

    id: str = Field(
        description="Unique identifier for the task, formatted sequentially like 'task_001', 'task_002'."
    )
    title: str = Field(
        description="Action-oriented concise title starting with an imperative verb."
    )
    description: str = Field(
        description="Detailed execution instructions for downstream specialist agents."
    )
    task_type: TaskType = Field(
        description="Controlled category of the task (RESEARCH, ANALYSIS, TRANSFORM, GENERATE, VERIFY, DECISION, ACTION)."
    )
    priority: Priority = Field(
        default=Priority.MEDIUM,
        description="Priority level for task execution ordering and resource allocation.",
    )
    action_level: ActionLevel = Field(
        default=ActionLevel.READ,
        description="Safety and side-effect tier (READ, ANALYZE, GENERATE, WRITE, EXTERNAL_ACTION, DESTRUCTIVE).",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of task IDs that must complete successfully before this task can start.",
    )
    required_capabilities: list[str] = Field(
        default_factory=list,
        description="List of capability tags required to execute this specific task.",
    )
    expected_output: str = Field(
        description="Clear description of the observable output or artifact produced by this task."
    )
    success_criteria: list[str] = Field(
        default_factory=list,
        description="Measurable verification criteria to validate this task's output before continuing.",
    )
    is_consequential: bool = Field(
        default=False,
        description="Flag indicating if the task has external side effects or requires human review in Phase 2.",
    )
    estimated_effort: str = Field(
        default="MEDIUM",
        description="Estimated effort/complexity: LOW, MEDIUM, or HIGH.",
    )


class PlanApproval(BaseModel):
    """Record of human approval, rejection, or modification of an ActionPlan."""

    approval_id: str = Field(
        default_factory=lambda: f"appr-{uuid.uuid4().hex[:8]}",
        description="Unique approval record identifier.",
    )
    plan_id: str = Field(description="Referenced ActionPlan ID.")
    plan_version: int = Field(
        default=1, description="Version of the plan reviewed."
    )
    status: ApprovalStatus = Field(
        default=ApprovalStatus.PENDING,
        description="Decision status: pending, approved, rejected, modified.",
    )
    approved_by: str | None = Field(
        default=None, description="User or authority who reviewed the plan."
    )
    decided_at: str | None = Field(
        default=None, description="ISO timestamp of review decision."
    )
    rejection_reason: str | None = Field(
        default=None, description="Detailed explanation if plan was rejected."
    )
    modifications: list[str] = Field(
        default_factory=list,
        description="List of requested user modifications if status is modified.",
    )


class ExecutionAuthorization(BaseModel):
    """Formal authorization ticket allowing Phase 3 autonomous runtime execution."""

    authorization_id: str = Field(
        default_factory=lambda: f"auth-{uuid.uuid4().hex[:8]}",
        description="Unique authorization token ID.",
    )
    event: str = Field(
        default="EXECUTION_AUTHORIZED",
        description="Event type name for downstream execution engines.",
    )
    plan_id: str = Field(description="Authorized ActionPlan ID.")
    plan_version: int = Field(default=1, description="Authorized plan version.")
    authorized_by: str = Field(description="Identity of the authorizing user.")
    authorized_at: str = Field(
        default_factory=lambda: datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        description="ISO timestamp of authorization.",
    )
    approved_task_ids: list[str] = Field(
        default_factory=list,
        description="List of task IDs authorized for autonomous execution.",
    )
    consequential_task_ids: list[str] = Field(
        default_factory=list,
        description="Identified side-effect task IDs authorized with explicit consent.",
    )
    is_active: bool = Field(
        default=True,
        description="Whether this authorization is active and unrevoked.",
    )


class ActionPlan(BaseModel):
    """Comprehensive, machine-readable structured action plan generated for a goal."""

    plan_id: str = Field(
        default_factory=lambda: f"plan-{uuid.uuid4().hex[:8]}",
        description="Unique identifier for this action plan.",
    )
    version: int = Field(
        default=1,
        description="Plan revision integer version (v1, v2, ...).",
    )
    status: PlanStatus = Field(
        default=PlanStatus.AWAITING_APPROVAL,
        description="Current lifecycle status of the plan.",
    )
    goal: str = Field(
        description="The original natural-language goal supplied by the user."
    )
    objective: str = Field(
        description="High-level refined objective statement."
    )
    summary: str = Field(
        description="Executive summary of the execution strategy and decomposition approach."
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Assumptions made when formulating the plan.",
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Constraints that the execution must strictly adhere to.",
    )
    tasks: list[PlanTask] = Field(
        default_factory=list,
        description="Ordered list of atomic tasks forming the dependency graph.",
    )
    final_deliverable: str = Field(
        description="Description of the final consolidated deliverable to be presented to the user."
    )
    success_criteria: list[str] = Field(
        default_factory=list,
        description="Global success criteria for the overall plan.",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        description="UTC timestamp of plan creation.",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        description="UTC timestamp of latest plan modification.",
    )
    approval: PlanApproval | None = Field(
        default=None,
        description="Latest approval/rejection record if reviewed.",
    )
    schema_version: str = Field(
        default="1.0.0",
        description="Schema specification version for backwards compatibility.",
    )


class ApprovalSummary(BaseModel):
    """Executive Human-in-the-Loop review dossier presented for approval."""

    plan_id: str
    version: int
    status: PlanStatus
    goal: str
    objective: str
    summary: str
    total_tasks: int
    consequential_tasks: list[PlanTask]
    required_capabilities: list[str]
    final_deliverable: str
    assumptions: list[str]
    constraints: list[str]
    success_criteria: list[str]
    is_approvable: bool
    validation_errors: list[str] = Field(default_factory=list)


# -----------------------------------------------------------------------------
# Phase 3 Autonomous Intelligence Models
# -----------------------------------------------------------------------------


class Evidence(BaseModel):
    """Grounded evidence collected during autonomous research."""

    id: str = Field(
        default_factory=lambda: f"ev-{uuid.uuid4().hex[:6]}",
        description="Unique evidence item identifier.",
    )
    claim: str = Field(description="Concrete verified claim or fact.")
    source_title: str = Field(description="Title of the source publication.")
    source_url: str = Field(description="URL of the retrieved source document.")
    source_type: str = Field(
        default="web_document",
        description="Category of source: web_document, official_docs, pricing_sheet, benchmark.",
    )
    excerpt: str | None = Field(
        default=None, description="Direct supporting quote or snippet."
    )
    relevance_score: float = Field(
        default=0.9,
        description="Relevance confidence score between 0.0 and 1.0.",
    )
    task_id: str | None = Field(
        default=None,
        description="Associated task ID that collected this evidence.",
    )
    collected_at: str = Field(
        default_factory=lambda: datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        description="ISO timestamp when evidence was collected.",
    )


class CriticEvaluation(BaseModel):
    """Quality and completeness evaluation produced by Critic Agent."""

    status: str = Field(
        default="evaluated", description="Status of the evaluation."
    )
    decision: CriticDecision = Field(
        description="Critic decision: READY (sufficient evidence), NEEDS_REFINEMENT (gaps found), or HALT."
    )
    quality_score: float = Field(
        description="Overall evidence quality score (0.0 to 100.0)."
    )
    confidence: float = Field(
        description="Confidence score in the collected evidence (0.0 to 1.0)."
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="Well-supported claims and strong areas.",
    )
    weaknesses: list[str] = Field(
        default_factory=list, description="Weak or partially supported claims."
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Specific information gaps to investigate.",
    )
    contradictions: list[str] = Field(
        default_factory=list, description="Detected source discrepancies."
    )
    follow_up_queries: list[str] = Field(
        default_factory=list,
        description="Targeted follow-up search queries to resolve missing information.",
    )
    reason: str = Field(
        default="", description="Executive justification for the decision."
    )


class VerificationResult(BaseModel):
    """Rigorous verification check performed prior to final answer synthesis."""

    status: str = Field(default="verified", description="Verification status.")
    is_verified: bool = Field(
        default=True,
        description="Whether the evidence base meets the verification threshold.",
    )
    coverage_score: float = Field(
        default=0.9, description="Goal objective coverage score (0.0 to 1.0)."
    )
    evidence_score: float = Field(
        default=0.9, description="Claim grounding score (0.0 to 1.0)."
    )
    confidence: float = Field(
        default=0.9, description="Overall verified confidence."
    )
    unsupported_claims: list[str] = Field(
        default_factory=list, description="Claims lacking sufficient evidence."
    )
    limitations: list[str] = Field(
        default_factory=list, description="Known uncertainties and limitations."
    )


class ActionableResult(BaseModel):
    """The final verified, evidence-grounded deliverable produced by AutoWork."""

    execution_id: str = Field(
        description="Unique identifier for the execution run."
    )
    plan_id: str = Field(description="Referenced ActionPlan ID.")
    status: ExecutionStatus = Field(
        default=ExecutionStatus.COMPLETED,
        description="Final execution status: completed, completed_with_limitations, failed.",
    )
    executive_summary: str = Field(
        description="Concise, high-impact executive summary answering the user goal."
    )
    key_findings: list[str] = Field(
        default_factory=list,
        description="Key findings and factual discoveries supported by evidence.",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Direct, actionable recommendations answering user criteria.",
    )
    next_actions: list[str] = Field(
        default_factory=list,
        description="Concrete, practical next steps the user should take.",
    )
    evidence: list[Evidence] = Field(
        default_factory=list,
        description="Traceable citations and evidence items supporting findings.",
    )
    confidence_score: float = Field(
        default=0.9, description="Overall confidence score (0.0 to 1.0)."
    )
    limitations: list[str] = Field(
        default_factory=list,
        description="Explicitly disclosed uncertainties and limitations.",
    )
    completed_tasks: list[str] = Field(
        default_factory=list,
        description="List of successfully completed task IDs.",
    )
    failed_tasks: list[str] = Field(
        default_factory=list, description="List of failed or skipped task IDs."
    )
    iterations_used: int = Field(
        default=1, description="Number of refinement iterations executed."
    )
    completed_at: str = Field(
        default_factory=lambda: datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        description="ISO timestamp of completion.",
    )


class ExecutionState(BaseModel):
    """Live tracking state of an active or completed autonomous execution run."""

    execution_id: str = Field(
        default_factory=lambda: f"exec-{uuid.uuid4().hex[:8]}",
        description="Unique execution session ID.",
    )
    plan_id: str = Field(description="Referenced ActionPlan ID.")
    plan_version: int = Field(default=1, description="Plan version executed.")
    status: ExecutionStatus = Field(
        default=ExecutionStatus.AUTHORIZED,
        description="Current runtime status.",
    )
    current_task_id: str | None = Field(
        default=None, description="Task ID currently being executed."
    )
    completed_tasks: list[str] = Field(
        default_factory=list, description="Tasks successfully executed."
    )
    failed_tasks: list[str] = Field(
        default_factory=list, description="Tasks that failed or had errors."
    )
    iteration: int = Field(
        default=1, description="Current research refinement cycle iteration."
    )
    max_iterations: int = Field(
        default=3, description="Configured maximum iterations budget."
    )
    evidence: list[Evidence] = Field(
        default_factory=list, description="Accumulated evidence store."
    )
    evidence_count: int = Field(default=0, description="Total evidence count.")
    sources: list[str] = Field(
        default_factory=list, description="Distinct source URLs discovered."
    )
    queries_executed: list[str] = Field(
        default_factory=list, description="Set of executed research queries."
    )
    critique: CriticEvaluation | None = Field(
        default=None, description="Latest Critic evaluation."
    )
    missing_information: list[str] = Field(
        default_factory=list, description="Gaps identified by Critic."
    )
    verification: VerificationResult | None = Field(
        default=None, description="Latest Verification result."
    )
    confidence_score: float | None = Field(
        default=None, description="Current verified confidence score."
    )
    final_result: ActionableResult | None = Field(
        default=None, description="Final actionable deliverable."
    )
    logs: list[str] = Field(
        default_factory=list, description="Operational event logs."
    )
    worker_id: str | None = Field(
        default=None, description="Worker instance ID holding execution lease."
    )
    claimed_at: str | None = Field(
        default=None, description="ISO timestamp when worker claimed lease."
    )
    error: str | None = Field(
        default=None, description="Error message if execution failed."
    )
    started_at: str = Field(
        default_factory=lambda: datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        description="Execution start timestamp.",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        description="Latest update timestamp.",
    )

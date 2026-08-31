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

"""Comprehensive Unit and Scenario Tests for Phase 3 Autonomous Execution."""

import pytest

from app.approval_service import ApprovalService
from app.execution_manager import (
    ExecutionAuthorizationError,
    ExecutionManager,
)
from app.models import (
    ActionLevel,
    ActionPlan,
    CriticDecision,
    ExecutionAuthorization,
    ExecutionStatus,
    PlanTask,
    Priority,
    TaskType,
)
from app.repository import InMemoryPlanRepository
from app.research import ResearchEngine
from app.specialists import (
    CriticAgent,
    FinalizerAgent,
    VerificationAgent,
)


@pytest.fixture
def repo() -> InMemoryPlanRepository:
    """Fresh in-memory repository."""
    return InMemoryPlanRepository()


@pytest.fixture
def approval_svc(repo: InMemoryPlanRepository) -> ApprovalService:
    """Fresh ApprovalService instance."""
    return ApprovalService(repository=repo)


@pytest.fixture
def manager(
    repo: InMemoryPlanRepository, approval_svc: ApprovalService
) -> ExecutionManager:
    """Fresh ExecutionManager instance."""
    return ExecutionManager(repository=repo, approval_svc=approval_svc)


@pytest.fixture
def sample_approved_plan(
    approval_svc: ApprovalService,
) -> tuple[ActionPlan, ExecutionAuthorization]:
    """Sample approved ActionPlan with valid authorization ticket."""
    task1 = PlanTask(
        id="task_001",
        title="Research AI coding agents",
        description="Search for candidate AI coding assistants and pricing.",
        task_type=TaskType.RESEARCH,
        priority=Priority.HIGH,
        action_level=ActionLevel.READ,
        expected_output="List of coding tools",
    )
    task2 = PlanTask(
        id="task_002",
        title="Analyze pricing and startup suitability",
        description="Compare pricing tiers and IDE integration capabilities.",
        task_type=TaskType.ANALYSIS,
        priority=Priority.MEDIUM,
        action_level=ActionLevel.ANALYZE,
        dependencies=["task_001"],
        expected_output="Comparison table",
    )
    task3 = PlanTask(
        id="task_003",
        title="Deploy chosen integration to team repo",
        description="Configure repository secrets and workflow file.",
        task_type=TaskType.ACTION,
        priority=Priority.HIGH,
        action_level=ActionLevel.EXTERNAL_ACTION,
        is_consequential=True,
        dependencies=["task_002"],
        expected_output="Configured integration proposal",
    )

    plan = ActionPlan(
        goal="Research the best AI coding agents for a small software startup and recommend the best option based on price, coding capability, integrations, and suitability.",
        objective="Recommend top AI coding assistant for a budget-conscious startup.",
        summary="Decomposed research, analysis, and setup roadmap.",
        tasks=[task1, task2, task3],
        final_deliverable="Actionable recommendation report.",
    )

    registered = approval_svc.register_plan(plan)
    _, auth = approval_svc.approve_plan(registered.plan_id, user_id="lead-dev")
    return registered, auth


def test_1_approved_plan_starts_and_completes_execution(
    manager: ExecutionManager,
    sample_approved_plan: tuple[ActionPlan, ExecutionAuthorization],
):
    """Test 1: Approved plan executes autonomously and reaches COMPLETED status."""
    plan, auth = sample_approved_plan
    result = manager.execute_plan(plan, auth)

    assert result.status == ExecutionStatus.COMPLETED
    assert result.plan_id == plan.plan_id
    assert len(result.key_findings) > 0
    assert len(result.recommendations) > 0
    assert len(result.next_actions) > 0
    assert len(result.evidence) > 0
    assert result.confidence_score >= 0.85


def test_2_unapproved_plan_cannot_execute(
    manager: ExecutionManager,
    approval_svc: ApprovalService,
):
    """Test 2: Unapproved plan raises ExecutionAuthorizationError."""
    unapproved_plan = ActionPlan(
        goal="Unapproved goal",
        objective="Objective",
        summary="Summary",
        tasks=[],
        final_deliverable="Deliverable",
    )
    registered = approval_svc.register_plan(unapproved_plan)

    fake_auth = ExecutionAuthorization(
        plan_id=registered.plan_id,
        plan_version=registered.version,
        authorized_by="attacker",
        is_active=False,  # Inactive
    )

    with pytest.raises(ExecutionAuthorizationError):
        manager.execute_plan(registered, fake_auth)


def test_3_research_task_produces_structured_evidence():
    """Test 3: Research engine produces grounded Evidence items with citations."""
    engine = ResearchEngine()
    evidence = engine.execute_research_task(
        task_id="task_001",
        query="best AI coding tools for small startups",
    )

    assert len(evidence) >= 3
    for ev in evidence:
        assert ev.claim != ""
        assert ev.source_title != ""
        assert ev.source_url.startswith("http")
        assert 0.0 <= ev.relevance_score <= 1.0


def test_4_critic_identifies_missing_information():
    """Test 4: Critic identifies missing gaps and requests NEEDS_REFINEMENT."""
    critic = CriticAgent()
    plan = ActionPlan(
        goal="Research AI coding agents with verified pricing and IDE integration",
        objective="Evaluate coding tools",
        summary="Summary",
        tasks=[],
        final_deliverable="Report",
    )

    # Empty evidence should trigger refinement
    critique = critic.evaluate(
        goal=plan.goal,
        plan=plan,
        evidence=[],
        iteration=1,
        max_iterations=3,
    )

    assert critique.decision == CriticDecision.NEEDS_REFINEMENT
    assert len(critique.missing_information) > 0
    assert len(critique.follow_up_queries) > 0


def test_5_refinement_generates_follow_up_queries():
    """Test 5: Critic generates valid follow-up search queries."""
    critic = CriticAgent()
    plan = ActionPlan(
        goal="Research pricing and deployment options for AI tools",
        objective="Pricing analysis",
        summary="Summary",
        tasks=[],
        final_deliverable="Report",
    )

    critique = critic.evaluate(
        goal=plan.goal,
        plan=plan,
        evidence=[],
        iteration=1,
        max_iterations=3,
    )

    assert any(
        "pricing" in q.lower() or "deployment" in q.lower()
        for q in critique.follow_up_queries
    )


def test_6_successful_refinement_loop(
    manager: ExecutionManager,
    sample_approved_plan: tuple[ActionPlan, ExecutionAuthorization],
):
    """Test 6: Autonomous loop iterates, refines evidence, and reaches verification."""
    plan, auth = sample_approved_plan
    result = manager.execute_plan(plan, auth)
    assert result.status == ExecutionStatus.COMPLETED

    state = manager.get_execution_state(plan.plan_id)
    assert state is not None
    assert state.iteration >= 1
    assert len(state.evidence) >= 3
    assert state.critique is not None


def test_7_maximum_iterations_limit():
    """Test 7: Loop halts when iteration reaches max_iterations."""
    critic = CriticAgent()
    plan = ActionPlan(
        goal="Broad undefined research goal",
        objective="Objective",
        summary="Summary",
        tasks=[],
        final_deliverable="Deliverable",
    )

    # At iteration == max_iterations, critic concludes READY
    critique = critic.evaluate(
        goal=plan.goal,
        plan=plan,
        evidence=[],
        iteration=3,
        max_iterations=3,
    )

    assert critique.decision == CriticDecision.READY
    assert "Maximum iteration budget" in critique.reason


def test_8_duplicate_query_prevention():
    """Test 8: Duplicate queries are tracked and avoided."""
    engine = ResearchEngine()
    query = "GitHub Copilot pricing plans"

    engine.execute_research_task("t1", query)
    assert engine.is_duplicate_query(query) is True
    assert engine.is_duplicate_query("GITHUB COPILOT PRICING PLANS ") is True
    assert engine.is_duplicate_query("Different Query") is False


def test_9_verification_agent_scoring():
    """Test 9: VerificationAgent checks claim coverage and computes confidence."""
    verifier = VerificationAgent()
    findings = ["• Finding 1", "• Finding 2"]
    engine = ResearchEngine()
    evidence = engine.execute_research_task("t1", "AI coding tools")

    ver_res = verifier.verify("Test goal", findings, evidence)
    assert ver_res.is_verified is True
    assert ver_res.confidence >= 0.85
    assert len(ver_res.limitations) > 0


def test_10_finalizer_synthesis():
    """Test 10: FinalizerAgent compiles structured actionable deliverable."""
    finalizer = FinalizerAgent()
    verifier = VerificationAgent()
    engine = ResearchEngine()
    evidence = engine.execute_research_task("t1", "AI coding tools")
    findings = ["• Finding 1"]
    ver_res = verifier.verify("Goal", findings, evidence)

    plan = ActionPlan(
        goal="Goal",
        objective="Objective",
        summary="Summary",
        tasks=[],
        final_deliverable="Deliverable",
    )

    result = finalizer.finalize(
        goal=plan.goal,
        plan=plan,
        findings=findings,
        verification=ver_res,
        evidence=evidence,
        completed_tasks=["task_001"],
        failed_tasks=[],
        iterations_used=1,
        execution_id="exec-123",
    )

    assert result.execution_id == "exec-123"
    assert len(result.recommendations) > 0
    assert len(result.next_actions) > 0
    assert len(result.evidence) > 0


def test_11_evidence_traceability(
    manager: ExecutionManager,
    sample_approved_plan: tuple[ActionPlan, ExecutionAuthorization],
):
    """Test 11: All final deliverable items contain traceable citations."""
    plan, auth = sample_approved_plan
    result = manager.execute_plan(plan, auth)

    for ev in result.evidence:
        assert ev.source_url != ""
        assert ev.source_title != ""
        assert ev.claim != ""


def test_12_no_destructive_side_effects_executed(
    manager: ExecutionManager,
    sample_approved_plan: tuple[ActionPlan, ExecutionAuthorization],
):
    """Test 12: External/destructive tasks are recognized and safely handled without unmonitored side effects."""
    plan, auth = sample_approved_plan
    result = manager.execute_plan(plan, auth)

    state = manager.get_execution_state(plan.plan_id)
    assert state is not None
    # Consequential task was safely processed
    assert "task_003" in result.completed_tasks
    assert any("CONSEQUENTIAL" in log for log in state.logs)


def test_13_scenario_semiconductor_ecosystem(
    manager: ExecutionManager,
    approval_svc: ApprovalService,
):
    """Test 13: Complex scenario — India's semiconductor manufacturing opportunity analysis."""
    task1 = PlanTask(
        id="task_001",
        title="Analyze semiconductor fiscal policy and ISM subsidies",
        description="Evaluate government subsidies, ATMP incentives, and fab capital expenditure requirements.",
        task_type=TaskType.RESEARCH,
        priority=Priority.HIGH,
        action_level=ActionLevel.READ,
        expected_output="Fiscal incentive summary",
    )
    task2 = PlanTask(
        id="task_002",
        title="Evaluate OSAT packaging and fabless design ecosystem",
        description="Identify leading investment opportunities in compound semiconductors and packaging.",
        task_type=TaskType.ANALYSIS,
        priority=Priority.HIGH,
        action_level=ActionLevel.ANALYZE,
        dependencies=["task_001"],
        expected_output="Opportunity ranking",
    )

    plan = ActionPlan(
        goal="Analyze India's semiconductor manufacturing opportunity and recommend top investment areas for the next 5 years.",
        objective="Identify top semiconductor investment sectors in India.",
        summary="Deconstructed semiconductor research roadmap.",
        tasks=[task1, task2],
        final_deliverable="Semiconductor Investment Strategy Report.",
    )

    registered = approval_svc.register_plan(plan)
    _, auth = approval_svc.approve_plan(
        registered.plan_id, user_id="investor-lead"
    )

    result = manager.execute_plan(registered, auth)
    assert result.status == ExecutionStatus.COMPLETED
    assert any(
        "semiconductor" in e.claim.lower() or "ism" in e.claim.lower()
        for e in result.evidence
    )
    assert len(result.recommendations) > 0

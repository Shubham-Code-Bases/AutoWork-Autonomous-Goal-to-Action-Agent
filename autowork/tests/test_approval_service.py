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

"""Unit tests for AutoWork Phase 2 Human Approval Gate and State Machine."""

import pytest

from app.approval_service import (
    ApprovalService,
    PlanNotFoundError,
    PlanValidationError,
)
from app.models import (
    ActionLevel,
    ActionPlan,
    ApprovalStatus,
    PlanStatus,
    PlanTask,
    Priority,
    TaskType,
)
from app.repository import InMemoryPlanRepository


@pytest.fixture
def repo() -> InMemoryPlanRepository:
    """Fresh in-memory repository for each test."""
    return InMemoryPlanRepository()


@pytest.fixture
def service(repo: InMemoryPlanRepository) -> ApprovalService:
    """Fresh ApprovalService instance."""
    return ApprovalService(repository=repo)


@pytest.fixture
def sample_plan() -> ActionPlan:
    """Sample valid ActionPlan for testing."""
    task1 = PlanTask(
        id="task_001",
        title="Analyze market options",
        description="Search candidate AI tools.",
        task_type=TaskType.RESEARCH,
        priority=Priority.HIGH,
        action_level=ActionLevel.READ,
        expected_output="List of tools",
    )
    task2 = PlanTask(
        id="task_002",
        title="Compare pricing models",
        description="Extract tier pricing.",
        task_type=TaskType.ANALYSIS,
        priority=Priority.MEDIUM,
        action_level=ActionLevel.ANALYZE,
        dependencies=["task_001"],
        expected_output="Pricing table",
    )
    task3 = PlanTask(
        id="task_003",
        title="Deploy chosen tool integration",
        description="Run setup scripts to connect IDE.",
        task_type=TaskType.ACTION,
        priority=Priority.HIGH,
        action_level=ActionLevel.EXTERNAL_ACTION,
        is_consequential=True,
        dependencies=["task_002"],
        expected_output="Active integration",
    )

    return ActionPlan(
        goal="Research and integrate AI coding tool",
        objective="Recommend and set up AI assistant",
        summary="Phased research, analysis, and setup plan.",
        tasks=[task1, task2, task3],
        final_deliverable="Configured AI assistant and report.",
    )


def test_1_plan_enters_awaiting_approval_state(
    service: ApprovalService, sample_plan: ActionPlan
):
    """Test 1: Generated plan enters AWAITING_APPROVAL upon registration."""
    registered = service.register_plan(sample_plan)
    assert registered.status == PlanStatus.AWAITING_APPROVAL
    assert registered.version == 1

    summary = service.get_approval_summary(registered.plan_id)
    assert summary.status == PlanStatus.AWAITING_APPROVAL
    assert summary.is_approvable is True
    assert summary.total_tasks == 3


def test_2_approval_transitions_to_approved_and_authorizes(
    service: ApprovalService, sample_plan: ActionPlan
):
    """Test 2: Human approval transitions state to APPROVED and issues execution authorization."""
    plan = service.register_plan(sample_plan)
    approval, auth = service.approve_plan(plan.plan_id, user_id="lead-engineer")

    assert approval.status == ApprovalStatus.APPROVED
    assert approval.approved_by == "lead-engineer"
    assert approval.decided_at is not None

    assert auth.plan_id == plan.plan_id
    assert auth.plan_version == 1
    assert auth.authorized_by == "lead-engineer"
    assert auth.event == "EXECUTION_AUTHORIZED"
    assert "task_003" in auth.consequential_task_ids

    # Verify authorization check passes
    authorized, active_auth, msg = service.check_execution_authorization(
        plan.plan_id
    )
    assert authorized is True
    assert active_auth is not None
    assert "Execution authorized" in msg


def test_3_rejection_transitions_to_rejected(
    service: ApprovalService, sample_plan: ActionPlan
):
    """Test 3: Plan rejection transitions state to REJECTED and records reason."""
    plan = service.register_plan(sample_plan)
    approval = service.reject_plan(
        plan.plan_id,
        reason="Budget limit exceeded for paid tools.",
        user_id="finance-reviewer",
    )

    assert approval.status == ApprovalStatus.REJECTED
    assert approval.approved_by == "finance-reviewer"
    assert approval.rejection_reason == "Budget limit exceeded for paid tools."

    # Verify execution is denied
    authorized, _, msg = service.check_execution_authorization(plan.plan_id)
    assert authorized is False
    assert "not APPROVED" in msg


def test_4_idempotent_approval(
    service: ApprovalService, sample_plan: ActionPlan
):
    """Test 4: Cannot approve twice / Idempotent approval returns existing authorization."""
    plan = service.register_plan(sample_plan)
    approval1, auth1 = service.approve_plan(
        plan.plan_id, user_id="lead-engineer"
    )
    approval2, auth2 = service.approve_plan(
        plan.plan_id, user_id="lead-engineer"
    )

    assert approval1.approval_id == approval2.approval_id
    assert auth1.authorization_id == auth2.authorization_id


def test_5_cannot_execute_without_approval(
    service: ApprovalService, sample_plan: ActionPlan
):
    """Test 5: Execution is strictly blocked prior to approval."""
    plan = service.register_plan(sample_plan)
    authorized, auth, msg = service.check_execution_authorization(plan.plan_id)

    assert authorized is False
    assert auth is None
    assert "awaiting_approval" in msg


def test_6_plan_modification_increments_version(
    service: ApprovalService, sample_plan: ActionPlan
):
    """Test 6: Modification creates v2 and resets state to AWAITING_APPROVAL."""
    plan = service.register_plan(sample_plan)
    service.approve_plan(plan.plan_id, user_id="lead-engineer")

    # Modify plan
    v2_plan = service.modify_plan(
        plan.plan_id,
        modification_notes="Restrict evaluation to open-source models only.",
        user_id="lead-engineer",
    )

    assert v2_plan.version == 2
    assert v2_plan.status == PlanStatus.AWAITING_APPROVAL
    assert any("open-source" in a for a in v2_plan.assumptions)


def test_7_modified_plan_must_be_approved_again(
    service: ApprovalService, sample_plan: ActionPlan
):
    """Test 7: v1 approval does NOT authorize v2; v2 must be approved explicitly."""
    plan = service.register_plan(sample_plan)
    service.approve_plan(plan.plan_id, user_id="lead-engineer")

    # Modify to v2
    service.modify_plan(
        plan.plan_id,
        modification_notes="Change scope.",
        user_id="lead-engineer",
    )

    # Check authorization on v2 before re-approval
    authorized, _, msg = service.check_execution_authorization(plan.plan_id)
    assert authorized is False
    assert "awaiting_approval" in msg

    # Re-approve v2
    approval_v2, auth_v2 = service.approve_plan(
        plan.plan_id, user_id="lead-engineer"
    )
    assert approval_v2.plan_version == 2
    assert auth_v2.plan_version == 2

    authorized, _, msg = service.check_execution_authorization(plan.plan_id)
    assert authorized is True


def test_8_invalid_missing_dependency_rejected(
    service: ApprovalService, sample_plan: ActionPlan
):
    """Test 8: Plan with missing dependency fails registration and cannot be approved."""
    bad_plan = sample_plan.model_copy(deep=True)
    bad_plan.tasks[1].dependencies = ["task_999"]  # Missing

    with pytest.raises(PlanValidationError):
        service.register_plan(bad_plan)


def test_9_circular_dependency_rejected(
    service: ApprovalService, sample_plan: ActionPlan
):
    """Test 9: Circular dependency graph fails validation."""
    cyclic_plan = sample_plan.model_copy(deep=True)
    cyclic_plan.tasks[0].dependencies = ["task_003"]  # Cycle 1 -> 2 -> 3 -> 1

    with pytest.raises(PlanValidationError):
        service.register_plan(cyclic_plan)


def test_10_self_dependency_rejected(
    service: ApprovalService, sample_plan: ActionPlan
):
    """Test 10: Task depending on itself fails validation."""
    self_dep_plan = sample_plan.model_copy(deep=True)
    self_dep_plan.tasks[0].dependencies = ["task_001"]

    with pytest.raises(PlanValidationError):
        service.register_plan(self_dep_plan)


def test_11_consequential_actions_visible_in_summary(
    service: ApprovalService, sample_plan: ActionPlan
):
    """Test 11: Consequential/dangerous actions are clearly exposed in ApprovalSummary."""
    plan = service.register_plan(sample_plan)
    summary = service.get_approval_summary(plan.plan_id)

    assert len(summary.consequential_tasks) == 1
    assert summary.consequential_tasks[0].id == "task_003"
    assert (
        summary.consequential_tasks[0].action_level
        == ActionLevel.EXTERNAL_ACTION
    )


def test_12_plan_not_found_raises(service: ApprovalService):
    """Test error raised when accessing non-existent plan ID."""
    with pytest.raises(PlanNotFoundError):
        service.get_approval_summary("non_existent_plan")

    with pytest.raises(PlanNotFoundError):
        service.approve_plan("non_existent_plan")

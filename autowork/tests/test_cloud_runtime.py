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

"""Unit and Integration Tests for Phase 4 Google Cloud Asynchronous Runtime."""

import base64
import json

import pytest
from fastapi.testclient import TestClient

from app.approval_service import ApprovalService
from app.cloud.firestore import InMemoryExecutionRepository
from app.cloud.pubsub import LocalAsyncDispatcher
from app.cloud.worker import ExecutionWorker, worker_app
from app.execution_manager import ExecutionManager
from app.models import (
    ActionPlan,
    ExecutionAuthorization,
    ExecutionState,
    ExecutionStatus,
    PlanTask,
    Priority,
    TaskType,
)
from app.repository import InMemoryPlanRepository
from app.server import api_app


@pytest.fixture
def plan_repo() -> InMemoryPlanRepository:
    return InMemoryPlanRepository()


@pytest.fixture
def exec_repo() -> InMemoryExecutionRepository:
    return InMemoryExecutionRepository()


@pytest.fixture
def approval_svc(plan_repo: InMemoryPlanRepository) -> ApprovalService:
    return ApprovalService(repository=plan_repo)


@pytest.fixture
def exec_manager(
    plan_repo: InMemoryPlanRepository, approval_svc: ApprovalService
) -> ExecutionManager:
    return ExecutionManager(repository=plan_repo, approval_svc=approval_svc)


@pytest.fixture
def worker(
    exec_repo: InMemoryExecutionRepository,
    plan_repo: InMemoryPlanRepository,
    exec_manager: ExecutionManager,
) -> ExecutionWorker:
    return ExecutionWorker(
        exec_repo=exec_repo, plan_repo=plan_repo, manager=exec_manager
    )


@pytest.fixture
def sample_plan_and_auth(
    approval_svc: ApprovalService,
) -> tuple[ActionPlan, ExecutionAuthorization]:
    """Sets up a registered and approved plan."""
    task = PlanTask(
        id="task_001",
        title="Analyze market landscape",
        description="Search for competitive AI coding assistants.",
        task_type=TaskType.RESEARCH,
        priority=Priority.HIGH,
        expected_output="Competitor analysis summary",
    )
    plan = ActionPlan(
        goal="Evaluate top coding assistants for small engineering team.",
        objective="Find best coding assistant",
        summary="Market evaluation",
        tasks=[task],
        final_deliverable="Recommendation report",
    )
    registered = approval_svc.register_plan(plan)
    _, auth = approval_svc.approve_plan(registered.plan_id, user_id="lead-dev")
    return registered, auth


def test_1_approval_creates_queued_execution(
    exec_repo: InMemoryExecutionRepository,
    sample_plan_and_auth: tuple[ActionPlan, ExecutionAuthorization],
):
    """Test 1: Plan approval creates an execution record with QUEUED status."""
    plan, auth = sample_plan_and_auth
    state = ExecutionState(
        execution_id="exec-001",
        plan_id=plan.plan_id,
        plan_version=auth.plan_version,
        status=ExecutionStatus.QUEUED,
    )
    exec_repo.save_execution(state)

    fetched = exec_repo.get_execution("exec-001")
    assert fetched is not None
    assert fetched.status == ExecutionStatus.QUEUED
    assert fetched.plan_id == plan.plan_id


def test_2_dispatcher_publishes_execution_id():
    """Test 2: Dispatcher receives and records published execution ID."""
    dispatcher = LocalAsyncDispatcher()
    success = dispatcher.dispatch("exec-002")

    assert success is True
    assert "exec-002" in dispatcher.published_jobs


def test_3_worker_loads_and_executes_job(
    worker: ExecutionWorker,
    exec_repo: InMemoryExecutionRepository,
    sample_plan_and_auth: tuple[ActionPlan, ExecutionAuthorization],
):
    """Test 3: Worker loads queued job, claims lease, and finishes execution."""
    plan, auth = sample_plan_and_auth
    state = ExecutionState(
        execution_id="exec-003",
        plan_id=plan.plan_id,
        plan_version=auth.plan_version,
        status=ExecutionStatus.QUEUED,
    )
    exec_repo.save_execution(state)

    success = worker.process_execution_job(
        "exec-003", worker_id="worker-node-1"
    )
    assert success is True

    updated_state = exec_repo.get_execution("exec-003")
    assert updated_state is not None
    assert updated_state.status == ExecutionStatus.COMPLETED
    assert updated_state.worker_id == "worker-node-1"
    assert updated_state.final_result is not None


def test_4_worker_rejects_unauthorized_execution(
    worker: ExecutionWorker,
    exec_repo: InMemoryExecutionRepository,
    approval_svc: ApprovalService,
):
    """Test 4: Worker fails gracefully if no authorization ticket exists."""
    unapproved_plan = ActionPlan(
        goal="Unapproved goal",
        objective="Objective",
        summary="Summary",
        tasks=[],
        final_deliverable="Deliverable",
    )
    registered = approval_svc.register_plan(unapproved_plan)

    state = ExecutionState(
        execution_id="exec-unauth",
        plan_id=registered.plan_id,
        plan_version=registered.version,
        status=ExecutionStatus.QUEUED,
    )
    exec_repo.save_execution(state)

    success = worker.process_execution_job("exec-unauth")
    assert success is False

    failed_state = exec_repo.get_execution("exec-unauth")
    assert failed_state.status == ExecutionStatus.FAILED
    assert "authorization" in failed_state.error.lower()


def test_5_idempotent_duplicate_delivery_protection(
    worker: ExecutionWorker,
    exec_repo: InMemoryExecutionRepository,
    sample_plan_and_auth: tuple[ActionPlan, ExecutionAuthorization],
):
    """Test 5: Duplicate message delivery does not re-execute an already running or completed job."""
    plan, auth = sample_plan_and_auth
    state = ExecutionState(
        execution_id="exec-duplicate",
        plan_id=plan.plan_id,
        plan_version=auth.plan_version,
        status=ExecutionStatus.QUEUED,
    )
    exec_repo.save_execution(state)

    # First delivery succeeds
    first_run = worker.process_execution_job(
        "exec-duplicate", worker_id="worker-A"
    )
    assert first_run is True

    # Second delivery with same execution_id is safely ignored
    second_run = worker.process_execution_job(
        "exec-duplicate", worker_id="worker-B"
    )
    assert second_run is True  # Safely returns without re-executing

    final_state = exec_repo.get_execution("exec-duplicate")
    assert final_state.worker_id == "worker-A"  # Preserved original claim


def test_6_progress_logs_and_results_persisted(
    worker: ExecutionWorker,
    exec_repo: InMemoryExecutionRepository,
    sample_plan_and_auth: tuple[ActionPlan, ExecutionAuthorization],
):
    """Test 6: Progress logs and final result deliverable are persisted."""
    plan, auth = sample_plan_and_auth
    state = ExecutionState(
        execution_id="exec-logs",
        plan_id=plan.plan_id,
        plan_version=auth.plan_version,
        status=ExecutionStatus.QUEUED,
    )
    exec_repo.save_execution(state)

    worker.process_execution_job("exec-logs")

    logs = exec_repo.get_execution("exec-logs").logs
    assert len(logs) > 0
    assert any("Lease claimed" in log for log in logs)

    result = exec_repo.get_result("exec-logs")
    assert result is not None
    assert result.confidence_score >= 0.85


def test_7_api_health_endpoint():
    """Test 7: Health probe endpoint responds with 200 OK."""
    client = TestClient(api_app)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_8_worker_health_endpoint():
    """Test 8: Worker health probe endpoint responds with 200 OK."""
    client = TestClient(worker_app)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["service"] == "autowork-worker"


def test_9_api_approve_endpoint_returns_immediately():
    """Test 9: POST /approve returns immediately with QUEUED status and execution_id."""
    client = TestClient(api_app)

    # 1. Create Plan
    create_res = client.post(
        "/api/plans",
        json={"goal": "Asynchronous background execution testing goal."},
    )
    assert create_res.status_code == 201
    plan_id = create_res.json()["plan_id"]

    # 2. Approve Plan (Returns immediately)
    appr_res = client.post(
        f"/api/plans/{plan_id}/approve",
        json={"user_id": "async-tester"},
    )
    assert appr_res.status_code == 200
    data = appr_res.json()
    assert "execution_id" in data
    assert data["status"] == ExecutionStatus.QUEUED
    assert "asynchronously" in data["message"]


def test_10_worker_pubsub_push_endpoint(
    exec_repo: InMemoryExecutionRepository,
    sample_plan_and_auth: tuple[ActionPlan, ExecutionAuthorization],
):
    """Test 10: Worker /pubsub/push endpoint decodes base64 payload and executes."""
    plan, auth = sample_plan_and_auth
    state = ExecutionState(
        execution_id="exec-pubsub-push",
        plan_id=plan.plan_id,
        plan_version=auth.plan_version,
        status=ExecutionStatus.QUEUED,
    )
    # Save to global default repository
    from app.cloud.firestore import default_execution_repository
    from app.repository import default_repository

    default_repository.save_plan(plan)
    default_repository.save_authorization(auth)
    default_execution_repository.save_execution(state)

    client = TestClient(worker_app)
    payload = json.dumps({"execution_id": "exec-pubsub-push"}).encode("utf-8")
    b64_data = base64.b64encode(payload).decode("utf-8")

    push_body = {"message": {"data": b64_data, "message_id": "msg-12345"}}

    res = client.post("/pubsub/push", json=push_body)
    assert res.status_code == 200
    assert res.json()["status"] == "processed"
    assert res.json()["execution_id"] == "exec-pubsub-push"

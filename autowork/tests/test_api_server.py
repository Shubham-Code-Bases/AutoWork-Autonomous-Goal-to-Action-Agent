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

"""Integration tests for AutoWork FastAPI endpoints, approval, and autonomous execution."""

import pytest
from fastapi.testclient import TestClient

from app.models import ExecutionStatus, PlanStatus
from app.server import api_app


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client fixture."""
    return TestClient(api_app)


def test_api_html_dashboard_accessible(client: TestClient):
    """Verify the root UI dashboard renders correctly."""
    response = client.get("/")
    assert response.status_code == 200
    assert "AutoWork Goal-to-Action" in response.text
    assert "Human Approval Gate" in response.text


def test_api_plan_lifecycle_full_flow(client: TestClient):
    """Test full end-to-end API lifecycle: Create -> Summary -> Modify -> Approve -> Execute."""
    # 1. Create Plan
    res = client.post(
        "/api/plans",
        json={
            "goal": "Research cloud database options for high-throughput IoT analytics."
        },
    )
    assert res.status_code == 201
    data = res.json()
    plan_id = data["plan_id"]
    assert data["status"] == PlanStatus.AWAITING_APPROVAL

    # 2. Get Plan Summary
    summary_res = client.get(f"/api/plans/{plan_id}/summary")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["is_approvable"] is True
    assert summary["total_tasks"] >= 3

    # 3. Check Authorization (Should be FALSE prior to approval)
    auth_check = client.get(f"/api/plans/{plan_id}/authorization")
    assert auth_check.status_code == 200
    assert auth_check.json()["is_authorized"] is False

    # 4. Modify Plan to v2
    mod_res = client.post(
        f"/api/plans/{plan_id}/modify",
        json={"modification_notes": "Prioritize managed serverless options."},
    )
    assert mod_res.status_code == 200
    assert mod_res.json()["new_version"] == 2
    assert mod_res.json()["status"] == PlanStatus.AWAITING_APPROVAL

    # 5. Approve Plan
    appr_res = client.post(
        f"/api/plans/{plan_id}/approve",
        json={"user_id": "tech-lead"},
    )
    assert appr_res.status_code == 200
    appr_data = appr_res.json()
    assert appr_data["status"] == ExecutionStatus.QUEUED
    assert appr_data["authorization"]["plan_version"] == 2
    assert appr_data["authorization"]["authorized_by"] == "tech-lead"

    # 6. Check Authorization (Should be TRUE now)
    auth_check_after = client.get(f"/api/plans/{plan_id}/authorization")
    assert auth_check_after.status_code == 200
    assert auth_check_after.json()["is_authorized"] is True

    # 7. Execute Plan Autonomously (Phase 3)
    exec_res = client.post(f"/api/plans/{plan_id}/execute")
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["status"] == ExecutionStatus.COMPLETED
    assert len(exec_data["recommendations"]) > 0
    assert len(exec_data["evidence"]) > 0

    # 8. Retrieve Live Execution State & Progress
    state_res = client.get(f"/api/plans/{plan_id}/execution")
    assert state_res.status_code == 200
    state_data = state_res.json()
    assert state_data["status"] == ExecutionStatus.COMPLETED
    assert len(state_data["logs"]) > 0


def test_api_unauthorized_execution_rejected(client: TestClient):
    """Verify that unapproved plan execution is rejected with 403 Forbidden."""
    res = client.post(
        "/api/plans",
        json={"goal": "Unapproved goal needing execution attempt."},
    )
    assert res.status_code == 201
    plan_id = res.json()["plan_id"]

    exec_res = client.post(f"/api/plans/{plan_id}/execute")
    assert exec_res.status_code == 403
    assert "Forbidden" in exec_res.json()["error"]


def test_api_plan_rejection_flow(client: TestClient):
    """Test plan creation followed by rejection."""
    res = client.post(
        "/api/plans",
        json={
            "goal": "Build an unconstrained scraper for private internal endpoints."
        },
    )
    assert res.status_code == 201
    plan_id = res.json()["plan_id"]

    reject_res = client.post(
        f"/api/plans/{plan_id}/reject",
        json={
            "reason": "Security policy violation.",
            "user_id": "security-officer",
        },
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == PlanStatus.REJECTED

    # Check Authorization (Denied)
    auth_check = client.get(f"/api/plans/{plan_id}/authorization")
    assert auth_check.status_code == 200
    assert auth_check.json()["is_authorized"] is False

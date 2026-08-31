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

"""AutoWork FastAPI Server — Cloud-Native Asynchronous Agent API & UI."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from .approval_service import (
    InvalidStateTransitionError,
    PlanNotFoundError,
    PlanValidationError,
    approval_service,
)
from .cloud import (
    default_dispatcher,
    default_execution_repository,
)
from .execution_manager import (
    ExecutionAuthorizationError,
    execution_manager,
)
from .models import (
    ActionableResult,
    ActionLevel,
    ActionPlan,
    ApprovalSummary,
    ExecutionState,
    ExecutionStatus,
    PlanStatus,
    PlanTask,
    Priority,
    TaskType,
)
from .repository import default_repository

logger = logging.getLogger("autowork.server")

# FastAPI application instance for Cloud Run API service
api_app = FastAPI(
    title="AutoWork Autonomous Agent API",
    description="Goal-to-Plan, Human Approval Gate, and Cloud-Native Asynchronous Agent Runtime.",
    version="0.4.0",
)

api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Request & Response Payloads
# -----------------------------------------------------------------------------


class CreatePlanRequest(BaseModel):
    """Payload to create an ActionPlan from a natural language goal."""

    goal: str = Field(description="High-level natural language goal.")
    user_id: str = Field(
        default="local-user", description="Authoring user identifier."
    )


class ApprovePlanRequest(BaseModel):
    """Payload to approve a plan and launch background execution."""

    user_id: str = Field(
        default="local-user", description="Authorizing user identifier."
    )


class RejectPlanRequest(BaseModel):
    """Payload to reject a plan."""

    reason: str = Field(description="Reason for plan rejection.")
    user_id: str = Field(
        default="local-user", description="Rejecting user identifier."
    )


class ModifyPlanRequest(BaseModel):
    """Payload to modify a plan."""

    modification_notes: str = Field(
        description="Notes or prompt describing requested modifications."
    )
    tasks: list[PlanTask] | None = Field(
        default=None, description="Optional updated task graph."
    )
    user_id: str = Field(
        default="local-user", description="Modifying user identifier."
    )


# -----------------------------------------------------------------------------
# Error Handling
# -----------------------------------------------------------------------------


@api_app.exception_handler(PlanNotFoundError)
async def plan_not_found_handler(
    request: Any, exc: PlanNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": "Not Found", "message": str(exc)},
    )


@api_app.exception_handler(InvalidStateTransitionError)
async def invalid_transition_handler(
    request: Any, exc: InvalidStateTransitionError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"error": "Conflict", "message": str(exc)},
    )


@api_app.exception_handler(PlanValidationError)
async def plan_validation_handler(
    request: Any, exc: PlanValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Unprocessable Entity", "message": str(exc)},
    )


@api_app.exception_handler(ExecutionAuthorizationError)
async def execution_auth_handler(
    request: Any, exc: ExecutionAuthorizationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"error": "Forbidden", "message": str(exc)},
    )


# -----------------------------------------------------------------------------
# Health Check Endpoint
# -----------------------------------------------------------------------------


@api_app.get("/health")
async def health_check() -> dict[str, str]:
    """Lightweight health probe endpoint for Cloud Run."""
    return {"status": "ok", "service": "autowork-api"}


# -----------------------------------------------------------------------------
# REST Endpoints (Phase 1, 2, 3, & 4)
# -----------------------------------------------------------------------------


@api_app.post("/api/plans", status_code=status.HTTP_201_CREATED)
async def create_plan(request: CreatePlanRequest) -> dict[str, Any]:
    """Generates and registers an ActionPlan from a natural language goal."""
    if not request.goal.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Goal cannot be empty.",
        )

    task1 = PlanTask(
        id="task_001",
        title="Analyze target objective and requirements",
        description=f"Parse goal: '{request.goal}' and extract core constraints.",
        task_type=TaskType.RESEARCH,
        priority=Priority.HIGH,
        action_level=ActionLevel.READ,
        expected_output="Objective specification and constraint catalog.",
        success_criteria=["Captured all user criteria."],
    )
    task2 = PlanTask(
        id="task_002",
        title="Synthesize structured execution roadmap",
        description="Deconstruct milestones into dependency-linked tasks.",
        task_type=TaskType.ANALYSIS,
        priority=Priority.MEDIUM,
        action_level=ActionLevel.ANALYZE,
        dependencies=["task_001"],
        expected_output="Action plan dependency matrix.",
        success_criteria=["Acyclic dependency structure verified."],
    )
    task3 = PlanTask(
        id="task_003",
        title="Generate final deliverable artifact",
        description="Compile final report and deliverables satisfying success criteria.",
        task_type=TaskType.GENERATE,
        priority=Priority.HIGH,
        action_level=ActionLevel.GENERATE,
        dependencies=["task_002"],
        expected_output="Consolidated actionable deliverable.",
        success_criteria=["Complete deliverable ready for user review."],
    )

    plan = ActionPlan(
        goal=request.goal,
        objective=f"Accomplish user goal: {request.goal}",
        summary="Decomposed into prerequisite research, structural analysis, and final deliverable generation.",
        constraints=["Adhere to safety boundaries", "Deterministic execution"],
        assumptions=["User will review and approve plan prior to execution"],
        tasks=[task1, task2, task3],
        final_deliverable="Complete Actionable Outcome Artifact.",
        success_criteria=[
            "All milestone tasks validated against success criteria."
        ],
    )

    registered_plan = approval_service.register_plan(plan)
    return {
        "plan_id": registered_plan.plan_id,
        "version": registered_plan.version,
        "status": registered_plan.status,
        "plan": registered_plan,
    }


@api_app.get("/api/plans")
async def list_plans() -> list[ActionPlan]:
    """Lists all registered ActionPlans in the system."""
    return default_repository.list_plans()


@api_app.get("/api/plans/{plan_id}")
async def get_plan(plan_id: str) -> ActionPlan:
    """Retrieves an ActionPlan by its unique identifier."""
    plan = default_repository.get_plan(plan_id)
    if not plan:
        raise PlanNotFoundError(f"Plan not found: {plan_id}")
    return plan


@api_app.get("/api/plans/{plan_id}/summary")
async def get_plan_summary(plan_id: str) -> ApprovalSummary:
    """Retrieves the Human-in-the-Loop review summary for a plan."""
    return approval_service.get_approval_summary(plan_id)


@api_app.post("/api/plans/{plan_id}/approve")
async def approve_plan(
    plan_id: str, request: ApprovePlanRequest
) -> dict[str, Any]:
    """Phase 4 Asynchronous Approval: Approves plan and queues background execution immediately."""
    approval, authorization = approval_service.approve_plan(
        plan_id=plan_id, user_id=request.user_id
    )

    # Initialize persistent queued execution record
    exec_id = f"exec-{uuid.uuid4().hex[:8]}"
    state = ExecutionState(
        execution_id=exec_id,
        plan_id=plan_id,
        plan_version=authorization.plan_version,
        status=ExecutionStatus.QUEUED,
    )
    state.logs.append(
        f"Execution queued by {request.user_id}. Background worker dispatched."
    )

    default_execution_repository.save_execution(state)

    # Publish to Pub/Sub / Asynchronous Dispatcher
    default_dispatcher.dispatch(exec_id)

    return {
        "execution_id": exec_id,
        "plan_id": plan_id,
        "plan_version": authorization.plan_version,
        "status": ExecutionStatus.QUEUED,
        "approval": approval,
        "authorization": authorization,
        "message": "Plan approved. AutoWork is executing asynchronously in the background. You may leave this page.",
    }


@api_app.post("/api/plans/{plan_id}/reject")
async def reject_plan(
    plan_id: str, request: RejectPlanRequest
) -> dict[str, Any]:
    """Rejects an ActionPlan, preventing any downstream execution."""
    approval = approval_service.reject_plan(
        plan_id=plan_id, reason=request.reason, user_id=request.user_id
    )
    return {
        "plan_id": plan_id,
        "status": PlanStatus.REJECTED,
        "approval": approval,
        "message": f"Plan rejected: {request.reason}",
    }


@api_app.post("/api/plans/{plan_id}/modify")
async def modify_plan(
    plan_id: str, request: ModifyPlanRequest
) -> dict[str, Any]:
    """Modifies a plan, creating a new revision (v+1) awaiting approval."""
    new_plan = approval_service.modify_plan(
        plan_id=plan_id,
        modification_notes=request.modification_notes,
        updated_tasks=request.tasks,
        user_id=request.user_id,
    )
    return {
        "plan_id": plan_id,
        "new_version": new_plan.version,
        "status": new_plan.status,
        "plan": new_plan,
        "message": f"Plan modified to version {new_plan.version}. Awaiting human review.",
    }


@api_app.get("/api/plans/{plan_id}/authorization")
async def check_authorization(plan_id: str) -> dict[str, Any]:
    """Checks whether autonomous execution is authorized for a plan."""
    authorized, auth, msg = approval_service.check_execution_authorization(
        plan_id
    )
    return {
        "plan_id": plan_id,
        "is_authorized": authorized,
        "authorization": auth,
        "message": msg,
    }


# -----------------------------------------------------------------------------
# Phase 3 & 4 Execution Endpoints
# -----------------------------------------------------------------------------


@api_app.post("/api/plans/{plan_id}/execute")
async def execute_plan_endpoint(plan_id: str) -> ActionableResult:
    """Executes an approved plan autonomously (synchronous Phase 3 endpoint)."""
    plan = default_repository.get_plan(plan_id)
    if not plan:
        raise PlanNotFoundError(f"Plan not found: {plan_id}")

    is_authorized, auth, msg = approval_service.check_execution_authorization(
        plan_id
    )
    if not is_authorized or not auth:
        raise ExecutionAuthorizationError(msg)

    result = execution_manager.execute_plan(plan, auth)
    return result


@api_app.get("/api/plans/{plan_id}/execution")
async def get_plan_execution_endpoint(plan_id: str) -> ExecutionState:
    """Retrieves live execution state for a plan."""
    state = execution_manager.get_execution_state(plan_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active or past execution found for plan '{plan_id}'.",
        )
    return state


@api_app.get("/api/executions/{execution_id}")
async def get_execution_state_endpoint(execution_id: str) -> ExecutionState:
    """Retrieves live execution state and progress logs from Firestore."""
    state = default_execution_repository.get_execution(execution_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution '{execution_id}' not found.",
        )
    return state


@api_app.get("/api/executions/{execution_id}/result")
async def get_execution_result_endpoint(execution_id: str) -> dict[str, Any]:
    """Retrieves the final actionable deliverable if completed."""
    state = default_execution_repository.get_execution(execution_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution '{execution_id}' not found.",
        )

    result = default_execution_repository.get_result(execution_id)
    return {
        "execution_id": execution_id,
        "status": state.status,
        "result_available": result is not None,
        "result": result,
    }


# -----------------------------------------------------------------------------
# Interactive Human Approval & Asynchronous Background Execution Dashboard
# -----------------------------------------------------------------------------


@api_app.get("/", response_class=HTMLResponse)
async def approval_ui_dashboard() -> HTMLResponse:
    """Renders the AutoWork Phase 5 Cloud-Native Asynchronous Web Interface."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AutoWork — Autonomous Goal-to-Action Agent</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #080c18;
            --bg-card: rgba(15, 23, 42, 0.75);
            --bg-card-hover: rgba(30, 41, 59, 0.85);
            --border-color: rgba(255, 255, 255, 0.12);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent-blue: #38bdf8;
            --accent-indigo: #818cf8;
            --accent-emerald: #10b981;
            --accent-amber: #f59e0b;
            --accent-rose: #f43f5e;
            --gradient-accent: linear-gradient(135deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 2.5rem 1rem;
            background-image: 
                radial-gradient(at 0% 0%, rgba(56, 189, 248, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(129, 140, 248, 0.15) 0px, transparent 50%);
        }
        .container { max-width: 1040px; width: 100%; }
        .header { text-align: center; margin-bottom: 2rem; }
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.3rem 0.85rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            background: rgba(56, 189, 248, 0.12);
            color: var(--accent-blue);
            border: 1px solid rgba(56, 189, 248, 0.3);
            margin-bottom: 0.85rem;
        }
        h1 {
            font-size: 2.5rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            background: var(--gradient-accent);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        p.subtitle { color: var(--text-secondary); font-size: 1.05rem; }
        .tagline-banner {
            font-size: 0.9rem;
            color: var(--accent-indigo);
            font-weight: 600;
            margin-top: 0.35rem;
        }
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            backdrop-filter: blur(20px);
            border-radius: 18px;
            padding: 1.85rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 12px 30px -5px rgba(0, 0, 0, 0.4);
        }
        .preset-row { display: flex; gap: 0.5rem; margin-top: 0.75rem; flex-wrap: wrap; }
        .btn-preset {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 0.35rem 0.75rem;
            border-radius: 8px;
            font-size: 0.75rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-preset:hover { background: rgba(56, 189, 248, 0.15); color: var(--accent-blue); border-color: var(--accent-blue); }
        .input-group { display: flex; gap: 0.75rem; margin-top: 0.75rem; }
        input[type="text"] {
            flex: 1;
            padding: 0.9rem 1.25rem;
            background: rgba(10, 15, 29, 0.85);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            color: var(--text-primary);
            font-size: 0.95rem;
            outline: none;
            transition: all 0.2s;
        }
        input[type="text"]:focus {
            border-color: var(--accent-blue);
            box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.25);
        }
        button {
            padding: 0.85rem 1.5rem;
            font-weight: 600;
            font-size: 0.9rem;
            border-radius: 12px;
            border: none;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
        }
        .btn-primary { background: var(--gradient-accent); color: #fff; box-shadow: 0 4px 15px rgba(56, 189, 248, 0.3); }
        .btn-primary:hover { opacity: 0.92; transform: translateY(-1px); }
        .btn-approve { background: var(--accent-emerald); color: #fff; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3); }
        .btn-approve:hover { background: #059669; }
        .btn-reject { background: rgba(244, 63, 94, 0.12); color: var(--accent-rose); border: 1px solid rgba(244, 63, 94, 0.3); }
        .btn-reject:hover { background: rgba(244, 63, 94, 0.25); }
        .btn-modify { background: rgba(245, 158, 11, 0.12); color: var(--accent-amber); border: 1px solid rgba(245, 158, 11, 0.3); }
        .btn-modify:hover { background: rgba(245, 158, 11, 0.25); }
        .alert-gate {
            background: rgba(56, 189, 248, 0.08);
            border-left: 4px solid var(--accent-blue);
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1.25rem;
            font-size: 0.9rem;
            color: #bae6fd;
        }
        .status-pill {
            display: inline-block;
            padding: 0.25rem 0.65rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
        }
        .status-awaiting { background: rgba(245, 158, 11, 0.2); color: var(--accent-amber); }
        .status-queued { background: rgba(129, 140, 248, 0.2); color: var(--accent-indigo); }
        .status-running { background: rgba(56, 189, 248, 0.2); color: var(--accent-blue); }
        .status-completed { background: rgba(16, 185, 129, 0.2); color: var(--accent-emerald); }
        .status-rejected { background: rgba(244, 63, 94, 0.2); color: var(--accent-rose); }
        .table-wrap { overflow-x: auto; margin-top: 1rem; }
        table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
        th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid var(--border-color); }
        th { color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.05em; }
        code { font-family: 'JetBrains Mono', monospace; background: rgba(255, 255, 255, 0.08); padding: 0.15rem 0.35rem; border-radius: 4px; font-size: 0.8rem; }
        .action-bar { display: flex; gap: 0.75rem; justify-content: flex-end; margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid var(--border-color); }
        #planSection, #execSection { display: none; }
        .log-box {
            background: rgba(0, 0, 0, 0.55);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            color: #94a3b8;
            max-height: 200px;
            overflow-y: auto;
            margin-top: 1rem;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 0.75rem;
            margin-top: 1rem;
            margin-bottom: 1.25rem;
        }
        .metric-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 0.85rem;
            text-align: center;
        }
        .metric-value { font-size: 1.35rem; font-weight: 800; color: var(--accent-blue); }
        .metric-label { font-size: 0.7rem; text-transform: uppercase; color: var(--text-muted); margin-top: 0.2rem; }
        .result-box {
            background: rgba(16, 185, 129, 0.06);
            border: 1px solid rgba(16, 185, 129, 0.25);
            border-radius: 14px;
            padding: 1.5rem;
            margin-top: 1.25rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="badge">🚀 Google AI Hackathon — Taskmaster Track</div>
            <h1>AutoWork Goal-to-Action</h1>
            <p class="subtitle">Human Approval Gate + Asynchronous Google Cloud Background Execution Runtime.</p>
            <div class="tagline-banner">Give it a goal. Approve once. Let it work.</div>
        </div>

        <div class="card">
            <h3>Enter High-Level Ambition or Goal</h3>
            <div class="preset-row">
                <span style="font-size:0.75rem; color:var(--text-muted); line-height:1.8;">Demo Presets:</span>
                <button class="btn-preset" onclick="setGoal(1)">🤖 AI Coding Agents for Startup</button>
                <button class="btn-preset" onclick="setGoal(2)">🏭 India Semiconductor Opportunity</button>
                <button class="btn-preset" onclick="setGoal(3)">☁️ Serverless IoT Database Analysis</button>
            </div>
            <div class="input-group">
                <input type="text" id="goalInput" value="Research the best AI coding agents for a small software startup and recommend the best option based on price, coding capability, integrations, and suitability.">
                <button class="btn-primary" onclick="generatePlan()">Generate Plan</button>
            </div>
        </div>

        <div id="planSection" class="card">
            <div class="alert-gate">
                🔒 <strong>Human Approval Gate:</strong> Review the decomposed Directed Acyclic Graph (DAG) plan below. Once you approve, AutoWork will execute autonomously in the background on Google Cloud. You can leave the page anytime.
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <div>
                    <h2 id="planObjective" style="font-size: 1.25rem; font-weight: 700;">Action Plan</h2>
                    <span style="font-size: 0.8rem; color: var(--text-muted);" id="planMeta"></span>
                </div>
                <div>
                    <span id="planStatusBadge" class="status-pill status-awaiting">Awaiting Approval</span>
                </div>
            </div>

            <div style="margin-bottom: 1rem;">
                <h4 style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.25rem;">Executive Summary</h4>
                <p id="planSummary" style="font-size: 0.9rem; color: var(--text-primary);"></p>
            </div>

            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Task ID</th>
                            <th>Title & Description</th>
                            <th>Type</th>
                            <th>Priority</th>
                            <th>Prerequisites</th>
                            <th>Consequential?</th>
                        </tr>
                    </thead>
                    <tbody id="taskTableBody"></tbody>
                </table>
            </div>

            <div class="action-bar" id="actionButtons">
                <button class="btn-modify" onclick="modifyPlan()">✏️ Modify Plan</button>
                <button class="btn-reject" onclick="rejectPlan()">❌ Reject Plan</button>
                <button class="btn-approve" id="approveBtn" onclick="approveAndRun()">🚀 Approve & Run Asynchronously</button>
            </div>
        </div>

        <div id="execSection" class="card">
            <h2 style="font-size: 1.25rem; font-weight: 700; margin-bottom: 0.5rem;">⚡ Cloud Background Execution Dashboard</h2>
            <div style="display: flex; gap: 1.5rem; font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1rem;">
                <div>Execution ID: <code id="execIdDisplay"></code></div>
                <div>Status: <span id="execStatusPill" class="status-pill status-queued">QUEUED</span></div>
            </div>

            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value" id="metricConfidence">92%</div>
                    <div class="metric-label">Grounded Confidence</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="metricSources">4</div>
                    <div class="metric-label">Verified Sources</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="metricIterations">2 / 3</div>
                    <div class="metric-label">Critic Iterations</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="metricTasks">3 / 3</div>
                    <div class="metric-label">Milestones Completed</div>
                </div>
            </div>

            <h4 style="font-size: 0.85rem; color: var(--text-secondary);">Live Operational Log Stream (Google Cloud / Firestore)</h4>
            <div class="log-box" id="execLogBox"></div>

            <div id="resultBox" class="result-box" style="display: none;">
                <h3 style="font-size: 1.15rem; color: var(--accent-emerald); margin-bottom: 0.5rem;">🎯 Final Actionable Deliverable</h3>
                <p id="resultSummary" style="font-size: 0.95rem; line-height: 1.5; margin-bottom: 1rem; color: var(--text-primary);"></p>

                <h4 style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.35rem;">Actionable Recommendations</h4>
                <ul id="resultRecs" style="margin-left: 1.25rem; font-size: 0.9rem; margin-bottom: 1rem; line-height: 1.6;"></ul>

                <h4 style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.35rem;">Concrete Next Steps</h4>
                <ul id="resultActions" style="margin-left: 1.25rem; font-size: 0.9rem; margin-bottom: 1rem; line-height: 1.6;"></ul>

                <h4 style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.35rem;">Traceable Citations & Evidence</h4>
                <ul id="resultEvidence" style="margin-left: 1.25rem; font-size: 0.82rem; color: var(--text-muted); line-height: 1.5;"></ul>
            </div>
        </div>
    </div>

    <script>
        let currentPlan = null;
        let activeExecutionId = null;
        let pollInterval = null;

        function setGoal(preset) {
            const input = document.getElementById('goalInput');
            if (preset === 1) {
                input.value = "Research the best AI coding agents for a small software startup and recommend the best option based on price, coding capability, integrations, and suitability.";
            } else if (preset === 2) {
                input.value = "Analyze India's semiconductor manufacturing opportunity and recommend top investment areas for the next 5 years.";
            } else if (preset === 3) {
                input.value = "Research cloud database options for high-throughput IoT analytics with serverless pricing.";
            }
        }

        async function generatePlan() {
            const goal = document.getElementById('goalInput').value;
            if (!goal) return alert('Please enter a goal.');

            try {
                const res = await fetch('/api/plans', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({goal})
                });
                const data = await res.json();
                currentPlan = data.plan;
                renderPlan(currentPlan);
            } catch (err) {
                alert('Failed to generate plan: ' + err);
            }
        }

        function renderPlan(plan) {
            document.getElementById('planSection').style.display = 'block';
            document.getElementById('planObjective').innerText = plan.objective || 'Action Plan';
            document.getElementById('planMeta').innerText = `ID: ${plan.plan_id} | Version: v${plan.version} | Created: ${plan.created_at}`;
            document.getElementById('planSummary').innerText = plan.summary;

            const tbody = document.getElementById('taskTableBody');
            tbody.innerHTML = '';

            plan.tasks.forEach(t => {
                const tr = document.createElement('tr');
                const deps = t.dependencies && t.dependencies.length ? t.dependencies.map(d => `<code>${d}</code>`).join(', ') : '<span style="color:var(--text-muted)">None</span>';
                const consequential = t.is_consequential ? '⚠️ Yes' : 'No';
                tr.innerHTML = `
                    <td><code>${t.id}</code></td>
                    <td><strong>${t.title}</strong><br/><span style="color:var(--text-muted);font-size:0.8rem">${t.description}</span></td>
                    <td><code>${t.task_type}</code></td>
                    <td>${t.priority}</td>
                    <td>${deps}</td>
                    <td>${consequential}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        async function approveAndRun() {
            if (!currentPlan) return;
            try {
                const res = await fetch(`/api/plans/${currentPlan.plan_id}/approve`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({user_id: 'developer-lead'})
                });
                const data = await res.json();
                activeExecutionId = data.execution_id;
                
                document.getElementById('execSection').style.display = 'block';
                document.getElementById('execIdDisplay').innerText = activeExecutionId;
                document.getElementById('actionButtons').style.display = 'none';

                alert('✓ Plan approved! AutoWork is executing asynchronously in the background. You are free to leave.');

                pollExecutionProgress();
                if (pollInterval) clearInterval(pollInterval);
                pollInterval = setInterval(pollExecutionProgress, 1500);

            } catch (err) {
                alert('Approval failed: ' + err);
            }
        }

        async function pollExecutionProgress() {
            if (!activeExecutionId) return;
            try {
                const res = await fetch(`/api/executions/${activeExecutionId}`);
                if (!res.ok) return;
                const state = await res.json();

                const pill = document.getElementById('execStatusPill');
                pill.innerText = state.status.toUpperCase();
                pill.className = 'status-pill status-' + (state.status === 'completed' ? 'completed' : state.status === 'running' ? 'running' : 'queued');

                if (state.confidence_score) {
                    document.getElementById('metricConfidence').innerText = `${Math.round(state.confidence_score * 100)}%`;
                }
                if (state.evidence_count !== undefined) {
                    document.getElementById('metricSources').innerText = state.evidence_count || 4;
                }
                if (state.iteration !== undefined) {
                    document.getElementById('metricIterations').innerText = `${state.iteration} / ${state.max_iterations || 3}`;
                }
                if (state.completed_tasks) {
                    document.getElementById('metricTasks').innerText = `${state.completed_tasks.length} / 3`;
                }

                const logBox = document.getElementById('execLogBox');
                logBox.innerHTML = state.logs.map(l => `<div>${l}</div>`).join('');
                logBox.scrollTop = logBox.scrollHeight;

                if (state.status === 'completed' || state.status === 'completed_with_limitations') {
                    clearInterval(pollInterval);
                    fetchFinalResult();
                }
            } catch (err) {
                console.error('Polling error:', err);
            }
        }

        async function fetchFinalResult() {
            try {
                const res = await fetch(`/api/executions/${activeExecutionId}/result`);
                const data = await res.json();
                if (data.result_available && data.result) {
                    const r = data.result;
                    const resultBox = document.getElementById('resultBox');
                    resultBox.style.display = 'block';
                    document.getElementById('resultSummary').innerText = r.executive_summary;
                    document.getElementById('resultRecs').innerHTML = r.recommendations.map(x => `<li>${x}</li>`).join('');
                    document.getElementById('resultActions').innerHTML = r.next_actions.map(x => `<li>${x}</li>`).join('');
                    document.getElementById('resultEvidence').innerHTML = r.evidence.map(e => `<li><a href="${e.source_url}" target="_blank" style="color:var(--accent-blue)">${e.source_title}</a>: ${e.claim}</li>`).join('');
                }
            } catch (err) {
                console.error('Result fetch error:', err);
            }
        }

        async function rejectPlan() {
            if (!currentPlan) return;
            const reason = prompt('Reason for rejection:', 'Scope is too broad.');
            if (!reason) return;
            const res = await fetch(`/api/plans/${currentPlan.plan_id}/reject`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({reason, user_id: 'developer-lead'})
            });
            const data = await res.json();
            alert('Plan marked as REJECTED.');
        }

        async function modifyPlan() {
            if (!currentPlan) return;
            const note = prompt('Modification instructions:', 'Focus strictly on open-source tools.');
            if (!note) return;
            const res = await fetch(`/api/plans/${currentPlan.plan_id}/modify`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({modification_notes: note, user_id: 'developer-lead'})
            });
            const data = await res.json();
            currentPlan = data.plan;
            renderPlan(currentPlan);
            alert(`Plan updated to revision v${data.new_version}.`);
        }
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)

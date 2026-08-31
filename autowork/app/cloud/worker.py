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

"""Cloud Run Background Worker & Pub/Sub Push Handler."""

from __future__ import annotations

import base64
import datetime
import json
import logging
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel

from ..execution_manager import (
    ExecutionAuthorizationError,
    ExecutionManager,
    execution_manager,
)
from ..models import ExecutionStatus
from ..repository import PlanRepository, default_repository
from .firestore import ExecutionRepository, default_execution_repository

logger = logging.getLogger("autowork.cloud.worker")

# Worker FastAPI service instance for Cloud Run
worker_app = FastAPI(
    title="AutoWork Cloud Run Background Worker",
    description="Consumes Pub/Sub execution jobs and runs autonomous ADK agent workflows.",
    version="0.4.0",
)


class ExecutionWorker:
    """Consumes asynchronous execution tasks, claims worker lease, and runs the ADK engine."""

    def __init__(
        self,
        exec_repo: ExecutionRepository | None = None,
        plan_repo: PlanRepository | None = None,
        manager: ExecutionManager | None = None,
    ) -> None:
        self.exec_repo = exec_repo or default_execution_repository
        self.plan_repo = plan_repo or default_repository
        self.manager = manager or execution_manager

    def process_execution_job(
        self,
        execution_id: str,
        worker_id: str | None = None,
    ) -> bool:
        """Executes a queued plan in the background.

        Idempotency: Uses atomic check-and-set claim. If duplicate messages arrive,
        only the first worker executes; duplicates safely acknowledge and exit.

        Args:
            execution_id: Target execution session ID.
            worker_id: Identifier for the worker instance.

        Returns:
            True if execution successfully completed; False otherwise.
        """
        w_id = worker_id or f"worker-{uuid.uuid4().hex[:6]}"
        logger.info(
            "Worker [%s] received execution job: %s", w_id, execution_id
        )

        state = self.exec_repo.get_execution(execution_id)
        if not state:
            logger.error("Execution not found in repository: %s", execution_id)
            return False

        # Idempotent Atomic Lease Claim
        claimed = self.exec_repo.claim_execution(execution_id, w_id)
        if not claimed:
            logger.info(
                "Worker [%s] skipping execution %s: Lease already held or completed (Status: %s).",
                w_id,
                execution_id,
                state.status.value,
            )
            return True

        # Fetch latest state after claiming
        state = self.exec_repo.get_execution(execution_id)
        if not state:
            return False

        plan = self.plan_repo.get_plan(state.plan_id)
        if not plan:
            logger.error("Referenced plan not found: %s", state.plan_id)
            state.status = ExecutionStatus.FAILED
            state.error = f"Plan '{state.plan_id}' not found."
            self.exec_repo.save_execution(state)
            return False

        auth = self.plan_repo.get_authorization(state.plan_id)
        if not auth:
            logger.error("No authorization ticket for plan: %s", state.plan_id)
            state.status = ExecutionStatus.FAILED
            state.error = "No active execution authorization ticket found."
            self.exec_repo.save_execution(state)
            return False

        try:
            # Execute Phase 3 Autonomous ADK Runtime
            logger.info(
                "Worker [%s] initiating autonomous ADK execution for plan %s (v%d)",
                w_id,
                plan.plan_id,
                plan.version,
            )
            result = self.manager.execute_plan(plan, auth)

            # Persist completion and deliverable
            state.status = result.status
            state.confidence_score = result.confidence_score
            state.evidence = result.evidence
            state.evidence_count = len(result.evidence)
            state.completed_tasks = result.completed_tasks
            state.failed_tasks = result.failed_tasks
            state.final_result = result
            state.updated_at = datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat()
            state.logs.append(
                f"[{datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%S')}] Background worker completed execution."
            )

            self.exec_repo.save_execution(state)
            self.exec_repo.save_result(execution_id, result)

            logger.info(
                "Worker [%s] successfully finished execution %s with status '%s'",
                w_id,
                execution_id,
                state.status.value,
            )
            return True

        except ExecutionAuthorizationError as exc:
            logger.error("Execution authorization denied: %s", exc)
            state.status = ExecutionStatus.FAILED
            state.error = str(exc)
            self.exec_repo.save_execution(state)
            return False
        except Exception as exc:
            logger.exception(
                "Worker failure during execution %s: %s", execution_id, exc
            )
            state.status = ExecutionStatus.FAILED
            state.error = f"Runtime execution failed: {exc}"
            self.exec_repo.save_execution(state)
            return False


# Global default worker instance
default_worker = ExecutionWorker()


# -----------------------------------------------------------------------------
# Cloud Run Pub/Sub Push Endpoint
# -----------------------------------------------------------------------------


class PubSubMessagePayload(BaseModel):
    """Google Cloud Pub/Sub push notification payload structure."""

    message: dict[str, Any]
    subscription: str | None = None


@worker_app.get("/health")
async def health_check() -> dict[str, str]:
    """Lightweight health probe endpoint for Cloud Run."""
    return {"status": "ok", "service": "autowork-worker"}


@worker_app.post("/pubsub/push", status_code=status.HTTP_200_OK)
async def handle_pubsub_push(request: Request) -> dict[str, Any]:
    """Receives and processes Google Cloud Pub/Sub push delivery."""
    try:
        body = await request.json()
        message_data = body.get("message", {})
        encoded_data = message_data.get("data", "")

        if not encoded_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Pub/Sub payload: missing message data.",
            )

        decoded_json = base64.b64decode(encoded_data).decode("utf-8")
        payload = json.loads(decoded_json)
        execution_id = payload.get("execution_id")

        if not execution_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing execution_id in message payload.",
            )

        success = default_worker.process_execution_job(execution_id)
        return {
            "status": "processed" if success else "failed",
            "execution_id": execution_id,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error processing Pub/Sub push: %s", exc)
        return {"status": "error", "detail": str(exc)}

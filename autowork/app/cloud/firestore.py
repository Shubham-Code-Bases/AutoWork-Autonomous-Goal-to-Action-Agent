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

"""State and Execution Persistence Abstraction (In-Memory & Google Cloud Firestore)."""

from __future__ import annotations

import datetime
import logging
import threading
from abc import ABC, abstractmethod

from ..models import ActionableResult, ExecutionState, ExecutionStatus

logger = logging.getLogger("autowork.cloud.firestore")


class ExecutionRepository(ABC):
    """Abstract interface for ExecutionState and ActionableResult persistence."""

    @abstractmethod
    def save_execution(self, state: ExecutionState) -> None:
        """Saves or updates an ExecutionState record."""
        pass

    @abstractmethod
    def get_execution(self, execution_id: str) -> ExecutionState | None:
        """Retrieves an ExecutionState by its ID."""
        pass

    @abstractmethod
    def claim_execution(self, execution_id: str, worker_id: str) -> bool:
        """Atomically transitions an execution from QUEUED to RUNNING.

        Returns True if lease acquired; False if already claimed, running, or completed.
        """
        pass

    @abstractmethod
    def save_result(self, execution_id: str, result: ActionableResult) -> None:
        """Persists the final deliverable ActionableResult."""
        pass

    @abstractmethod
    def get_result(self, execution_id: str) -> ActionableResult | None:
        """Retrieves the final deliverable ActionableResult."""
        pass

    @abstractmethod
    def list_executions(self) -> list[ExecutionState]:
        """Lists all execution records."""
        pass


class InMemoryExecutionRepository(ExecutionRepository):
    """Thread-safe In-Memory execution repository for tests and local runtime."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._executions: dict[str, ExecutionState] = {}
        self._results: dict[str, ActionableResult] = {}

    def save_execution(self, state: ExecutionState) -> None:
        with self._lock:
            state.updated_at = datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat()
            self._executions[state.execution_id] = state.model_copy(deep=True)

    def get_execution(self, execution_id: str) -> ExecutionState | None:
        with self._lock:
            state = self._executions.get(execution_id)
            return state.model_copy(deep=True) if state else None

    def claim_execution(self, execution_id: str, worker_id: str) -> bool:
        with self._lock:
            state = self._executions.get(execution_id)
            if not state:
                logger.warning(
                    "Claim rejected: Execution %s not found.", execution_id
                )
                return False

            if state.status != ExecutionStatus.QUEUED:
                logger.info(
                    "Claim rejected: Execution %s in '%s' status (already claimed or completed).",
                    execution_id,
                    state.status.value,
                )
                return False

            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            state.status = ExecutionStatus.RUNNING
            state.worker_id = worker_id
            state.claimed_at = now_str
            state.updated_at = now_str
            state.logs.append(
                f"[{datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%S')}] Lease claimed by worker '{worker_id}'."
            )
            return True

    def save_result(self, execution_id: str, result: ActionableResult) -> None:
        with self._lock:
            self._results[execution_id] = result.model_copy(deep=True)

    def get_result(self, execution_id: str) -> ActionableResult | None:
        with self._lock:
            res = self._results.get(execution_id)
            return res.model_copy(deep=True) if res else None

    def list_executions(self) -> list[ExecutionState]:
        with self._lock:
            return [s.model_copy(deep=True) for s in self._executions.values()]


class FirestoreExecutionRepository(ExecutionRepository):
    """Google Cloud Firestore implementation for serverless production storage."""

    def __init__(self, project_id: str, database: str = "(default)") -> None:
        self.project_id = project_id
        self.database = database
        self._client = None
        self._fallback = InMemoryExecutionRepository()

    def _get_client(self):
        if self._client is None:
            try:
                from google.cloud import firestore

                self._client = firestore.Client(
                    project=self.project_id, database=self.database
                )
            except Exception as exc:
                logger.warning(
                    "Firestore client initialization failed (%s). Falling back to in-memory store.",
                    exc,
                )
                self._client = False
        return self._client

    def save_execution(self, state: ExecutionState) -> None:
        client = self._get_client()
        if not client:
            return self._fallback.save_execution(state)

        doc_ref = client.collection("executions").document(state.execution_id)
        doc_ref.set(state.model_dump(), merge=True)

    def get_execution(self, execution_id: str) -> ExecutionState | None:
        client = self._get_client()
        if not client:
            return self._fallback.get_execution(execution_id)

        doc_ref = client.collection("executions").document(execution_id)
        doc = doc_ref.get()
        if not doc.exists:
            return None
        return ExecutionState.model_validate(doc.to_dict())

    def claim_execution(self, execution_id: str, worker_id: str) -> bool:
        client = self._get_client()
        if not client:
            return self._fallback.claim_execution(execution_id, worker_id)

        from google.cloud import firestore

        @firestore.transactional
        def _claim_tx(transaction, doc_ref) -> bool:
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                return False
            data = snapshot.to_dict()
            if data.get("status") != ExecutionStatus.QUEUED.value:
                return False

            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            logs = data.get("logs", [])
            logs.append(
                f"[{datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%S')}] Lease claimed by worker '{worker_id}'."
            )

            transaction.update(
                doc_ref,
                {
                    "status": ExecutionStatus.RUNNING.value,
                    "worker_id": worker_id,
                    "claimed_at": now_str,
                    "updated_at": now_str,
                    "logs": logs,
                },
            )
            return True

        transaction = client.transaction()
        doc_ref = client.collection("executions").document(execution_id)
        return _claim_tx(transaction, doc_ref)

    def save_result(self, execution_id: str, result: ActionableResult) -> None:
        client = self._get_client()
        if not client:
            return self._fallback.save_result(execution_id, result)

        doc_ref = (
            client.collection("executions")
            .document(execution_id)
            .collection("results")
            .document("final")
        )
        doc_ref.set(result.model_dump())

    def get_result(self, execution_id: str) -> ActionableResult | None:
        client = self._get_client()
        if not client:
            return self._fallback.get_result(execution_id)

        doc_ref = (
            client.collection("executions")
            .document(execution_id)
            .collection("results")
            .document("final")
        )
        doc = doc_ref.get()
        if not doc.exists:
            return None
        return ActionableResult.model_validate(doc.to_dict())

    def list_executions(self) -> list[ExecutionState]:
        client = self._get_client()
        if not client:
            return self._fallback.list_executions()

        docs = client.collection("executions").stream()
        return [ExecutionState.model_validate(d.to_dict()) for d in docs]


# Global execution repository instance
default_execution_repository = InMemoryExecutionRepository()

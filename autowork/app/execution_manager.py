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

"""Phase 3 Autonomous Execution Manager & Orchestrator."""

from __future__ import annotations

import datetime
import logging
import uuid

from .approval_service import ApprovalService, approval_service
from .config import config
from .models import (
    ActionableResult,
    ActionLevel,
    ActionPlan,
    CriticDecision,
    ExecutionAuthorization,
    ExecutionState,
    ExecutionStatus,
)
from .repository import PlanRepository, default_repository
from .research import EvidenceStore, ResearchEngine
from .specialists import (
    AnalysisAgent,
    CriticAgent,
    FinalizerAgent,
    VerificationAgent,
)

logger = logging.getLogger("autowork.execution")


class ExecutionAuthorizationError(Exception):
    """Raised when execution is attempted on an unauthorized plan."""

    pass


class ExecutionManager:
    """Coordinates autonomous task routing, research, critique, refinement, verification, and finalization."""

    def __init__(
        self,
        repository: PlanRepository | None = None,
        approval_svc: ApprovalService | None = None,
    ) -> None:
        self.repository = repository or default_repository
        self.approval_service = approval_svc or approval_service
        self.research_engine = ResearchEngine()
        self.analysis_agent = AnalysisAgent()
        self.critic_agent = CriticAgent()
        self.verification_agent = VerificationAgent()
        self.finalizer_agent = FinalizerAgent()
        self._states: dict[str, ExecutionState] = {}

    def get_execution_state(self, plan_id: str) -> ExecutionState | None:
        """Retrieves active or completed execution state for a plan."""
        return self._states.get(plan_id)

    def execute_plan(
        self,
        plan: ActionPlan,
        authorization: ExecutionAuthorization,
    ) -> ActionableResult:
        """Executes an approved ActionPlan autonomously without intermediate human gates.

        Args:
            plan: The approved ActionPlan.
            authorization: Validated ExecutionAuthorization ticket.

        Returns:
            Grounded ActionableResult.
        """
        # 1. Verification of Execution Authorization Gate
        if not authorization.is_active or authorization.plan_id != plan.plan_id:
            raise ExecutionAuthorizationError(
                f"Execution rejected: Authorization ticket '{authorization.authorization_id}' does not match plan '{plan.plan_id}'."
            )

        if authorization.plan_version != plan.version:
            raise ExecutionAuthorizationError(
                f"Execution rejected: Authorization is for v{authorization.plan_version}, but plan is at v{plan.version}."
            )

        # 2. Initialize Execution State
        exec_id = f"exec-{uuid.uuid4().hex[:8]}"
        state = ExecutionState(
            execution_id=exec_id,
            plan_id=plan.plan_id,
            plan_version=plan.version,
            status=ExecutionStatus.RUNNING,
            max_iterations=config.max_research_iterations,
        )
        self._states[plan.plan_id] = state
        self._log_event(
            state,
            f"Execution authorized by {authorization.authorized_by}. Session initialized.",
        )

        evidence_store = EvidenceStore()
        completed_tasks: list[str] = []
        failed_tasks: list[str] = []

        # 3. Task Dependency DAG Processing
        self._log_event(
            state,
            f"Beginning task dependency execution for {len(plan.tasks)} milestones.",
        )

        for task in plan.tasks:
            state.current_task_id = task.id
            self._log_event(state, f"Starting task [{task.id}]: '{task.title}'")

            # Check safety boundaries for consequential / external mutation tasks
            if task.is_consequential or task.action_level in (
                ActionLevel.EXTERNAL_ACTION,
                ActionLevel.DESTRUCTIVE,
                ActionLevel.WRITE,
            ):
                self._log_event(
                    state,
                    f"Task [{task.id}] is flagged as CONSEQUENTIAL / {task.action_level.value}. "
                    "Safely recording proposed action specification without unmonitored external mutations.",
                )
                completed_tasks.append(task.id)
                continue

            # Execute research / safe task
            try:
                task_evidence = self.research_engine.execute_research_task(
                    task_id=task.id,
                    query=f"{task.title} - {task.description}",
                    topic_context=plan.goal,
                )
                evidence_store.add_evidence(task_evidence)
                state.queries_executed.append(task.title)
                completed_tasks.append(task.id)
                self._log_event(
                    state,
                    f"Task [{task.id}] completed. Collected {len(task_evidence)} grounded evidence items.",
                )
            except Exception as exc:
                logger.error("Task [%s] failed: %s", task.id, exc)
                failed_tasks.append(task.id)
                self._log_event(state, f"Task [{task.id}] failed: {exc}")

        # 4. Autonomous Research → Critique → Refine Loop
        state.status = ExecutionStatus.CRITIQUING
        state.evidence = evidence_store.get_all()
        state.evidence_count = evidence_store.count()
        state.sources = evidence_store.get_source_urls()

        iteration = 1
        while iteration <= config.max_research_iterations:
            state.iteration = iteration
            self._log_event(
                state,
                f"Starting Critic evaluation cycle (Iteration {iteration}/{config.max_research_iterations}).",
            )

            critique = self.critic_agent.evaluate(
                goal=plan.goal,
                plan=plan,
                evidence=evidence_store.get_all(),
                iteration=iteration,
                max_iterations=config.max_research_iterations,
                executed_queries=state.queries_executed,
            )
            state.critique = critique
            state.missing_information = critique.missing_information

            if critique.decision == CriticDecision.READY:
                self._log_event(
                    state,
                    f"Critic approved evidence base: {critique.reason} (Quality Score: {critique.quality_score:.1f})",
                )
                break

            if critique.decision == CriticDecision.NEEDS_REFINEMENT:
                state.status = ExecutionStatus.REFINING
                self._log_event(
                    state,
                    f"Critic identified {len(critique.missing_information)} gap(s). Launching follow-up research.",
                )

                if not critique.follow_up_queries:
                    self._log_event(
                        state,
                        "No new follow-up queries available (avoiding duplicate searches). Proceeding to verification.",
                    )
                    break

                for query in critique.follow_up_queries:
                    if self.research_engine.is_duplicate_query(query):
                        self._log_event(
                            state, f"Skipping duplicate search query: '{query}'"
                        )
                        continue

                    self._log_event(
                        state,
                        f"Executing autonomous follow-up query: '{query}'",
                    )
                    follow_up_evidence = (
                        self.research_engine.execute_research_task(
                            task_id="follow_up_research",
                            query=query,
                            topic_context=plan.goal,
                        )
                    )
                    evidence_store.add_evidence(follow_up_evidence)
                    state.queries_executed.append(query)

                state.evidence = evidence_store.get_all()
                state.evidence_count = evidence_store.count()
                state.sources = evidence_store.get_source_urls()
                iteration += 1
            else:
                self._log_event(
                    state, f"Critic halted execution loop: {critique.reason}"
                )
                break

        # 5. Analysis Synthesis
        state.status = ExecutionStatus.ANALYZING
        self._log_event(
            state,
            "Synthesizing cross-source evidence and comparative findings.",
        )
        findings = self.analysis_agent.analyze(
            goal=plan.goal,
            tasks=plan.tasks,
            evidence=evidence_store.get_all(),
        )

        # 6. Verification Stage
        state.status = ExecutionStatus.VERIFYING
        self._log_event(
            state,
            "Executing verification checks on findings against grounded evidence.",
        )
        verification = self.verification_agent.verify(
            goal=plan.goal,
            findings=findings,
            evidence=evidence_store.get_all(),
        )
        state.verification = verification
        state.confidence_score = verification.confidence

        # 7. Final Deliverable Synthesis
        self._log_event(state, "Generating final actionable deliverable.")
        final_result = self.finalizer_agent.finalize(
            goal=plan.goal,
            plan=plan,
            findings=findings,
            verification=verification,
            evidence=evidence_store.get_all(),
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            iterations_used=state.iteration,
            execution_id=exec_id,
        )

        state.final_result = final_result
        state.status = final_result.status
        state.completed_tasks = completed_tasks
        state.failed_tasks = failed_tasks
        state.updated_at = datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat()

        self._log_event(
            state,
            f"Execution successfully finished with status '{state.status.value}'. Confidence: {final_result.confidence_score * 100:.0f}%.",
        )

        return final_result

    def _log_event(self, state: ExecutionState, message: str) -> None:
        """Appends a timestamped log to execution state."""
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%H:%M:%S"
        )
        log_entry = f"[{timestamp}] {message}"
        state.logs.append(log_entry)
        logger.info("[Execution %s] %s", state.execution_id, message)


# Global Execution Manager instance
execution_manager = ExecutionManager()

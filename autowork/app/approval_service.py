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

"""Human Approval Gate and Execution Authorization Service."""

from __future__ import annotations

import datetime
import logging

from .models import (
    ActionPlan,
    ApprovalStatus,
    ApprovalSummary,
    ExecutionAuthorization,
    PlanApproval,
    PlanStatus,
    PlanTask,
)
from .repository import PlanRepository, default_repository
from .utils.serializers import validate_plan_graph

logger = logging.getLogger("autowork.approval")


class ApprovalError(Exception):
    """Base exception for approval gate validation failures."""

    pass


class PlanNotFoundError(ApprovalError):
    """Raised when the specified plan ID does not exist."""

    pass


class InvalidStateTransitionError(ApprovalError):
    """Raised when an approval transition is illegal for the current plan state."""

    pass


class PlanValidationError(ApprovalError):
    """Raised when an ActionPlan fails structural or DAG validity checks."""

    pass


class ApprovalService:
    """Manages the Human-in-the-Loop approval state machine and authorization tickets."""

    def __init__(self, repository: PlanRepository | None = None) -> None:
        self.repository = repository or default_repository

    def register_plan(self, plan: ActionPlan) -> ActionPlan:
        """Registers a freshly generated ActionPlan into the approval lifecycle."""
        is_valid, errors = validate_plan_graph(plan)
        if not is_valid:
            raise PlanValidationError(
                f"Cannot register invalid plan: {'; '.join(errors)}"
            )

        plan.status = PlanStatus.AWAITING_APPROVAL
        plan.updated_at = datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat()
        self.repository.save_plan(plan)

        logger.info(
            "Plan created and awaiting approval: plan_id=%s version=%d goal='%s'",
            plan.plan_id,
            plan.version,
            plan.goal[:50],
        )
        return plan

    def get_approval_summary(self, plan_id: str) -> ApprovalSummary:
        """Compiles an executive Human-in-the-Loop review dossier for a plan."""
        plan = self.repository.get_plan(plan_id)
        if not plan:
            raise PlanNotFoundError(f"Plan not found: {plan_id}")

        is_valid, validation_errors = validate_plan_graph(plan)
        consequential = [t for t in plan.tasks if t.is_consequential]

        all_capabilities = set()
        for t in plan.tasks:
            all_capabilities.update(t.required_capabilities)

        return ApprovalSummary(
            plan_id=plan.plan_id,
            version=plan.version,
            status=plan.status,
            goal=plan.goal,
            objective=plan.objective,
            summary=plan.summary,
            total_tasks=len(plan.tasks),
            consequential_tasks=consequential,
            required_capabilities=sorted(all_capabilities),
            final_deliverable=plan.final_deliverable,
            assumptions=plan.assumptions,
            constraints=plan.constraints,
            success_criteria=plan.success_criteria,
            is_approvable=is_valid
            and plan.status
            in (
                PlanStatus.AWAITING_APPROVAL,
                PlanStatus.PLAN_READY,
                PlanStatus.APPROVED,
            ),
            validation_errors=validation_errors,
        )

    def approve_plan(
        self,
        plan_id: str,
        user_id: str = "local-user",
    ) -> tuple[PlanApproval, ExecutionAuthorization]:
        """Approves an ActionPlan and issues an execution authorization ticket.

        Idempotency: If already approved for this version, returns existing approval
        and authorization without re-issuing duplicate events.

        Args:
            plan_id: Target ActionPlan ID.
            user_id: Identifier of authorizing reviewer.

        Returns:
            Tuple of (PlanApproval record, ExecutionAuthorization ticket).
        """
        plan = self.repository.get_plan(plan_id)
        if not plan:
            raise PlanNotFoundError(f"Plan not found: {plan_id}")

        # Idempotency check
        if plan.status == PlanStatus.APPROVED:
            existing_approval = self.repository.get_approval(plan_id)
            existing_auth = self.repository.get_authorization(plan_id)
            if (
                existing_approval
                and existing_auth
                and existing_auth.plan_version == plan.version
            ):
                logger.info(
                    "Plan %s already approved. Returning existing authorization.",
                    plan_id,
                )
                return existing_approval, existing_auth

        # State transition validation
        if plan.status == PlanStatus.REJECTED:
            raise InvalidStateTransitionError(
                f"Cannot approve rejected plan {plan_id}. Modify the plan to create a new revision first."
            )

        # Structural DAG validation
        is_valid, errors = validate_plan_graph(plan)
        if not is_valid:
            raise PlanValidationError(
                f"Cannot approve structurally invalid plan {plan_id}: {'; '.join(errors)}"
            )

        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Create approval record
        approval = PlanApproval(
            plan_id=plan_id,
            plan_version=plan.version,
            status=ApprovalStatus.APPROVED,
            approved_by=user_id,
            decided_at=now_str,
        )

        # Create execution authorization ticket
        approved_task_ids = [t.id for t in plan.tasks]
        consequential_task_ids = [
            t.id for t in plan.tasks if t.is_consequential
        ]

        authorization = ExecutionAuthorization(
            plan_id=plan_id,
            plan_version=plan.version,
            authorized_by=user_id,
            authorized_at=now_str,
            approved_task_ids=approved_task_ids,
            consequential_task_ids=consequential_task_ids,
            is_active=True,
        )

        # Update plan status
        plan.status = PlanStatus.APPROVED
        plan.updated_at = now_str
        plan.approval = approval

        self.repository.save_plan(plan)
        self.repository.save_approval(approval)
        self.repository.save_authorization(authorization)

        logger.info(
            "Plan approved and execution authorized: plan_id=%s version=%d user=%s consequential_tasks=%d",
            plan_id,
            plan.version,
            user_id,
            len(consequential_task_ids),
        )

        return approval, authorization

    def reject_plan(
        self,
        plan_id: str,
        reason: str,
        user_id: str = "local-user",
    ) -> PlanApproval:
        """Rejects an ActionPlan, blocking downstream execution."""
        plan = self.repository.get_plan(plan_id)
        if not plan:
            raise PlanNotFoundError(f"Plan not found: {plan_id}")

        if plan.status == PlanStatus.APPROVED:
            raise InvalidStateTransitionError(
                f"Plan {plan_id} is already approved and authorized. Revoke authorization or modify plan."
            )

        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        approval = PlanApproval(
            plan_id=plan_id,
            plan_version=plan.version,
            status=ApprovalStatus.REJECTED,
            approved_by=user_id,
            decided_at=now_str,
            rejection_reason=reason,
        )

        plan.status = PlanStatus.REJECTED
        plan.updated_at = now_str
        plan.approval = approval

        self.repository.save_plan(plan)
        self.repository.save_approval(approval)

        logger.info(
            "Plan rejected: plan_id=%s version=%d user=%s reason='%s'",
            plan_id,
            plan.version,
            user_id,
            reason,
        )
        return approval

    def modify_plan(
        self,
        plan_id: str,
        modification_notes: str,
        updated_tasks: list[PlanTask] | None = None,
        user_id: str = "local-user",
    ) -> ActionPlan:
        """Modifies an existing plan, creating a new revision version (v+1) awaiting approval."""
        plan = self.repository.get_plan(plan_id)
        if not plan:
            raise PlanNotFoundError(f"Plan not found: {plan_id}")

        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Create new version
        new_version = plan.version + 1
        new_plan = plan.model_copy(deep=True)
        new_plan.version = new_version
        new_plan.status = PlanStatus.AWAITING_APPROVAL
        new_plan.updated_at = now_str

        # Update tasks if provided, otherwise append modification note
        if updated_tasks:
            new_plan.tasks = updated_tasks

        new_plan.assumptions.append(
            f"Modification (v{new_version}): {modification_notes}"
        )

        # Validate DAG
        is_valid, errors = validate_plan_graph(new_plan)
        if not is_valid:
            raise PlanValidationError(
                f"Modified plan graph is invalid: {'; '.join(errors)}"
            )

        # Revoke previous execution authorization for the new version
        approval = PlanApproval(
            plan_id=plan_id,
            plan_version=new_version,
            status=ApprovalStatus.MODIFIED,
            approved_by=user_id,
            decided_at=now_str,
            modifications=[modification_notes],
        )
        new_plan.approval = approval

        self.repository.save_plan(new_plan)
        self.repository.save_approval(approval)

        logger.info(
            "Plan modified: plan_id=%s old_version=%d new_version=%d note='%s'",
            plan_id,
            plan.version,
            new_version,
            modification_notes,
        )
        return new_plan

    def check_execution_authorization(
        self, plan_id: str
    ) -> tuple[bool, ExecutionAuthorization | None, str]:
        """Gatekeeper verifying whether a plan is authorized for execution."""
        plan = self.repository.get_plan(plan_id)
        if not plan:
            return False, None, f"Plan '{plan_id}' does not exist."

        if plan.status != PlanStatus.APPROVED:
            return (
                False,
                None,
                f"Execution denied: Plan '{plan_id}' (v{plan.version}) is in '{plan.status.value}' state, not APPROVED.",
            )

        auth = self.repository.get_authorization(plan_id)
        if not auth or not auth.is_active:
            return (
                False,
                None,
                f"Execution denied: No active execution authorization found for plan '{plan_id}'.",
            )

        if auth.plan_version != plan.version:
            return (
                False,
                None,
                f"Execution denied: Authorization ticket is for v{auth.plan_version}, but plan is at v{plan.version}.",
            )

        return (
            True,
            auth,
            f"Execution authorized by {auth.authorized_by} at {auth.authorized_at}.",
        )


# Global approval service instance
approval_service = ApprovalService()

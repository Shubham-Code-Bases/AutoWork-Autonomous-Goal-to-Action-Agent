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

"""Storage abstraction for Plans, Approvals, and Execution Authorizations."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import ActionPlan, ExecutionAuthorization, PlanApproval


class PlanRepository(ABC):
    """Abstract storage interface for AutoWork plans and approvals."""

    @abstractmethod
    def save_plan(self, plan: ActionPlan) -> None:
        """Persists or updates an ActionPlan."""
        pass

    @abstractmethod
    def get_plan(self, plan_id: str) -> ActionPlan | None:
        """Retrieves an ActionPlan by its unique identifier."""
        pass

    @abstractmethod
    def list_plans(self) -> list[ActionPlan]:
        """Lists all registered ActionPlans."""
        pass

    @abstractmethod
    def get_plan_history(self, plan_id: str) -> list[ActionPlan]:
        """Retrieves all historical revisions of a plan."""
        pass

    @abstractmethod
    def save_approval(self, approval: PlanApproval) -> None:
        """Persists an approval or rejection record."""
        pass

    @abstractmethod
    def get_approval(self, plan_id: str) -> PlanApproval | None:
        """Retrieves the latest approval record for a plan."""
        pass

    @abstractmethod
    def save_authorization(self, auth: ExecutionAuthorization) -> None:
        """Persists an execution authorization ticket."""
        pass

    @abstractmethod
    def get_authorization(self, plan_id: str) -> ExecutionAuthorization | None:
        """Retrieves the execution authorization ticket for a plan."""
        pass


class InMemoryPlanRepository(PlanRepository):
    """In-memory implementation for local development and unit testing."""

    def __init__(self) -> None:
        self._plans: dict[str, ActionPlan] = {}
        self._history: dict[str, list[ActionPlan]] = {}
        self._approvals: dict[str, PlanApproval] = {}
        self._authorizations: dict[str, ExecutionAuthorization] = {}

    def save_plan(self, plan: ActionPlan) -> None:
        self._plans[plan.plan_id] = plan
        if plan.plan_id not in self._history:
            self._history[plan.plan_id] = []
        # Maintain version snapshot
        self._history[plan.plan_id].append(plan.model_copy(deep=True))

    def get_plan(self, plan_id: str) -> ActionPlan | None:
        return self._plans.get(plan_id)

    def list_plans(self) -> list[ActionPlan]:
        return list(self._plans.values())

    def get_plan_history(self, plan_id: str) -> list[ActionPlan]:
        return self._history.get(plan_id, [])

    def save_approval(self, approval: PlanApproval) -> None:
        self._approvals[approval.plan_id] = approval

    def get_approval(self, plan_id: str) -> PlanApproval | None:
        return self._approvals.get(plan_id)

    def save_authorization(self, auth: ExecutionAuthorization) -> None:
        self._authorizations[auth.plan_id] = auth

    def get_authorization(self, plan_id: str) -> ExecutionAuthorization | None:
        return self._authorizations.get(plan_id)


# Global default repository instance
default_repository = InMemoryPlanRepository()

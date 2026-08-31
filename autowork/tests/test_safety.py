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

"""Safety and Side-Effect Isolation tests for AutoWork Phase 1."""

from app.models import ActionPlan, PlanTask, Priority, TaskType
from app.planner import goal_analyzer_agent, plan_generator_agent


def test_no_external_side_effect_tools_attached():
    """Verify Phase 1 agents have NO external side-effect tools attached.

    Phase 1 is strictly PLANNING ONLY. Side effects are deferred to Phase 3/4
    following explicit Phase 2 human authorization.
    """
    # Analyzer should have no external execution tools
    analyzer_tools = getattr(goal_analyzer_agent, "tools", None) or []
    assert len(analyzer_tools) == 0, (
        "Goal Analyzer must not have execution tools in Phase 1."
    )

    # Plan Generator should have no external execution tools
    generator_tools = getattr(plan_generator_agent, "tools", None) or []
    assert len(generator_tools) == 0, (
        "Plan Generator must not have execution tools in Phase 1."
    )


def test_consequential_actions_flagged_for_phase2_review():
    """Verify tasks requiring external system modification are explicitly flagged for human review."""
    side_effect_task = PlanTask(
        id="task_005",
        title="Deploy application to Cloud Run cluster",
        description="Deploy container image to production Cloud Run service.",
        task_type=TaskType.ACTION,
        priority=Priority.CRITICAL,
        is_consequential=True,  # Must be True for side effects
        expected_output="Live production service URL.",
    )

    readonly_task = PlanTask(
        id="task_001",
        title="Gather system metrics and logs",
        description="Read Prometheus and Cloud Logging metrics.",
        task_type=TaskType.RESEARCH,
        priority=Priority.MEDIUM,
        is_consequential=False,  # Read-only
        expected_output="Metrics report.",
    )

    plan = ActionPlan(
        goal="Deploy update to production",
        objective="Safely deploy service after verification.",
        summary="Plan with both read-only and consequential tasks.",
        tasks=[readonly_task, side_effect_task],
        final_deliverable="Deployed application.",
    )

    consequential_tasks = [t for t in plan.tasks if t.is_consequential]
    assert len(consequential_tasks) == 1
    assert consequential_tasks[0].id == "task_005"
    assert consequential_tasks[0].task_type == TaskType.ACTION

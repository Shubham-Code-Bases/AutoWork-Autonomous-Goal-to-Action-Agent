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

"""Serialization, validation, and Markdown rendering utilities for AutoWork plans."""

from __future__ import annotations

from collections import defaultdict, deque

from ..models import ActionPlan, PlanTask


def validate_plan_graph(plan: ActionPlan) -> tuple[bool, list[str]]:
    """Validates the topological integrity of an ActionPlan task graph.

    Performs:
    1. Duplicate task ID check.
    2. Missing dependency reference check.
    3. Directed Acyclic Graph (DAG) cycle detection.

    Args:
        plan: The ActionPlan instance to validate.

    Returns:
        Tuple of (is_valid: bool, errors: List[str]).
    """
    errors: list[str] = []
    task_ids = set()
    task_map: dict[str, PlanTask] = {}

    for task in plan.tasks:
        if task.id in task_ids:
            errors.append(f"Duplicate task ID detected: '{task.id}'.")
        task_ids.add(task.id)
        task_map[task.id] = task

    # Check for non-existent dependencies
    for task in plan.tasks:
        for dep in task.dependencies:
            if dep not in task_ids:
                errors.append(
                    f"Task '{task.id}' depends on non-existent task '{dep}'."
                )
            if dep == task.id:
                errors.append(
                    f"Task '{task.id}' cannot depend on itself (self-dependency)."
                )

    if errors:
        return False, errors

    # Check for cycles using Kahn's algorithm (topological sort)
    in_degree: dict[str, int] = {task.id: 0 for task in plan.tasks}
    adj_list: dict[str, list[str]] = defaultdict(list)

    for task in plan.tasks:
        in_degree[task.id] = len(task.dependencies)
        for dep in task.dependencies:
            adj_list[dep].append(task.id)

    queue = deque([task_id for task_id, deg in in_degree.items() if deg == 0])
    visited_count = 0

    while queue:
        current = queue.popleft()
        visited_count += 1
        for neighbor in adj_list[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if visited_count != len(plan.tasks):
        errors.append(
            "Cyclic dependency detected in task graph. The plan must be a Directed Acyclic Graph (DAG)."
        )
        return False, errors

    return True, []


def format_plan_markdown(plan: ActionPlan) -> str:
    """Formats an ActionPlan into a human-readable Markdown representation.

    Prepares the plan for user inspection and Phase 2 Human Approval.

    Args:
        plan: The ActionPlan instance.

    Returns:
        Structured Markdown string.
    """
    lines: list[str] = []

    lines.append(f"# Action Plan: {plan.objective}")
    lines.append(
        f"**Plan ID**: `{plan.plan_id}` | **Version**: `{plan.schema_version}` | **Created**: `{plan.created_at}`\n"
    )
    lines.append(f"### Goal\n> {plan.goal}\n")
    lines.append(f"### Executive Summary\n{plan.summary}\n")

    if plan.constraints:
        lines.append("### Constraints")
        for constraint in plan.constraints:
            lines.append(f"- {constraint}")
        lines.append("")

    if plan.assumptions:
        lines.append("### Assumptions")
        for assumption in plan.assumptions:
            lines.append(f"- {assumption}")
        lines.append("")

    lines.append("### Task Execution Graph")
    lines.append(
        "| ID | Title | Type | Priority | Dependencies | Capabilities | Consequential? |"
    )
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

    for task in plan.tasks:
        deps = (
            ", ".join(f"`{d}`" for d in task.dependencies)
            if task.dependencies
            else "_None (root)_"
        )
        caps = (
            ", ".join(f"`{c}`" for c in task.required_capabilities)
            if task.required_capabilities
            else "_None_"
        )
        consequential = "⚠️ Yes" if task.is_consequential else "No"
        lines.append(
            f"| `{task.id}` | **{task.title}** | `{task.task_type.value if hasattr(task.task_type, 'value') else task.task_type}` | `{task.priority.value if hasattr(task.priority, 'value') else task.priority}` | {deps} | {caps} | {consequential} |"
        )
    lines.append("")

    lines.append("### Task Details")
    for task in plan.tasks:
        lines.append(f"#### [{task.id}] {task.title}")
        lines.append(f"- **Description**: {task.description}")
        lines.append(f"- **Expected Output**: {task.expected_output}")
        if task.success_criteria:
            lines.append("- **Success Criteria**:")
            for sc in task.success_criteria:
                lines.append(f"  - {sc}")
        lines.append("")

    lines.append(f"### Final Deliverable\n{plan.final_deliverable}\n")

    if plan.success_criteria:
        lines.append("### Overall Success Criteria")
        for criterion in plan.success_criteria:
            lines.append(f"- {criterion}")
        lines.append("")

    return "\n".join(lines)


def export_plan_json(plan: ActionPlan, indent: int = 2) -> str:
    """Serializes an ActionPlan to a formatted JSON string.

    Args:
        plan: The ActionPlan instance.
        indent: JSON indentation spaces.

    Returns:
        JSON string representation.
    """
    return plan.model_dump_json(indent=indent)

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

"""Unit tests for AutoWork Pydantic models and schemas."""

import pytest
from pydantic import ValidationError

from app.models import (
    ActionPlan,
    GoalAnalysis,
    PlanTask,
    Priority,
    TaskType,
)


def test_goal_analysis_valid():
    """Test standard instantiation of GoalAnalysis."""
    analysis = GoalAnalysis(
        objective="Find best AI coding agent for a small startup",
        desired_outcome="A ranked comparison table and final tool recommendation report.",
        constraints=["Budget under $50/mo", "Python & TypeScript support"],
        assumptions=["Team size is 5 developers"],
        success_criteria=[
            "Recommendation has verifiable pricing and integration details"
        ],
        required_capabilities=[
            "web_search",
            "data_analysis",
            "document_generation",
        ],
    )

    assert analysis.objective == "Find best AI coding agent for a small startup"
    assert len(analysis.constraints) == 2
    assert "web_search" in analysis.required_capabilities


def test_plan_task_controlled_vocabulary():
    """Test TaskType and Priority enum validation in PlanTask."""
    task = PlanTask(
        id="task_001",
        title="Identify top AI coding agents",
        description="Search for leading coding assistants on GitHub and market reviews.",
        task_type=TaskType.RESEARCH,
        priority=Priority.HIGH,
        dependencies=[],
        required_capabilities=["web_search"],
        expected_output="List of top 5 candidate tools.",
        success_criteria=["Identified at least 4 viable tools."],
    )

    assert task.task_type == TaskType.RESEARCH
    assert task.priority == Priority.HIGH
    assert task.is_consequential is False


def test_plan_task_invalid_type_raises():
    """Test that invalid task types raise validation errors."""
    with pytest.raises(ValidationError):
        PlanTask(
            id="task_001",
            title="Invalid Task",
            description="Test",
            task_type="INVALID_TYPE",  # Invalid
            expected_output="Output",
        )


def test_action_plan_json_serialization():
    """Test ActionPlan JSON serialization and round-trip parsing."""
    task1 = PlanTask(
        id="task_001",
        title="Research candidates",
        description="Search tools",
        task_type=TaskType.RESEARCH,
        priority=Priority.HIGH,
        expected_output="List of tools",
    )
    task2 = PlanTask(
        id="task_002",
        title="Compare pricing",
        description="Extract costs",
        task_type=TaskType.ANALYSIS,
        dependencies=["task_001"],
        expected_output="Pricing table",
    )

    plan = ActionPlan(
        goal="Find the best tool",
        objective="Recommend optimal tool",
        summary="Decomposed into research and analysis phases.",
        constraints=["Budget limit"],
        tasks=[task1, task2],
        final_deliverable="Markdown recommendation document.",
        success_criteria=["Clear selection justified by data."],
    )

    json_str = plan.model_dump_json()
    assert "task_001" in json_str
    assert "task_002" in json_str

    # Round trip
    parsed = ActionPlan.model_validate_json(json_str)
    assert parsed.goal == plan.goal
    assert len(parsed.tasks) == 2
    assert parsed.tasks[1].dependencies == ["task_001"]

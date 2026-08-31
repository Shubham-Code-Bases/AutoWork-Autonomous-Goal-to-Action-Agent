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

"""Unit tests for AutoWork Planner, DAG validation, and plan formatting."""

from app.models import ActionPlan, PlanTask, Priority, TaskType
from app.utils.serializers import format_plan_markdown, validate_plan_graph


def test_simple_goal_plan_structure():
    """Test 1: Simple goal plan structure meets core requirements."""
    goal_input = "Create a marketing plan for my startup."

    task1 = PlanTask(
        id="task_001",
        title="Analyze target demographic and market positioning",
        description="Identify ICP, key value propositions, and competitor landscape.",
        task_type=TaskType.RESEARCH,
        priority=Priority.HIGH,
        dependencies=[],
        required_capabilities=["web_search", "data_analysis"],
        expected_output="Customer persona dossier and competitor positioning matrix.",
        success_criteria=["Defines at least 2 primary user personas."],
    )
    task2 = PlanTask(
        id="task_002",
        title="Select optimal marketing channels",
        description="Evaluate SEO, social media, content marketing, and paid channels.",
        task_type=TaskType.ANALYSIS,
        priority=Priority.MEDIUM,
        dependencies=["task_001"],
        required_capabilities=["data_analysis"],
        expected_output="Channel evaluation matrix with ROI estimates.",
        success_criteria=["Ranks top 3 acquisition channels."],
    )
    task3 = PlanTask(
        id="task_003",
        title="Synthesize 90-day execution roadmap",
        description="Draft sprint-by-sprint tactical milestones and budget allocation.",
        task_type=TaskType.GENERATE,
        priority=Priority.HIGH,
        dependencies=["task_002"],
        required_capabilities=["document_generation"],
        expected_output="Comprehensive 90-day startup marketing strategy document.",
        success_criteria=["Includes timeline, channel allocation, and KPIs."],
    )

    plan = ActionPlan(
        goal=goal_input,
        objective="Formulate a targeted 90-day go-to-market marketing plan.",
        summary="Phased plan covering market research, channel evaluation, and roadmap synthesis.",
        constraints=["Early-stage startup budget", "Organic growth focus"],
        assumptions=["B2B SaaS product"],
        tasks=[task1, task2, task3],
        final_deliverable="Complete Startup Go-To-Market & Marketing Roadmap (Markdown/PDF).",
        success_criteria=[
            "Plan addresses primary persona",
            "Allocates realistic budget",
            "Provides 90-day actionable sprints",
        ],
    )

    is_valid, errors = validate_plan_graph(plan)
    assert is_valid is True
    assert len(errors) == 0
    assert len(plan.tasks) == 3
    assert plan.final_deliverable != ""


def test_complex_goal_dependency_graph():
    """Test 2: Complex goal with parallel branches and multi-parent dependencies."""
    goal_input = "Research cloud providers, compare cost and AI capabilities, and recommend the best option for an AI startup."

    tasks = [
        PlanTask(
            id="task_001",
            title="Identify major AI cloud hyperscalers",
            description="Catalog GCP, AWS, and Azure AI offerings and model support.",
            task_type=TaskType.RESEARCH,
            priority=Priority.HIGH,
            dependencies=[],
            expected_output="Cloud provider overview document.",
        ),
        PlanTask(
            id="task_002",
            title="Benchmark GPU compute & model hosting costs",
            description="Collect pricing for H100/A100 instances and token inferencing APIs.",
            task_type=TaskType.RESEARCH,
            priority=Priority.HIGH,
            dependencies=["task_001"],
            expected_output="Compute cost comparison dataset.",
        ),
        PlanTask(
            id="task_003",
            title="Evaluate proprietary and open-source model ecosystems",
            description="Assess Gemini, Bedrock, and Azure OpenAI integration capabilities.",
            task_type=TaskType.ANALYSIS,
            priority=Priority.HIGH,
            dependencies=["task_001"],
            expected_output="AI capability benchmark matrix.",
        ),
        PlanTask(
            id="task_004",
            title="Perform multi-criteria decision matrix scoring",
            description="Score candidates on price, developer velocity, AI services, and startups credits.",
            task_type=TaskType.DECISION,
            priority=Priority.CRITICAL,
            dependencies=["task_002", "task_003"],
            expected_output="Ranked multi-criteria decision table.",
        ),
        PlanTask(
            id="task_005",
            title="Generate executive cloud architecture recommendation",
            description="Author final recommendation report detailing chosen provider and rationale.",
            task_type=TaskType.GENERATE,
            priority=Priority.HIGH,
            dependencies=["task_004"],
            expected_output="Final Cloud Architecture Recommendation Report.",
        ),
    ]

    plan = ActionPlan(
        goal=goal_input,
        objective="Recommend the best cloud provider for an AI startup based on cost and capability.",
        summary="Parallel research into cost and capabilities followed by weighted decision matrix and final report.",
        tasks=tasks,
        final_deliverable="Cloud Provider Evaluation & Recommendation Report.",
    )

    is_valid, errors = validate_plan_graph(plan)
    assert is_valid is True
    assert len(errors) == 0
    assert len(plan.tasks) == 5
    # Verify task_004 has multi-parent dependencies
    assert set(plan.tasks[3].dependencies) == {"task_002", "task_003"}


def test_constraints_preservation():
    """Test 3: Verify explicit hardware and financial constraints are preserved in plan."""
    goal_input = "Find the best laptop for AI development under ₹150,000 with at least 32GB RAM."

    plan = ActionPlan(
        goal=goal_input,
        objective="Identify and evaluate laptops for AI development meeting budget and RAM specifications.",
        summary="Search laptops, filter by 32GB RAM and ₹150,000 budget, rank top models.",
        constraints=[
            "Budget under ₹150,000 INR",
            "Minimum 32GB unified memory / RAM",
        ],
        assumptions=["Available for purchase in India"],
        tasks=[
            PlanTask(
                id="task_001",
                title="Search laptops with 32GB RAM under ₹150,000",
                description="Query e-commerce and OEM sites for developer laptops within budget constraint.",
                task_type=TaskType.RESEARCH,
                priority=Priority.HIGH,
                expected_output="List of laptops satisfying ₹150k budget and 32GB RAM.",
                success_criteria=[
                    "Every listed item is <= ₹150,000 and has >= 32GB RAM."
                ],
            ),
            PlanTask(
                id="task_002",
                title="Compare local LLM inference performance",
                description="Compare VRAM bandwidth and NPU/GPU TFLOPS for local AI development.",
                task_type=TaskType.ANALYSIS,
                dependencies=["task_001"],
                expected_output="Performance comparison scores.",
            ),
            PlanTask(
                id="task_003",
                title="Generate final buyer recommendation",
                description="Synthesize top 3 laptops with direct purchasing links and trade-off summary.",
                task_type=TaskType.GENERATE,
                dependencies=["task_002"],
                expected_output="Final Buyer Guide with top recommendation.",
            ),
        ],
        final_deliverable="AI Developer Laptop Buyer's Guide with top recommendation.",
        success_criteria=[
            "All recommended laptops strictly cost <= ₹150,000",
            "All recommended laptops possess >= 32GB RAM",
        ],
    )

    is_valid, errors = validate_plan_graph(plan)
    assert is_valid is True
    assert len(errors) == 0
    assert "Budget under ₹150,000 INR" in plan.constraints
    assert "Minimum 32GB unified memory / RAM" in plan.constraints
    assert any("₹150,000" in sc for sc in plan.success_criteria)


def test_dag_cycle_detection():
    """Test DAG cycle detection fails invalid cyclic graphs."""
    cyclic_tasks = [
        PlanTask(
            id="task_001",
            title="Task A",
            description="A",
            task_type=TaskType.RESEARCH,
            dependencies=["task_003"],  # Cycle: 1 -> 2 -> 3 -> 1
            expected_output="A",
        ),
        PlanTask(
            id="task_002",
            title="Task B",
            description="B",
            task_type=TaskType.ANALYSIS,
            dependencies=["task_001"],
            expected_output="B",
        ),
        PlanTask(
            id="task_003",
            title="Task C",
            description="C",
            task_type=TaskType.GENERATE,
            dependencies=["task_002"],
            expected_output="C",
        ),
    ]

    plan = ActionPlan(
        goal="Cyclic test",
        objective="Test cycle detection",
        summary="Test",
        tasks=cyclic_tasks,
        final_deliverable="None",
    )

    is_valid, errors = validate_plan_graph(plan)
    assert is_valid is False
    assert any("Cyclic dependency" in err for err in errors)


def test_missing_dependency_detection():
    """Test validation catches dependencies pointing to non-existent task IDs."""
    bad_tasks = [
        PlanTask(
            id="task_001",
            title="Task 1",
            description="Test",
            task_type=TaskType.RESEARCH,
            dependencies=["task_999"],  # Non-existent
            expected_output="Test",
        ),
    ]

    plan = ActionPlan(
        goal="Missing dep test",
        objective="Test",
        summary="Test",
        tasks=bad_tasks,
        final_deliverable="None",
    )

    is_valid, errors = validate_plan_graph(plan)
    assert is_valid is False
    assert any("non-existent task 'task_999'" in err for err in errors)


def test_format_plan_markdown():
    """Test Markdown formatting produces expected sections for Phase 2 approval."""
    task = PlanTask(
        id="task_001",
        title="Initial Research",
        description="Search tools",
        task_type=TaskType.RESEARCH,
        priority=Priority.HIGH,
        required_capabilities=["web_search"],
        expected_output="Raw list",
        success_criteria=["Found items"],
    )

    plan = ActionPlan(
        goal="Test Goal",
        objective="Test Objective",
        summary="Executive summary text.",
        constraints=["Time limit"],
        tasks=[task],
        final_deliverable="Final Report",
    )

    md = format_plan_markdown(plan)
    assert "# Action Plan: Test Objective" in md
    assert "### Task Execution Graph" in md
    assert "| `task_001` |" in md
    assert "### Final Deliverable" in md

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

"""AutoWork Core Planner and Goal Analyzer ADK Agent definitions."""

from __future__ import annotations

import logging

from google.adk.agents import LlmAgent, SequentialAgent

from .config import config
from .models import ActionPlan, GoalAnalysis
from .prompts import (
    GOAL_ANALYZER_INSTRUCTION,
    PLAN_GENERATOR_INSTRUCTION,
)

logger = logging.getLogger("autowork.planner")


def create_goal_analyzer_agent(
    model_name: str | None = None,
) -> LlmAgent:
    """Instantiates the Goal Analyzer ADK LLM Agent.

    Args:
        model_name: Optional override for the underlying Gemini model.

    Returns:
        Configured LlmAgent instance.
    """
    model = model_name or config.planner_model
    return LlmAgent(
        name="goal_analyzer",
        model=model,
        description="Analyzes and deconstructs natural language user goals into structured objectives, constraints, and success criteria.",
        instruction=GOAL_ANALYZER_INSTRUCTION,
        output_schema=GoalAnalysis,
        output_key="goal_analysis",
    )


def create_plan_generator_agent(
    model_name: str | None = None,
) -> LlmAgent:
    """Instantiates the Plan Generator ADK LLM Agent.

    Args:
        model_name: Optional override for the underlying Gemini model.

    Returns:
        Configured LlmAgent instance.
    """
    model = model_name or config.planner_model
    return LlmAgent(
        name="plan_generator",
        model=model,
        description="Transforms analyzed goals into a structured, dependency-aware ActionPlan DAG.",
        instruction=PLAN_GENERATOR_INSTRUCTION,
        output_schema=ActionPlan,
        output_key="action_plan",
    )


def create_autowork_pipeline(
    model_name: str | None = None,
) -> SequentialAgent:
    """Constructs the sequential AutoWork Phase 1 agent pipeline.

    Workflow:
    1. User Goal -> Goal Analyzer (Produces `goal_analysis` state)
    2. Goal Analysis -> Plan Generator (Produces `action_plan` state)

    Args:
        model_name: Optional override for the Gemini model.

    Returns:
        SequentialAgent orchestrating the Phase 1 core pipeline.
    """
    analyzer = create_goal_analyzer_agent(model_name=model_name)
    generator = create_plan_generator_agent(model_name=model_name)

    return SequentialAgent(
        name="autowork_pipeline",
        description="AutoWork Autonomous Goal-to-Action Planning Pipeline.",
        sub_agents=[analyzer, generator],
    )


# Standard singleton instances for easy import
goal_analyzer_agent = create_goal_analyzer_agent()
plan_generator_agent = create_plan_generator_agent()
autowork_sequential_pipeline = create_autowork_pipeline()

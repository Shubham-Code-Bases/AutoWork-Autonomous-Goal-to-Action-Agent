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

"""Unit tests for AutoWork Google ADK Agent definitions and pipeline configuration."""

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.apps import App

from app.agent import app
from app.models import ActionPlan, GoalAnalysis
from app.planner import (
    create_autowork_pipeline,
    create_goal_analyzer_agent,
    create_plan_generator_agent,
)


def test_goal_analyzer_agent_configuration():
    """Verify Goal Analyzer agent attributes and schema binding."""
    agent = create_goal_analyzer_agent(model_name="gemini-3.5-flash")
    assert isinstance(agent, LlmAgent)
    assert agent.name == "goal_analyzer"
    assert agent.output_schema == GoalAnalysis
    assert agent.output_key == "goal_analysis"
    assert "AutoWork Goal Analyzer" in agent.instruction


def test_plan_generator_agent_configuration():
    """Verify Plan Generator agent attributes and schema binding."""
    agent = create_plan_generator_agent(model_name="gemini-3.5-flash")
    assert isinstance(agent, LlmAgent)
    assert agent.name == "plan_generator"
    assert agent.output_schema == ActionPlan
    assert agent.output_key == "action_plan"
    assert "AutoWork Plan Generator" in agent.instruction


def test_sequential_pipeline_structure():
    """Verify AutoWork sequential pipeline orchestrates analyzer and generator in order."""
    pipeline = create_autowork_pipeline(model_name="gemini-3.5-flash")
    assert isinstance(pipeline, SequentialAgent)
    assert pipeline.name == "autowork_pipeline"
    assert len(pipeline.sub_agents) == 2

    # Check agent ordering
    first_agent = pipeline.sub_agents[0]
    second_agent = pipeline.sub_agents[1]

    assert first_agent.name == "goal_analyzer"
    assert first_agent.output_key == "goal_analysis"

    assert second_agent.name == "plan_generator"
    assert second_agent.output_key == "action_plan"


def test_app_root_agent_binding():
    """Verify the root app exports the sequential pipeline."""
    assert isinstance(app, App)
    assert app.name == "autowork"
    assert app.root_agent is not None
    assert app.root_agent.name == "autowork_pipeline"

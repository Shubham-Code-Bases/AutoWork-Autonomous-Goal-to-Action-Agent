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

"""Configuration management for AutoWork."""

import os

from pydantic import BaseModel, Field


class AutoWorkConfig(BaseModel):
    """Runtime configuration for AutoWork agents and autonomous execution."""

    # Model settings
    model_name: str = Field(
        default_factory=lambda: os.getenv("MODEL_NAME", "gemini-3.5-flash")
    )
    planner_model: str = Field(
        default_factory=lambda: os.getenv(
            "PLANNER_MODEL", os.getenv("MODEL_NAME", "gemini-3.5-flash")
        )
    )
    critic_model: str = Field(
        default_factory=lambda: os.getenv(
            "CRITIC_MODEL", os.getenv("MODEL_NAME", "gemini-3.5-flash")
        )
    )
    worker_model: str = Field(
        default_factory=lambda: os.getenv(
            "WORKER_MODEL", os.getenv("MODEL_NAME", "gemini-3.5-flash")
        )
    )
    temperature: float = Field(
        default_factory=lambda: float(os.getenv("AUTOWORK_TEMPERATURE", "0.2"))
    )

    # Phase 3 Autonomous Execution Limits & Budgets
    max_research_iterations: int = Field(
        default_factory=lambda: int(os.getenv("MAX_RESEARCH_ITERATIONS", "3"))
    )
    max_searches: int = Field(
        default_factory=lambda: int(os.getenv("MAX_SEARCHES", "15"))
    )
    max_retries: int = Field(
        default_factory=lambda: int(os.getenv("MAX_RETRIES", "2"))
    )
    min_confidence_score: float = Field(
        default_factory=lambda: float(os.getenv("MIN_CONFIDENCE_SCORE", "0.75"))
    )

    # Google Cloud / Vertex AI settings
    use_vertexai: bool = Field(
        default_factory=lambda: (
            os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower()
            in ("1", "true", "yes")
        )
    )
    project_id: str | None = Field(
        default_factory=lambda: os.getenv("GOOGLE_CLOUD_PROJECT", None)
    )
    location: str = Field(
        default_factory=lambda: os.getenv(
            "GOOGLE_CLOUD_LOCATION", "us-central1"
        )
    )

    # API Keys
    gemini_api_key: str | None = Field(
        default_factory=lambda: os.getenv(
            "GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", None)
        )
    )


config = AutoWorkConfig()

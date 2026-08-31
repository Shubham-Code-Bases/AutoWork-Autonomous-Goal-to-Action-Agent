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

"""Google Cloud Environment and Service Configuration."""

from __future__ import annotations

import os

from pydantic import BaseModel, Field


class CloudConfig(BaseModel):
    """Google Cloud deployment settings for AutoWork."""

    project_id: str = Field(
        default_factory=lambda: os.getenv(
            "GOOGLE_CLOUD_PROJECT", os.getenv("GCP_PROJECT", "autowork-prod")
        )
    )
    location: str = Field(
        default_factory=lambda: os.getenv(
            "GOOGLE_CLOUD_LOCATION", "us-central1"
        )
    )
    firestore_database: str = Field(
        default_factory=lambda: os.getenv("FIRESTORE_DATABASE", "(default)")
    )
    pubsub_topic: str = Field(
        default_factory=lambda: os.getenv("PUBSUB_TOPIC", "autowork-executions")
    )
    pubsub_subscription: str = Field(
        default_factory=lambda: os.getenv(
            "PUBSUB_SUBSCRIPTION", "autowork-worker-subscription"
        )
    )
    worker_url: str = Field(
        default_factory=lambda: os.getenv(
            "WORKER_SERVICE_URL", "http://autowork-worker:8080"
        )
    )
    is_cloud_mode: bool = Field(
        default_factory=lambda: (
            os.getenv("AUTOWORK_CLOUD_MODE", "false").lower()
            in ("1", "true", "yes")
        )
    )


cloud_config = CloudConfig()

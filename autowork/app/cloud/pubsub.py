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

"""Pub/Sub Job Queue & Asynchronous Dispatcher."""

from __future__ import annotations

import json
import logging
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable

logger = logging.getLogger("autowork.cloud.pubsub")


class ExecutionDispatcher(ABC):
    """Abstract job queue dispatcher for execution sessions."""

    @abstractmethod
    def dispatch(self, execution_id: str) -> bool:
        """Publishes an execution job to the background queue."""
        pass


class LocalAsyncDispatcher(ExecutionDispatcher):
    """Local asynchronous dispatcher using non-blocking background threads."""

    def __init__(
        self, worker_handler: Callable[[str], None] | None = None
    ) -> None:
        self.worker_handler = worker_handler
        self.published_jobs: list[str] = []

    def set_handler(self, handler: Callable[[str], None]) -> None:
        """Sets the background worker execution handler."""
        self.worker_handler = handler

    def dispatch(self, execution_id: str) -> bool:
        self.published_jobs.append(execution_id)
        logger.info(
            "LocalAsyncDispatcher queued execution job: %s", execution_id
        )

        if self.worker_handler:
            # Spawn non-blocking background worker thread
            thread = threading.Thread(
                target=self.worker_handler,
                args=(execution_id,),
                daemon=True,
                name=f"worker-{execution_id}",
            )
            thread.start()

        return True


class PubSubDispatcher(ExecutionDispatcher):
    """Google Cloud Pub/Sub publisher for serverless Cloud Run workers."""

    def __init__(
        self,
        project_id: str,
        topic_name: str = "autowork-executions",
        fallback: ExecutionDispatcher | None = None,
    ) -> None:
        self.project_id = project_id
        self.topic_name = topic_name
        self.fallback = fallback or LocalAsyncDispatcher()
        self._publisher = None

    def _get_publisher(self):
        if self._publisher is None:
            try:
                from google.cloud import pubsub_v1

                self._publisher = pubsub_v1.PublisherClient()
                self._topic_path = self._publisher.topic_path(
                    self.project_id, self.topic_name
                )
            except Exception as exc:
                logger.warning(
                    "Pub/Sub Publisher initialization failed (%s). Using local dispatcher.",
                    exc,
                )
                self._publisher = False
        return self._publisher

    def dispatch(self, execution_id: str) -> bool:
        publisher = self._get_publisher()
        if not publisher:
            return self.fallback.dispatch(execution_id)

        try:
            payload = json.dumps({"execution_id": execution_id}).encode("utf-8")
            future = publisher.publish(self._topic_path, payload)
            message_id = future.result(timeout=5.0)
            logger.info(
                "Pub/Sub message published to %s: message_id=%s execution_id=%s",
                self._topic_path,
                message_id,
                execution_id,
            )
            return True
        except Exception as exc:
            logger.error(
                "Pub/Sub publish failed (%s). Falling back to local dispatcher.",
                exc,
            )
            return self.fallback.dispatch(execution_id)


# Global default dispatcher instance
default_dispatcher = LocalAsyncDispatcher()

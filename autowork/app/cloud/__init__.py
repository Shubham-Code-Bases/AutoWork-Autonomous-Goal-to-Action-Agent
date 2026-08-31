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

"""AutoWork Google Cloud Infrastructure & Asynchronous Runtime Package."""

from .config import CloudConfig, cloud_config
from .firestore import (
    ExecutionRepository,
    FirestoreExecutionRepository,
    InMemoryExecutionRepository,
    default_execution_repository,
)
from .pubsub import (
    ExecutionDispatcher,
    LocalAsyncDispatcher,
    PubSubDispatcher,
    default_dispatcher,
)
from .worker import ExecutionWorker, default_worker, worker_app

# Wire local dispatcher to background worker handler
default_dispatcher.set_handler(default_worker.process_execution_job)

__all__ = [
    "CloudConfig",
    "ExecutionDispatcher",
    "ExecutionRepository",
    "ExecutionWorker",
    "FirestoreExecutionRepository",
    "InMemoryExecutionRepository",
    "LocalAsyncDispatcher",
    "PubSubDispatcher",
    "cloud_config",
    "default_dispatcher",
    "default_execution_repository",
    "default_worker",
    "worker_app",
]

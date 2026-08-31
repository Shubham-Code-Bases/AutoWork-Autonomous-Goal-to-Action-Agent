# AutoWork — Autonomous Goal-to-Action Agent

[![Google ADK](https://img.shields.io/badge/Google-ADK_2.0-blue.svg)](https://github.com/google/adk-python)
[![Google Cloud Run](https://img.shields.io/badge/Google_Cloud-Cloud_Run-4285F4.svg)](https://cloud.google.com/run)
[![Google Cloud Pub/Sub](https://img.shields.io/badge/Google_Cloud-Pub%2FSub-34A853.svg)](https://cloud.google.com/pubsub)
[![Google Cloud Firestore](https://img.shields.io/badge/Google_Cloud-Firestore-FFCA28.svg)](https://cloud.google.com/firestore)
[![License](https://img.shields.io/badge/License-Apache_2.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue.svg)](https://python.org)
[![Status](https://img.shields.io/badge/Phase_4-Cloud_Asynchronous_Runtime_Complete-brightgreen.svg)]()
[![Tests](https://img.shields.io/badge/Tests-55%20Passed%20(100%25)-brightgreen.svg)]()

> **AutoWork** transforms ambitious, high-level user goals into structured execution plans and executes them **autonomously in the background on Google Cloud** following a **single Human Approval Gate**.

---

## 1. Problem Statement

Standard AI assistants block the user's browser during multi-step reasoning, forcing users to wait minutes on synchronous HTTP connections and babysit intermediate steps. Conversely, uncontrolled autonomous agents pose significant safety, cost, and infrastructure hazards by performing unapproved external mutations.

## 2. The AutoWork Asynchronous Autonomy Model

AutoWork decouples user interaction from long-running execution through a **Cloud-Native Asynchronous Runtime**:

```text
Human:
  1. Submits a high-level goal.
  2. Reviews the decomposed Directed Acyclic Graph (DAG) action plan.
  3. Approves the plan once.
  4. FREE TO LEAVE!

AutoWork (in Background on Google Cloud):
  1. API publishes execution job to Google Cloud Pub/Sub.
  2. Cloud Run Background Worker consumes the event and claims an atomic lease.
  3. Autonomous ADK runtime executes research, critique, dynamic refinement, and verification.
  4. State, checkpoints, and deliverables are persisted in Cloud Firestore.
  5. User can return at any time or monitor live progress from the Web Dashboard.
```

---

## 3. Google Cloud-Native Architecture

```mermaid
flowchart TD
    subgraph Client["1. User Interface"]
        U["User"]
        UI["AutoWork Web Dashboard"]
    end

    subgraph API["2. Cloud Run API Service (autowork-api)"]
        GA["Goal Analyzer (LlmAgent)"]
        PG["Plan Generator (LlmAgent)"]
        APPR["Approval & Gatekeeper"]
    end

    subgraph Queue["3. Asynchronous Job Queue"]
        PS["Google Cloud Pub/Sub<br/>(Topic: autowork-executions)"]
        SUB["Push Subscription<br/>(autowork-worker-subscription)"]
    end

    subgraph State["4. Persistent State Store"]
        FS[("Google Cloud Firestore<br/>(Collections: plans, executions)")]
    end

    subgraph Worker["5. Cloud Run Worker Service (autowork-worker)"]
        LEASE["Idempotent Atomic Lease Claim"]
        RT["AutoWork Phase 3 ADK Runtime"]
        RE["Research Engine & Citations"]
        CR["Critic Agent & Refinement Loop"]
        VA["Verification Agent"]
        FA["Finalizer Agent"]
    end

    subgraph AI["6. Google AI Backbone"]
        GEM["Gemini (gemini-3.5-flash / Vertex AI)"]
    end

    U -->|Submit Goal & Approve Plan| UI
    UI -->|REST API| API
    API -->|1. Create Plan & Authorize| FS
    API -->|2. Publish execution_id (Non-blocking)| PS
    API -->|3. Return immediately (QUEUED)| UI

    PS -->|Push Message| SUB
    SUB -->|Invoke Worker Endpoint| LEASE
    LEASE -->|Claim Lock (QUEUED → RUNNING)| FS
    LEASE -->|Execute Plan| RT

    RT --> RE & CR & VA & FA
    RT <--> GEM
    RT -->|Stream Logs & Checkpoints| FS
    FA -->|Persist Actionable Result| FS

    UI -.->|Poll Live Progress & Results| FS
```

---

## 4. Google Cloud Services Mapping

| Google Cloud Service | Role in AutoWork |
| :--- | :--- |
| **Google Cloud Run** | Hosts two decoupled container services: `autowork-api` (interactive REST API & Dashboard) and `autowork-worker` (serverless background execution). |
| **Google Cloud Pub/Sub** | Asynchronous job queue (`autowork-executions`) ensuring non-blocking request handling and guaranteed message delivery. |
| **Google Cloud Firestore** | Scalable NoSQL persistence storing plan DAGs, approval authorizations, operational logs, and final actionable deliverables. |
| **Google Vertex AI / Gemini** | High-throughput cognitive backbone powering goal understanding, critique gap analysis, and final synthesis. |
| **Google Cloud Build** | Automated CI/CD container build pipeline (`cloudbuild.yaml`) deploying to Artifact Registry and Cloud Run. |
| **Google Cloud Logging** | Structured operational telemetry and audit logging. |

---

## 5. Hackathon Alignment Matrix

| Hackathon Requirement | AutoWork Phase 4 Implementation |
| :--- | :--- |
| **Gemini AI Integration** | Google Gemini (`gemini-3.5-flash`) via Google ADK 2.0 / Vertex AI |
| **Google Agent Framework** | Google Agent Development Kit (ADK 2.0) `LlmAgent` & `SequentialAgent` pipelines |
| **Google Cloud Native** | Dual Cloud Run container microservices (`autowork-api` and `autowork-worker`) |
| **Asynchronous Background Runtime** | Decoupled Cloud Pub/Sub queue with atomic idempotency leases |
| **Complex Multi-Step Workflow** | Atomic task decomposition into Directed Acyclic Graphs (DAGs) |
| **Autonomous Self-Correction** | Search → Critique → Gap Detection → Refinement → Verification loop |
| **Human-in-the-Loop Governance** | Phase 2 one-time approval gate with explicit capability authorization |
| **Safety & Consequential Gating** | External mutations (`EXTERNAL_ACTION`, `DESTRUCTIVE`) safely isolated as proposed recommendations |
| **Grounded Traceable Citations** | Authentic source URLs, excerpts, and relevance confidence scoring |
| **State Persistence** | Cloud Firestore native schema tracking execution lifecycle checkpoints |

---

## 6. REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Lightweight health check probe for Cloud Run (`{"status": "ok"}`). |
| `POST` | `/api/plans` | Decomposes a natural-language goal into a structured `ActionPlan` (`AWAITING_APPROVAL`). |
| `GET` | `/api/plans/{id}` | Retrieves full structured `ActionPlan` JSON. |
| `GET` | `/api/plans/{id}/summary` | Generates executive Human-in-the-Loop review dossier. |
| `POST` | `/api/plans/{id}/approve` | **Asynchronous Approval**: Authorizes plan, publishes job to Pub/Sub, and returns `QUEUED` immediately. |
| `POST` | `/api/plans/{id}/reject` | Rejects plan and records rationale. |
| `POST` | `/api/plans/{id}/modify` | Modifies plan, increments version (`v1` → `v2`), and resets to `awaiting_approval`. |
| `GET` | `/api/executions/{id}` | Retrieves live execution state, progress logs, and metrics from Firestore. |
| `GET` | `/api/executions/{id}/result` | Retrieves final actionable deliverable and traceable citations. |
| `POST` | `/pubsub/push` | Cloud Run Worker endpoint receiving push notifications from Pub/Sub. |
| `GET` | `/` | Interactive Web Dashboard with live Firestore log stream. |

---

## 7. Getting Started & Running Locally

### Prerequisites
- **Python 3.11 / 3.12**
- **uv** package manager
- Gemini API Key **or** Google Cloud Vertex AI credentials

### Step 1: Install Dependencies
```bash
cd autowork
uv sync --dev
```

### Step 2: Run the Full Test Suite (55 Tests)
```bash
uv run pytest -v
```

### Step 3: Launch Local Server (Supports Local Async & Cloud Mode)
```bash
uv run uvicorn app.server:api_app --host 127.0.0.1 --port 8000 --reload
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

---

## 8. Google Cloud Deployment Guide

### Automated Cloud Deployment in 3 Steps:

```bash
# 1. Configure GCP Project and Enable APIs, Firestore, Pub/Sub, and IAM
chmod +x scripts/*.sh
./scripts/setup_gcp.sh

# 2. Deploy API Service to Cloud Run
./scripts/deploy_api.sh

# 3. Deploy Worker Service to Cloud Run and wire Pub/Sub Push
./scripts/deploy_worker.sh
```

---

## 9. Technology Stack
- **AI Model**: Google Gemini (`gemini-3.5-flash`)
- **Agent Framework**: Google Agent Development Kit (ADK 2.0)
- **Cloud Infrastructure**: Google Cloud Run, Cloud Pub/Sub, Cloud Firestore, Cloud Build
- **API & Worker Layer**: FastAPI, Uvicorn, Python 3.12
- **Data Validation**: Pydantic v2
- **Development Accelerator**: Antigravity IDE

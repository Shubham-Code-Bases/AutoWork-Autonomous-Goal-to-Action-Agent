# AutoWork — Autonomous Goal-to-Action Agent

[![Google ADK](https://img.shields.io/badge/Google-ADK_2.0-blue.svg)](https://github.com/google/adk-python)
[![Google Cloud Run](https://img.shields.io/badge/Google_Cloud-Cloud_Run-4285F4.svg)](https://cloud.google.com/run)
[![Google Cloud Pub/Sub](https://img.shields.io/badge/Google_Cloud-Pub%2FSub-34A853.svg)](https://cloud.google.com/pubsub)
[![Google Cloud Firestore](https://img.shields.io/badge/Google_Cloud-Firestore-FFCA28.svg)](https://cloud.google.com/firestore)
[![License](https://img.shields.io/badge/License-Apache_2.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue.svg)](https://python.org)
[![Status](https://img.shields.io/badge/Hackathon-Submission_Ready-brightgreen.svg)]()
[![Tests](https://img.shields.io/badge/Tests-55%20Passed%20(100%25)-brightgreen.svg)]()

> ### **Give it a goal. Approve once. Let it work.**

**AutoWork** is an autonomous AI agent that transforms ambitious, high-level user goals into structured execution plans, waits for a **single Human Approval Gate**, and then executes the approved workflow **asynchronously in the background on Google Cloud**.

It autonomously researches, analyzes evidence, **critiques its own findings**, identifies information gaps, conducts adaptive follow-up research, **verifies factual grounding**, and generates verified, executive-ready deliverables with traceable citations.

Built with **Gemini**, the **Google Agent Development Kit (ADK 2.0)**, and **Google Cloud**.

---

## ⚡ Quick Navigation for Judges & Reviewers

- 🚀 **Application Source**: [`autowork/`](./autowork/)
- 🎬 **4-Minute Video Demo Script**: [`autowork/DEMO.md`](./autowork/DEMO.md)
- 📝 **Devpost Submission Text & Metadata**: [`autowork/DEVPOST.md`](./autowork/DEVPOST.md)
- 🧪 **55 Automated Tests**: Run `cd autowork && uv run pytest -v` (100% pass rate)

---

## 🛑 Problem: The "Chatbot Orchestration Tax"

Modern AI assistants operate as synchronous prompt-and-answer engines:
```text
User asks  →  AI responds  →  User asks again  →  AI responds
```
For complex work, the user must manually:
- Break the problem into sub-tasks.
- Babysit blocking browser windows during multi-step reasoning.
- Search and cross-reference information.
- Identify missing information and write follow-up prompts.
- Verify evidence grounding manually.
- Synthesize conclusions and determine concrete next steps.

**AutoWork removes this orchestration burden.**

---

## 💡 Solution: Goal → Plan → Approve → Execute → Verify → Act

```text
User provides a high-level goal.
        ↓
AutoWork creates a structured Directed Acyclic Graph (DAG) plan.
        ↓
User reviews and approves ONCE.
        ↓
AutoWork executes independently in the background on Google Cloud.
        ↓
Specialist agents search, collect evidence, and analyze.
        ↓
Critic Agent audits evidence and identifies information gaps.
        ↓
Follow-up research dynamically fills missing data.
        ↓
Verification Agent checks grounding and scores confidence.
        ↓
Final actionable deliverable with traceable citations.
```

---

## 🏗️ Google Cloud System Architecture

```mermaid
flowchart TD
    subgraph Client["1. User Interface"]
        U["User"]
        UI["AutoWork Web Dashboard (HTML5 / Vanilla CSS)"]
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
        RE["Research Engine & Grounded Citations"]
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

## 🔄 The Autonomous Intelligence Loop (Search → Critique → Refine → Verify)

```mermaid
flowchart LR
    A[Approved Plan] --> B[Research Engine]
    B --> C[Evidence Store]
    C --> D[Critic Agent]
    D --> E{Information Gaps Found?}
    E -->|Yes: Trigger Follow-up| F[Follow-up Research]
    F --> B
    E -->|No: Sufficient Evidence| G[Verification Agent]
    G --> H[Finalizer Agent]
    H --> I[Actionable Result]
```

---

## ☁️ Google Cloud Services Mapping

| Google Cloud Service | Role in AutoWork |
| :--- | :--- |
| **Google Cloud Run** | Hosts two decoupled container services: `autowork-api` (interactive REST API & Dashboard) and `autowork-worker` (serverless background execution). |
| **Google Cloud Pub/Sub** | Asynchronous job queue (`autowork-executions`) ensuring non-blocking request handling and guaranteed message delivery. |
| **Google Cloud Firestore** | Scalable NoSQL persistence storing plan DAGs, approval authorizations, operational logs, and final actionable deliverables. |
| **Google Vertex AI / Gemini** | High-throughput cognitive backbone powering goal understanding, critique gap analysis, and final synthesis. |
| **Google Cloud Build** | Automated CI/CD container build pipeline (`cloudbuild.yaml`) deploying to Artifact Registry and Cloud Run. |
| **Google Cloud Logging** | Structured operational telemetry and audit logging. |

---

## 🚀 Quickstart & Local Development

### 1. Install Dependencies
```bash
cd autowork
uv sync --dev
```

### 2. Configure Environment
```bash
cp .env.example .env
# Set GEMINI_API_KEY or configure Vertex AI
```

### 3. Run Test Suite (55 Tests — 100% Pass Rate)
```bash
uv run pytest -v
```

### 4. Launch Local Web Dashboard
```bash
uv run uvicorn app.server:api_app --host 127.0.0.1 --port 8000 --reload
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

---

## ☁️ Google Cloud Deployment (3 Steps)

```bash
cd autowork
chmod +x scripts/*.sh

# 1. Enable Cloud APIs, Firestore, Pub/Sub, and IAM Service Accounts
./scripts/setup_gcp.sh

# 2. Deploy API Service to Cloud Run
./scripts/deploy_api.sh

# 3. Deploy Background Worker Service to Cloud Run & wire Pub/Sub push
./scripts/deploy_worker.sh
```

---

## 🏆 Hackathon Track & Requirements Matrix

**Primary Track: Taskmaster (Autonomous Multi-Step Goal Execution)**

| Hackathon Requirement | AutoWork Implementation |
| :--- | :--- |
| **Gemini 3.5+ Model** | Google Gemini (`gemini-3.5-flash`) runtime |
| **Google Agent Framework** | Google Agent Development Kit (ADK 2.0) |
| **Google Cloud Infrastructure** | Google Cloud Run (API + Worker), Pub/Sub, Firestore |
| **Asynchronous Background Execution** | Decoupled Cloud Pub/Sub queue with atomic idempotency leases |
| **Complex Multi-Step Workflow** | Directed Acyclic Graph (DAG) task decomposition |
| **Autonomous Self-Correction** | Search → Critique → Gap Detection → Refinement → Verification |
| **Human-in-the-Loop Governance** | One-time human approval gate with explicit authorization tickets |
| **Safety & Consequential Gating** | External mutations safely isolated as proposed recommendations |
| **Grounded Citations** | Authentic source URLs, excerpts, and relevance confidence scoring |
| **Persistent State** | Cloud Firestore native schema tracking execution checkpoints |
| **Production Architecture** | Decoupled API and Worker microservices with health probes |
| **Reproducibility** | Complete README, automated setup scripts, and 55 passing tests |

---

## 🛡️ Safety & Control Principles

1. **No Automatic Execution**: Generated plans never execute without explicit human approval.
2. **Deterministic Governance**: Authorization logic is enforced in the application layer, not inferred by the LLM.
3. **Strict Resource Budgets**: Research is capped at 3 iterations, 15 search calls, and strict query timeouts to prevent runaway costs.
4. **External Mutation Gating**: Actions marked `EXTERNAL_ACTION` or `DESTRUCTIVE` are presented as recommendations for human implementation rather than blind automated triggers.
5. **Persistent Audit Trail**: Full execution histories and critique logs are retained in Firestore.

---

## ⚡ Development Note: Antigravity Accelerator

AutoWork was developed using **Antigravity** as a pair-programming development accelerator to meet the hackathon's accelerated development schedule. Antigravity is not part of the runtime architecture; the runtime is **Python 3.12 + Google ADK 2.0 + Gemini + Google Cloud**.

---

## 📚 About ADK Sample Code & Attribution

AutoWork builds on patterns demonstrated by Google's [Agent Development Kit (ADK)](https://github.com/google/adk-python) sample repository, particularly agent orchestration, sequential planning, evaluation, and iterative refinement patterns. The upstream reference samples are preserved under [`core/`](./core/) and [`contrib/`](./contrib/) for ecosystem completeness under the Apache 2.0 License.

---

## 📄 License

Apache 2.0 — see [LICENSE](./LICENSE).

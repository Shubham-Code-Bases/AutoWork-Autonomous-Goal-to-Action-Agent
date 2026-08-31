# AutoWork — 4-Minute Video Demonstration Script

> **Product**: AutoWork — Autonomous Goal-to-Action Agent  
> **Tagline**: *Give it a goal. Approve once. Let it work.*  
> **Target Track**: Taskmaster  
> **Target Video Duration**: 3:30 – 4:00 minutes

---

## 1. Demo Goals

### Primary Demo Goal:
```text
"Research the best AI coding agents for a small software startup and recommend the best option based on price, coding capability, integrations, and suitability."
```

### Fallback Demo Goal (if offline / presenting market analysis):
```text
"Analyze India's semiconductor manufacturing opportunity and recommend top investment areas for the next 5 years."
```

---

## 2. 4-Minute Step-by-Step Script & Timeline

### ⏱️ 0:00–0:25 | The Problem Statement
- **Screen**: Webcam / Intro Title Slide.
- **Narrator**:
  > *"Modern AI assistants force users into constant prompt-and-response loops. For any complex objective, you have to break down tasks manually, babysit the browser, search, synthesize, detect missing information, and verify everything yourself. Chatbots stop at answering questions — they don't do autonomous work."*

---

### ⏱️ 0:25–0:45 | The AutoWork Solution
- **Screen**: AutoWork Web Dashboard (`http://localhost:8000`).
- **Narrator**:
  > *"AutoWork solves this with a fundamentally different paradigm: **Goal → Plan → Approve → Asynchronous Background Execution → Verified Deliverable**. You provide a high-level goal, approve the structured workflow once, and AutoWork executes autonomously on Google Cloud while you are free to leave."*

---

### ⏱️ 0:45–1:15 | Step 1: Goal to Directed Acyclic Graph (DAG) Plan
- **Screen**: Web UI (`http://localhost:8000`).
- **Action**: Click Preset **"🤖 AI Coding Agents for Startup"** and click **"Generate Plan"**.
- **Narrator**:
  > *"AutoWork uses Google Gemini and the Google Agent Development Kit (ADK 2.0) to parse the goal and synthesize a Directed Acyclic Graph (DAG) of dependency-linked milestones. Notice how tasks are typed, prioritized, and safety-classified. Consequential external actions are isolated and flagged for explicit human review."*

---

### ⏱️ 1:15–1:30 | Step 2: One-Time Human Approval Gate
- **Screen**: Web UI.
- **Action**: Click **"🚀 Approve & Run Asynchronously"**.
- **Narrator**:
  > *"Here is the core governance principle: the human reviews and approves the plan once. The moment I click 'Approve', AutoWork registers the authorization ticket, dispatches the execution job to Google Cloud Pub/Sub, and returns immediately with status 'QUEUED'. The user is completely free to close the tab or leave."*

---

### ⏱️ 1:30–2:10 | Step 3: Google Cloud Background Execution Proof
- **Screen**: Switch between Browser UI and Google Cloud Console tabs (or terminal showing async response).
- **Narrator**:
  > *"In the background on Google Cloud, our Cloud Run Worker receives the Pub/Sub push notification and claims an atomic idempotency lease in Cloud Firestore. This ensures no job is ever executed twice. Even if the browser is closed or refreshed, the agent continues operating serverlessly."*

---

### ⏱️ 2:10–2:55 | Step 4: Autonomous Intelligence (Search → Critique → Refine → Verify)
- **Screen**: Web UI live operational log stream and metrics.
- **Narrator**:
  > *"Now watch the autonomous intelligence loop in action:*
  > *1. The **Research Engine** gathers grounded evidence and prevents duplicate queries.*
  > *2. The **Critic Agent** audits the findings against user constraints and detects that pricing tiers and integration details were incomplete.*
  > *3. The Critic triggers an automatic follow-up refinement search.*
  > *4. Finally, the **Verification Agent** computes a grounding score (92% confidence) to ensure all claims are backed by authentic citations."*

---

### ⏱️ 2:55–3:30 | Step 5: Final Actionable Deliverable
- **Screen**: Scroll to the Final Result section.
- **Narrator**:
  > *"AutoWork completes the execution and presents an executive-ready deliverable:*
  > *- A comprehensive Executive Summary and Trade-off Matrix.*
  > *- Grounded recommendations tailored to small engineering teams.*
  > *- Concrete, phased Next Steps.*
  > *- Fully traceable citations with direct source links and a 92% confidence rating.*
  > *- Explicit disclosure of limitations."*

---

### ⏱️ 3:30–3:50 | Step 6: Architecture Overview
- **Screen**: Architecture Diagram in README / Slide.
- **Narrator**:
  > *"Under the hood, AutoWork is built on:*
  > *- **Google Gemini & Google ADK 2.0** for agent orchestration and multi-agent critique.*
  > *- **Google Cloud Run** for decoupled API and background worker microservices.*
  > *- **Google Cloud Pub/Sub** for guaranteed asynchronous job queuing.*
  > *- **Google Cloud Firestore** for persistent plan and execution state.*
  > *- **Antigravity IDE** as our rapid development accelerator."*

---

### ⏱️ 3:50–4:00 | Step 7: Closing
- **Screen**: Closing slide / AutoWork banner.
- **Narrator**:
  > *"AutoWork changes AI from something you repeatedly prompt into an autonomous system you can give a goal to, approve once, and let work. Thank you!"*

---

## 3. Google Cloud Console Screens to Show During Demo

| Service | Screen / Filter | What to Highlight |
| :--- | :--- | :--- |
| **Cloud Run** | Services: `autowork-api` & `autowork-worker` | Show two independent microservices running on Google Cloud. |
| **Cloud Pub/Sub** | Topic: `autowork-executions` | Show the message queue that decouples API requests from worker execution. |
| **Cloud Firestore** | Collections: `plans` & `executions` | Show live persistent document containing `status: "completed"` and logs. |
| **Cloud Logging** | Filter: `resource.type="cloud_run_revision"` | Show structured logs: `Lease claimed`, `Critic identified gaps`, `Verification passed`. |

---

## 4. Fallback Script (If Offline / Local Mode)
If presenting without active Google Cloud connectivity, run locally using the built-in local asynchronous queue:
```bash
uv run uvicorn app.server:api_app --host 127.0.0.1 --port 8000 --reload
```
The local runtime uses the exact same `LocalAsyncDispatcher` and `InMemoryExecutionRepository` mimicking Cloud Run + Pub/Sub + Firestore with 100% fidelity.

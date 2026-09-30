# AI Customer Support Agent — Complete Project Documentation

This document explains **what the project is**, **what it does**, **how it works**, and **how to run and test everything**.

---

## Table of contents

1. [What is this project?](#1-what-is-this-project)
2. [What problem does it solve?](#2-what-problem-does-it-solve)
3. [What technologies are used?](#3-what-technologies-are-used)
4. [High-level architecture](#4-high-level-architecture)
5. [Project folder structure](#5-project-folder-structure)
6. [How the system works (step by step)](#6-how-the-system-works-step-by-step)
7. [Agents and their roles](#7-agents-and-their-roles)
8. [Tools](#8-tools)
9. [Human-in-the-loop (approvals)](#9-human-in-the-loop-approvals)
10. [Database and demo data](#10-database-and-demo-data)
11. [Environment variables](#11-environment-variables)
12. [How to run the project locally](#12-how-to-run-the-project-locally)
13. [How to test with Swagger UI](#13-how-to-test-with-swagger-ui)
14. [How to test with curl / API flow](#14-how-to-test-with-curl--api-flow)
15. [How to run automated tests](#15-how-to-run-automated-tests)
16. [Docker](#16-docker)
17. [Demo customer scenarios](#17-demo-customer-scenarios)
18. [LangSmith (optional)](#18-langsmith-optional)
19. [Safety rules](#19-safety-rules)
20. [Future improvements](#20-future-improvements)

---

## 1. What is this project?

**AI Customer Support Agent** is a portfolio-quality **agentic customer support platform**.

It is **not** a simple chatbot that only replies with text.

It is a full workflow system where:

- A customer sends a support message through an API
- An AI system **classifies** the issue
- A **supervisor** routes it to a specialist agent (billing, technical, account, or general)
- That agent uses **tools** to investigate (transactions, knowledge base, account status, etc.)
- Sensitive actions (like refunds) require **human approval**
- A clear customer reply is generated and stored in the database

Think of it as a small **AI support desk** with routing, tools, memory, and human review.

---

## 2. What problem does it solve?

Traditional chatbots often:

- Guess answers
- Invent refunds or account actions
- Have no clear handoff to humans
- Do not keep structured records

This project shows a better pattern:

| Need | How this project handles it |
|------|-----------------------------|
| Understand the request | Structured intent classification |
| Use the right specialist | Supervisor + specialized agents |
| Use real data | Tools + database services |
| Avoid dangerous auto-actions | Human-in-the-loop approvals |
| Remember context | Conversation + customer memory |
| Trace what happened | Logs + optional LangSmith |

---

## 3. What technologies are used?

| Technology | Role |
|------------|------|
| **Python 3.11+** | Main language |
| **FastAPI** | REST API + Swagger docs |
| **Pydantic** | Request/response schemas + structured LLM output |
| **SQLAlchemy (async)** | Database ORM |
| **PostgreSQL / SQLite** | Data storage |
| **Alembic** | Database migrations |
| **LangChain** | LLM client, tools, prompts |
| **LangGraph** | Multi-step agent workflow, routing, HITL |
| **LangSmith** | Optional tracing / observability |
| **Pytest** | Automated tests |
| **Docker Compose** | Run API + Postgres together |

---

## 4. High-level architecture

```
                Customer
                   |
                   v
            FastAPI API  (+ Swagger at /docs)
                   |
                   v
        Support Orchestrator
                   |
                   v
            LangGraph Workflow
                   |
          Support Supervisor
                   |
    +--------------+--------------+--------------+
    |              |              |              |
    v              v              v              v
 Billing       Technical       Account        General
  Agent          Agent          Agent          Agent
    |              |              |              |
    +--------------+--------------+--------------+
                   |
                   v
           Evaluate Resolution
                   |
         +---------+---------+
         |                   |
         v                   v
   Human Review         Auto Resolve
   (approve/reject)           |
         |                   |
         +---------+---------+
                   |
                   v
            Final Response
                   |
                   v
              PostgreSQL / SQLite
```

### Layer responsibilities

| Layer | Responsibility |
|-------|----------------|
| **API** (`app/api/`) | Receive HTTP requests only |
| **Orchestrator** (`support_orchestrator.py`) | Start/resume the graph |
| **Graph** (`app/graph/`) | Workflow steps and routing |
| **Agents** (`app/agents/`) | Decide what to do |
| **Tools** (`app/tools/`) | Safe actions agents can call |
| **Services** (`app/services/`) | Database business logic |
| **Models** (`app/models/`) | Database tables |

Business logic is **not** placed inside FastAPI route handlers.

---

## 5. Project folder structure

```
ai-customer-support/
│
├── app/                          # Application code
│   ├── main.py                   # FastAPI entrypoint
│   ├── config.py                 # Settings from environment
│   ├── llm.py                    # LLM + LangSmith setup
│   ├── prompts.py                # Agent system prompts
│   │
│   ├── api/                      # HTTP API
│   │   ├── dependencies.py
│   │   └── routes/
│   │       ├── conversations.py
│   │       ├── customers.py
│   │       ├── tickets.py
│   │       └── approvals.py
│   │
│   ├── agents/                   # AI agents
│   │   ├── classifier.py
│   │   ├── supervisor.py
│   │   ├── billing.py
│   │   ├── technical.py
│   │   ├── account.py
│   │   ├── general.py
│   │   └── response.py
│   │
│   ├── graph/                    # LangGraph workflow
│   │   ├── state.py
│   │   ├── nodes.py
│   │   ├── routing.py
│   │   └── workflow.py
│   │
│   ├── tools/                    # Agent tools
│   ├── services/                 # Business logic
│   ├── models/                   # SQLAlchemy tables
│   ├── schemas/                  # Pydantic schemas
│   ├── database/                 # DB engine/session
│   ├── memory/                   # Conversation + customer memory
│   └── middleware/               # Logging + tool safety
│
├── knowledge/                    # Markdown knowledge base
│   ├── billing.md
│   ├── refunds.md
│   ├── account.md
│   ├── password_reset.md
│   └── technical.md
│
├── tests/                        # Pytest tests
├── scripts/seed_database.py      # Demo seed data
├── alembic/                      # DB migrations
│
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── .env.example
├── README.md
└── DOCUMENTATION.md              # This file
```

---

## 6. How the system works (step by step)

When a customer sends a message, this happens:

### Step 1 — API receives the message

Example:

```http
POST /api/v1/conversations/{conversation_id}/messages
{
  "content": "I was charged twice for my subscription."
}
```

### Step 2 — Load context

The graph loads:

- Customer profile (plan, device, app version, status)
- Previous messages in the same conversation

### Step 3 — Classify the request

Produces structured output (`SupportIntent`):

- `category`: billing / technical / account / general
- `priority`: low / medium / high / critical
- `summary`
- `requires_human`
- `reason`

If `LLM_API_KEY` is set, an LLM is used.  
If not, a heuristic classifier still works for demos and tests.

### Step 4 — Supervisor routes

The supervisor only chooses which specialist should handle the request.  
It does **not** solve the issue itself.

### Step 5 — Specialist agent investigates

The chosen agent calls tools, for example:

- Get transactions
- Search knowledge base
- Create password reset
- Prepare refund request

### Step 6 — Evaluate resolution

- If the issue is safe to finish → generate response
- If a sensitive action is needed → pause for human approval

### Step 7 — Human approval (when needed)

A reviewer calls:

```http
POST /api/v1/approvals/{approval_id}/approve
```

or

```http
POST /api/v1/approvals/{approval_id}/reject
```

The workflow resumes and completes.

### Step 8 — Save conversation

Customer message, agent reply, tickets, approvals, and actions are stored in the database.

---

## 7. Agents and their roles

| Agent | Responsibility | Example input |
|-------|----------------|---------------|
| **Classifier** | Understand category + priority | Any customer message |
| **Supervisor** | Route to the right specialist | Uses classification result |
| **Billing** | Charges, refunds, invoices, subscriptions | “I was charged twice” |
| **Technical** | Bugs, crashes, app/API issues | “App crashes when I upload a PDF” |
| **Account** | Password, email, account status | “I forgot my password” |
| **General** | Policies, hours, FAQ from knowledge base | “What are your support hours?” |
| **Response** | Write the final customer-facing reply | After investigation / approval |

---

## 8. Tools

Agents cannot run arbitrary SQL. They only call controlled tools.

### Read tools

- `get_customer`
- `get_subscription`
- `get_transactions`
- `get_invoice`
- `get_account_status`
- `get_customer_device`
- `get_service_status`
- `search_knowledge_base`

### Safe write tools

- `create_password_reset`
- `create_support_ticket`

### Sensitive write tools (require human approval)

- `create_refund_request`
- `prepare_email_change`

Sensitive tools only **prepare** an action. They do not complete it until a human approves.

---

## 9. Human-in-the-loop (approvals)

### Why?

Refunds and account changes are risky. The AI must not claim “refund completed” unless a human approved and the system recorded it.

### Flow

```
Agent prepares action
        |
        v
Approval row created (status = pending)
        |
        v
LangGraph pauses (interrupt)
        |
        v
API returns awaiting_approval + approval_id
        |
        v
Human approves or rejects
        |
        +-- approved --> execute real action --> final reply
        |
        +-- rejected --> cancel --> final reply
```

### Approval API

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/approvals` | List pending approvals |
| POST | `/api/v1/approvals/{id}/approve` | Approve |
| POST | `/api/v1/approvals/{id}/reject` | Reject |

---

## 10. Database and demo data

### Main tables

- `customers`
- `conversations`
- `messages`
- `tickets`
- `transactions`
- `approvals`
- `support_actions`

### Seed demo customers

Run:

```bash
python scripts/seed_database.py
```

| Customer ID | Name | Useful for |
|-------------|------|------------|
| `CUST-001` | Alice Johnson | Duplicate subscription charge |
| `CUST-002` | Bob Smith | Failed payment / password reset |
| `CUST-003` | Carol Lee | Technical PDF crash |

Demo transactions include duplicate charges `TX-1001` and `TX-1002` for `CUST-001`.

---

## 11. Environment variables

Copy the example file:

```bash
cp .env.example .env
```

Then edit `.env`.

| Variable | Required | Meaning |
|----------|----------|---------|
| `DATABASE_URL` | Yes | Database connection string |
| `LLM_API_KEY` | No* | LLM provider API key |
| `LLM_MODEL` | No | Model name (default: `openai/gpt-4o-mini`) |
| `LLM_BASE_URL` | No | OpenAI-compatible base URL (e.g. OpenRouter) |
| `LLM_TEMPERATURE` | No | Generation temperature |
| `LANGSMITH_TRACING` | No | `true` / `false` |
| `LANGSMITH_API_KEY` | No | LangSmith key |
| `LANGSMITH_PROJECT` | No | LangSmith project name |
| `CHECKPOINT_DB_PATH` | No | Path for LangGraph checkpoints |
| `KNOWLEDGE_DIR` | No | Path to Markdown knowledge files |

\*Without `LLM_API_KEY`, the app still runs using a heuristic classifier for demos and tests.

### Example local SQLite URL

```env
DATABASE_URL=sqlite+aiosqlite:///./data/support.db
```

### Example Postgres URL

```env
DATABASE_URL=postgresql+asyncpg://support:support@localhost:5432/support_db
```

**Never commit real API keys.** Keep secrets only in `.env` (already in `.gitignore`).

---

## 12. How to run the project locally

### Prerequisites

- Python 3.11+ (3.12 recommended)
- `pip`
- Optional: Docker (for Compose setup)
- Optional: LLM API key (OpenRouter / OpenAI-compatible)

### Setup steps

```bash
# 1. Go to project folder
cd ai-customer-support

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Configure environment
cp .env.example .env
# Edit .env if needed

# 5. Create data folder + seed demo data
mkdir -p data
export DATABASE_URL=sqlite+aiosqlite:///./data/support.db
python scripts/seed_database.py

# 6. Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Verify server is up

Open:

- Health: [http://localhost:8000/health](http://localhost:8000/health)
- Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)

Expected health response:

```json
{"status": "ok", "app": "AI Customer Support Agent"}
```

---

## 13. How to test with Swagger UI

This project has **no custom chat frontend**.  
Swagger is the interactive UI for testing APIs.

### Open Swagger

After starting the server, open:

**[http://localhost:8000/docs](http://localhost:8000/docs)**

Also available:

- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- OpenAPI JSON: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

### Suggested Swagger test order

1. `GET /health`
2. `GET /api/v1/customers`
3. `POST /api/v1/conversations` with body:

```json
{
  "customer_id": "CUST-001"
}
```

4. Copy the returned conversation `id`
5. `POST /api/v1/conversations/{conversation_id}/messages` with body:

```json
{
  "content": "I was charged twice for my subscription."
}
```

6. If `approval_id` is returned, open Approvals and call:

`POST /api/v1/approvals/{approval_id}/approve`

```json
{
  "reviewer_note": "Verified duplicate charge"
}
```

7. Check conversation again with `GET /api/v1/conversations/{id}`

---

## 14. How to test with curl / API flow

### A) Create conversation

```bash
curl -s -X POST http://localhost:8000/api/v1/conversations \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":"CUST-001"}'
```

Save the `id` from the response.

### B) Send billing message

```bash
curl -s -X POST http://localhost:8000/api/v1/conversations/CONV_ID_HERE/messages \
  -H 'Content-Type: application/json' \
  -d '{"content":"I was charged twice for my subscription."}'
```

Expected highlights:

- `assigned_agent`: `"billing"`
- `requires_human`: `true`
- `status`: `"awaiting_approval"`
- `approval_id` present

### C) List approvals

```bash
curl -s http://localhost:8000/api/v1/approvals
```

### D) Approve refund

```bash
curl -s -X POST http://localhost:8000/api/v1/approvals/APR_ID_HERE/approve \
  -H 'Content-Type: application/json' \
  -d '{"reviewer_note":"Verified duplicate"}'
```

### E) Other scenario commands

Password reset (`CUST-002`):

```bash
# create conversation for CUST-002, then:
curl -s -X POST http://localhost:8000/api/v1/conversations/CONV_ID/messages \
  -H 'Content-Type: application/json' \
  -d '{"content":"I forgot my password."}'
```

Technical issue (`CUST-003`):

```bash
curl -s -X POST http://localhost:8000/api/v1/conversations/CONV_ID/messages \
  -H 'Content-Type: application/json' \
  -d '{"content":"The app crashes when I upload a PDF."}'
```

Unknown question:

```bash
curl -s -X POST http://localhost:8000/api/v1/conversations/CONV_ID/messages \
  -H 'Content-Type: application/json' \
  -d '{"content":"I need help with something that isn'\''t documented."}'
```

List tickets:

```bash
curl -s http://localhost:8000/api/v1/tickets
```

---

## 15. How to run automated tests

```bash
cd ai-customer-support
source .venv/bin/activate
pytest -v
```

### What the tests cover

- Intent classification / routing
- Tool behavior
- Billing agent + approval flow
- Account / password flow
- Technical and unknown-ticket flows
- FastAPI endpoints

### Tip for stable tests

If your `.env` has a real `LLM_API_KEY`, tests may try to call the live LLM.

For offline/reliable tests, temporarily use a placeholder key:

```bash
LLM_API_KEY=test-key pytest -v
```

---

## 16. Docker

### Start API + Postgres

```bash
cd ai-customer-support
docker compose up --build
```

Then open:

- API: [http://localhost:8000](http://localhost:8000)
- Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)

Pass an LLM key if you want live model calls:

```bash
export LLM_API_KEY=your-key-here
docker compose up --build
```

### Stop

```bash
docker compose down
```

---

## 17. Demo customer scenarios

| # | Scenario | Customer | Expected path |
|---|----------|----------|---------------|
| 1 | Duplicate charge | `CUST-001` | classify → billing → detect duplicates → refund approval → human approve → final reply |
| 2 | Forgot password | `CUST-002` | classify → account → password reset → final reply |
| 3 | PDF upload crash | `CUST-003` | classify → technical → knowledge base → troubleshooting / ticket |
| 4 | Undocumented question | any | classify → general → insufficient knowledge → create ticket |

### What “working correctly” looks like

| Check | Expected result |
|-------|-----------------|
| Health endpoint | `"status": "ok"` |
| Billing message | `assigned_agent = billing`, approval required |
| Approve refund | `status = approved`, confirmation text |
| Password message | `assigned_agent = account` |
| PDF crash | `assigned_agent = technical` |
| Unknown question | `assigned_agent = general` + `ticket_id` |

---

## 18. LangSmith (optional)

LangSmith is **not required** for local development.

To enable tracing:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_PROJECT=ai-customer-support
```

When enabled, you can inspect:

- Graph node runs
- Tool calls
- Errors
- Latency

When disabled, the app still works normally.

---

## 19. Safety rules

The system is designed to:

1. Never invent transaction or customer data
2. Never claim a refund completed unless it was approved and recorded
3. Never expose API keys or internal prompts
4. Never run arbitrary SQL from customer text
5. Require human approval for refunds and sensitive account changes
6. Escalate unknown issues with support tickets instead of hallucinating policies

---

## 20. Future improvements

Possible next steps:

- Simple web chat UI for customers and an approval console for agents
- Vector database for smarter knowledge search
- Real payment-provider integration
- Streaming responses (SSE/WebSockets)
- Authentication and roles for the approval API
- Postgres-backed LangGraph checkpointer for production HITL scale

---

## Quick start cheat sheet

```bash
cd ai-customer-support
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
mkdir -p data
export DATABASE_URL=sqlite+aiosqlite:///./data/support.db
python scripts/seed_database.py
uvicorn app.main:app --reload --port 8000
```

Then open **http://localhost:8000/docs** and test the APIs in Swagger.

---

## Related files

| File | Purpose |
|------|---------|
| `README.md` | Short project overview |
| `DOCUMENTATION.md` | This full guide |
| `.env.example` | Environment template |
| `scripts/seed_database.py` | Demo data loader |
| `docker-compose.yml` | Docker run config |

If you want a shorter version for interviews/portfolios, use `README.md`.  
If you want full setup and testing detail, use this `DOCUMENTATION.md`.

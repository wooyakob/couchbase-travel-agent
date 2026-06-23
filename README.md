# ACME Travel Assistant

A governed, stateful AI agent for planning your dream Caribbean vacation. Ask about hotels, check the weather, compare currencies, and book trips — all through a conversational chat interface powered by LangGraph + AgentC on Couchbase Capella.

## What It Does

The ACME Travel Assistant is a ReAct agent that helps users research and book travel. It remembers your preferences across sessions, searches hotel inventory with vector search, checks live weather and currency rates, and enforces company travel policies via RAG. Every interaction is traced and versioned through Couchbase's AgentC catalog.

**Tools available to the agent:**
- **Hotels** — SQL++ and semantic vector search across the hotel inventory
- **Weather** — Live forecasts via OpenWeatherMap
- **Currency** — Live conversion rates via CurrencyFreaks
- **Policies** — RAG retrieval of company travel policies
- **Memory** — Persists your preferences and trip bookings across sessions

---

## External Prerequisites

Before setting up the cluster, ensure you have:

- [ ] An active **OpenAI integration** in your Capella tenant (AIServices → Integration)
- [ ] The **OpenAI API key** for that integration
- [ ] An **S3 integration** in your tenant linked to the **aiserviceshol** bucket
- [ ] An active [OpenWeatherMap API key](https://openweathermap.org/api)
- [ ] An active [CurrencyFreaks API key](https://currencyfreaks.com)

---

## Capella Infrastructure Setup

### Cluster

- [ ] Create a fresh Capella cluster (**Multi-Node**, on **AWS**, on **8.0+**, with **Search and Eventing**, on **Dev Pro** plan)
- [ ] Import the **travel-sample** bucket
- [ ] Create a dedicated bucket named **agent_catalog**

### Security

- [ ] Add your allowed IP
- [ ] Create the **Agentic_Developer_Role** (All privileges)
- [ ] Create user **acme_user** with the password from your `env_template` and assign the new role
- [ ] Download the Root Certificate and rename it **cert.pem**

### Scopes & Collections

- [ ] In `travel-sample`, create scope/collection **persistence.memory** (preferences and history)
- [ ] In `travel-sample`, create scope/collection **company.policies** (RAG policy data)

### SQL++ Indices

- [ ] Create the memory index on `persistence.memory(user_id)`:

```sql
CREATE INDEX idx_memory_user ON `travel-sample`.persistence.memory(user_id);
```

---

## Capella AI Services Setup

### Sentiment Analysis

- [ ] Deploy the **Analyze Sentiment** AI Function using the OpenAI integration (**gpt-4o**)

### Vector Embedding Workflows

- [ ] Create a workflow with **Data from Capella** on `inventory.hotel`
  - Custom mapping: field `description` → `v_description`
  - Model: OpenAI **text-embedding-3-small**

- [ ] Create a workflow with **Unstructured Data from External Sources** to chunk the PDF policy document and populate `company.policies`
  - Model: OpenAI **text-embedding-3-small**

---

## Local Setup

### 1. Place your certificate

Upload your **cert.pem** file to the root of this repository.

### 2. Configure environment variables

```bash
cp env_template .env
```

Edit `.env` with your API keys and cluster connection strings:

```
OPENAI_API_KEY=...
OPENWEATHER_API_KEY=...
CURRENCYFREAKS_API_KEY=...

CB_CONNECTION_STRING=couchbases://cb...
CB_USERNAME=acme_user
CB_PASSWORD=...

AGENT_CATALOG_CONN_STRING=couchbases://cb...
AGENT_CATALOG_USERNAME=acme_user
AGENT_CATALOG_PASSWORD=...
AGENT_CATALOG_CONN_ROOT_CERTIFICATE=cert.pem
```

### 3. Activate the environment

```bash
export $(grep -v '^#' .env | xargs)
export PYTHONPATH=$PYTHONPATH:.
source venv/bin/activate
```

### 4. Initialize the AgentC catalog

```bash
agentc init
./update_hook.sh
```

### 5. Publish tools and prompts to the catalog

**Option A** — commit your code (the post-commit hook runs automatically):

```bash
git add . && git commit -m "Resurrecting assets: version 1.0"
```

**Option B** — trigger the hook manually without a commit:

```bash
.git/hooks/post-commit
```

---

## Running the App

### Full stack — chat interface (recommended)

Open two terminals:

```bash
# Terminal 1 — FastAPI backend
uvicorn api:app --reload --port 8000

# Terminal 2 — Next.js frontend
cd frontend && npm run dev
```

Then open **http://localhost:3000** in your browser.

The chat interface streams tool calls live as the agent works — watch it search hotels, check the weather, and look up policy details in real time.

### CLI only

```bash
python travel_agent.py
```

---

## Example Conversations

**Session 1: Finding a hotel**
```
You: Hi, I'm planning a Caribbean vacation. Can you find me a hotel in the Bahamas?
You: I prefer modern beachfront resorts with a pool.
```

**Session 2: Picking dates**
```
You: I want to go to Barbados. What's the weather like next week?
You: Which day looks best for arrival — Monday or Wednesday?
You: Book the top-rated hotel for Monday.
```

**Session 3: Budget planning**
```
You: I'm back! Where did I go last time?
You: I need to stay under $200/night this trip. What fits my usual preferences?
You: What's the exchange rate for USD to BBD?
```

---

## Architecture

| Component | Description |
|---|---|
| `travel_agent.py` | CLI entry point. `TravelAssistant` extends `agentc_langgraph.agent.ReActAgent`; wraps each session in an `agentc.Span` for tracing |
| `api.py` | FastAPI backend. Exposes `/api/chat` as an SSE stream emitting `tool_call`, `message`, and `done` events |
| `frontend/` | Next.js 14 app. Streams tool call events live via `ToolCallCard`; renders final responses via `MessageBubble` |
| `tools_and_prompts/` | `@agentc.catalog.tool`-decorated functions; versioned by AgentC |
| `services/` | `CouchbaseService` (cluster connection) and `OpenAIService` (embeddings + sentiment) singletons |

### Data layout in Couchbase

| Bucket | Scope.Collection | Purpose |
|---|---|---|
| `travel-sample` | `inventory.hotel` | Hotel docs with `v_description` vector embeddings |
| `travel-sample` | `persistence.memory` | User preferences and trip bookings |
| `travel-sample` | `company.policies` | Chunked policy PDF with vector embeddings |
| `agent_catalog` | (AgentC-managed) | Versioned tool and prompt snapshots |

Vector queries use `APPROX_VECTOR_DISTANCE(field, $embedding, "L2")` in SQL++.

### Tracing

Every session opens an `agentc.Span`. All tool calls and messages are logged to `.agent-activity/activity.log` and published to the `agent_catalog` bucket for deeper analysis with SQL++.

---

## Updating Tools or Prompts

After any change to `tools_and_prompts/`, re-index and publish:

```bash
agentc index tools_and_prompts/
agentc publish --bucket agent_catalog
```

The post-commit hook does this automatically. To test an individual tool in isolation:

```bash
python tools_and_prompts/hotels.py
python tools_and_prompts/memory.py
python tools_and_prompts/weather.py
python tools_and_prompts/currency.py
python tools_and_prompts/policies.py
python services/couchbase_service.py   # connection ping
```

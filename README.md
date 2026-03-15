# OceanSwarm

A live, persistent AI agent ecosystem where autonomous agents powered by Claude interact in a shared world. Agents perceive their environment, take actions, form memories, and evolve over time — emergent behavior arises from simple rules.

## Requirements

- Python 3.11+
- An Anthropic API key **or** a Claude.ai Pro subscription

## Setup

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Configure environment
cp .env.example .env
```

Edit `.env` and set your credentials:

```env
# Option A: API key
ANTHROPIC_API_KEY=sk-ant-...

# Option B: leave blank — Claude Code will use your Claude.ai Pro subscription
ANTHROPIC_API_KEY=
```

## Running the server

```bash
.venv/bin/uvicorn main:app --reload
```

The interactive API docs are available at **http://localhost:8000/docs**.

## Running the simulation

### 1. Spawn agents

```bash
curl -X POST http://localhost:8000/agents/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Mira", "age": 28, "gender": "female", "personality_prompt": "curious and friendly"}'

curl -X POST http://localhost:8000/agents/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Kael", "age": 35, "gender": "male", "personality_prompt": "cautious and resourceful"}'
```

### 2. Inject world events (optional)

```bash
curl -X POST http://localhost:8000/world/events \
  -H "Content-Type: application/json" \
  -d '{"event_type": "drought"}'
```

Available predefined events: `market_crash`, `market_boom`, `storm`, `drought`, `war`, `peace`, `plague`.
Custom events are also supported — just add a `description` field.

### 3. Run ticks

**Manual** — one tick at a time, useful for development:

```bash
curl -X POST http://localhost:8000/simulation/tick
```

**Clock-based** — runs automatically on an interval:

```bash
# Start (uses TICK_INTERVAL_SECONDS from .env, default 30s)
curl -X POST http://localhost:8000/simulation/start

# Start with a custom interval
curl -X POST http://localhost:8000/simulation/start \
  -H "Content-Type: application/json" \
  -d '{"interval_seconds": 10}'

# Stop
curl -X POST http://localhost:8000/simulation/stop
```

### 4. Observe the simulation

```bash
# Current state of all agents
curl http://localhost:8000/agents/

# Simulation status (tick count, running state)
curl http://localhost:8000/simulation/status

# Action log (last 50 actions across all ticks)
curl http://localhost:8000/simulation/logs

# Filter by tick or agent
curl "http://localhost:8000/simulation/logs?tick=3"
curl "http://localhost:8000/simulation/logs?agent_id=<id>"

# Active world events
curl "http://localhost:8000/world/events?active_only=true"
```

### 5. Real-time stream (WebSocket)

```bash
# Requires wscat: npm install -g wscat
wscat -c ws://localhost:8000/ws
```

Each tick pushes a summary:

```json
{
  "tick": 4,
  "agents_processed": 2,
  "actions": [
    {
      "agent_id": "...",
      "agent_name": "Mira",
      "action": "move",
      "parameters": {"direction": "north"},
      "message": null
    },
    {
      "agent_id": "...",
      "agent_name": "Kael",
      "action": "gather",
      "parameters": {"resource": "food"},
      "message": "Anyone need food?"
    }
  ]
}
```

## Running tests

```bash
pytest
# or with coverage
pytest --cov=. --cov-report=term-missing
```

## Project structure

```
oceanswarm/
├── config.py                 # Settings loaded from .env
├── main.py                   # FastAPI app entry point
├── db/
│   ├── database.py           # SQLAlchemy async engine
│   └── models.py             # ORM models (Agent, WorldEvent, TickLog…)
├── agents/
│   ├── schemas.py            # Pydantic schemas (input/output contracts)
│   ├── actions.py            # Action resolution and energy costs
│   ├── memory.py             # Rolling memory window
│   └── llm.py                # Claude prompt builder and async API call
├── simulation/
│   ├── world.py              # Grid, proximity detection, spawn logic
│   ├── events.py             # Predefined world events
│   └── engine.py             # Tick orchestrator (clock-based + manual)
├── api/
│   ├── routes/
│   │   ├── agents.py         # Agent CRUD endpoints
│   │   ├── world.py          # World event endpoints
│   │   └── simulation.py     # Tick control and logs
│   └── websocket.py          # Real-time broadcast to WebSocket clients
└── tests/                    # 29 unit and integration tests
```

## License

MIT

"""LLM integration: calls the claude CLI using your Claude.ai Pro subscription."""
import asyncio
import json
import logging
import os

from agents.schemas import AgentAction, AgentContext

logger = logging.getLogger(__name__)

# JSON schema sent to --json-schema so Claude is forced to return valid structured output
AGENT_RESPONSE_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["move", "communicate", "interact", "idle", "gather"],
        },
        "parameters": {"type": "object"},
        "message": {"type": ["string", "null"]},
        "memory_update": {"type": ["string", "null"]},
        "internal_state": {
            "type": "object",
            "properties": {
                "mood": {"type": "string"},
                "goal": {"type": "string"},
            },
        },
    },
    "required": ["action", "parameters", "internal_state"],
})

SYSTEM_PROMPT = """\
You are an autonomous agent living in a simulated world.
Act in character at all times based on your personality, memories, and current state.
You can only perceive and interact with agents nearby you.
Do NOT reference anything outside the simulation.
Respond ONLY with valid JSON matching the provided schema.
"""


def _available_directions(x: int, y: int) -> list[str]:
    from config import settings
    dirs = []
    if x > 0:
        dirs.append("west")
    if x < settings.world_width - 1:
        dirs.append("east")
    if y > 0:
        dirs.append("north")
    if y < settings.world_height - 1:
        dirs.append("south")
    return dirs


def _build_user_prompt(ctx: AgentContext) -> str:
    nearby = "\n".join(
        f"  - {a.name} (id: {a.id}, distance: {a.distance:.1f}"
        + (f', last said: "{a.last_message}"' if a.last_message else "")
        + ")"
        for a in ctx.nearby_agents
    ) or "  (none)"

    events = "\n".join(f"  - {e}" for e in ctx.world_events) or "  (none)"
    memories = "\n".join(f"  - {m}" for m in ctx.memory) or "  (none)"
    dirs = "|".join(_available_directions(ctx.position["x"], ctx.position["y"]))

    return f"""\
You are {ctx.name}, a {ctx.age}-year-old {ctx.gender}.
Personality: {ctx.personality or "no special personality defined"}

Current state:
  Energy: {ctx.energy:.1f}/100
  Position: ({ctx.position['x']}, {ctx.position['y']})
  Inventory: {ctx.inventory or "empty"}
  Mood: {ctx.internal_state.get('mood', 'neutral')}
  Goal: {ctx.internal_state.get('goal', 'none')}

Recent memories:
{memories}

Active world events:
{events}

Nearby agents:
{nearby}

Decide your next action. Valid actions:
  move        -> parameters: {{"direction": "{dirs}"}}  (available from your position)
  communicate -> parameters: {{"target_id": "<id>", "content": "<text>"}}
  interact    -> parameters: {{"target_id": "<id>", "type": "trade|help|fight"}}
  gather      -> parameters: {{"resource": "food|water|tools"}}
  idle        -> parameters: {{}}
"""


async def generate_tick_summary(tick: int, actions: list[dict]) -> str:
    """Generate a short narrative summary of what happened this tick."""
    lines = []
    for a in actions:
        msg = a.get("message") or a.get("parameters", {}).get("content", "")
        msg_part = f': "{msg[:80]}"' if msg else ""
        lines.append(f"  {a['agent_name']}: {a['action']}{msg_part}")

    prompt = (
        f"Tick {tick} of a life simulation. Here is what each agent did:\n"
        + "\n".join(lines)
        + "\n\nWrite a single short sentence (max 25 words) summarising the social mood and key moment. "
        "Be vivid and observational, like a narrator. No bullet points, no labels."
    )

    cmd = [
        "claude", "-p", prompt,
        "--output-format", "text",
        "--no-session-persistence",
    ]
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            return stdout.decode().strip()
    except Exception as exc:
        logger.warning("Tick summary failed: %s", exc)
    return ""


async def call_llm(ctx: AgentContext) -> tuple[AgentAction, str | None]:
    """Call Claude via the claude CLI. Returns (action, error_message).
    error_message is None on success, or a string describing the failure."""
    prompt = _build_user_prompt(ctx)

    cmd = [
        "claude", "-p", prompt,
        "--system-prompt", SYSTEM_PROMPT,
        "--output-format", "json",
        "--no-session-persistence",
        "--json-schema", AGENT_RESPONSE_SCHEMA,
    ]

    # Strip ANTHROPIC_API_KEY so the CLI uses the Claude.ai Pro subscription
    # (browser OAuth) instead of the API key which requires separate credits.
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error = stderr.decode().strip() or "claude CLI exited with non-zero status"
            msg = f"claude CLI error for agent {ctx.id}: {error}"
            logger.error(msg)
            return AgentAction(action="idle", internal_state=ctx.internal_state), msg

        outer = json.loads(stdout.decode())
        # When --json-schema is used, structured output is in "structured_output".
        # Falls back to "result" (plain text) if schema was not applied.
        data = outer.get("structured_output") or json.loads(outer.get("result", "{}"))
        return AgentAction(**data), None

    except json.JSONDecodeError as exc:
        msg = f"Invalid JSON from claude CLI for agent {ctx.id}: {exc}"
        logger.warning(msg)
        return AgentAction(action="idle", internal_state=ctx.internal_state), msg
    except FileNotFoundError:
        msg = "claude CLI not found — make sure Claude Code is installed and in PATH"
        logger.error(msg)
        return AgentAction(action="idle", internal_state=ctx.internal_state), msg
    except Exception as exc:
        msg = f"Unexpected error for agent {ctx.id}: {type(exc).__name__}: {exc}"
        logger.error(msg)
        return AgentAction(action="idle", internal_state=ctx.internal_state), msg

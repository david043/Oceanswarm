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


async def generate_tick_summary(tick: int, actions: list[dict], prev_summary: str = "") -> str:
    """Generate a short summary of notable events this tick. Returns '' if nothing notable."""
    notable = []
    for a in actions:
        if not a.get("is_alive", True):
            notable.append(f"{a['agent_name']} died (energy {a.get('energy', 0):.1f})")
        elif a["action"] == "communicate":
            msg = a.get("message") or a.get("parameters", {}).get("content", "")
            notable.append(f"{a['agent_name']} said: \"{msg[:80]}\"")
        elif a["action"] == "interact":
            itype = a.get("parameters", {}).get("type", "")
            notable.append(f"{a['agent_name']} {itype or 'interacted'}")
        elif a.get("llm_error"):
            notable.append(f"{a['agent_name']} errored")

    if not notable:
        return ""

    prev_context = f"Last tick: {prev_summary}\n" if prev_summary else ""
    prompt = (
        f"{prev_context}"
        f"Notable events this tick:\n" + "\n".join(f"- {e}" for e in notable) +
        "\n\nWrite 1-2 short bullet points (each max 10 words) summarising only the most important events. "
        "Use plain language. No intro, no labels, just the bullets."
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
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            logger.warning("Tick summary timed out")
            return ""
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
        "--model", "claude-haiku-4-5-20251001",
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
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            msg = f"claude CLI timed out for agent {ctx.id}"
            logger.warning(msg)
            return AgentAction(action="idle", internal_state=ctx.internal_state), msg

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

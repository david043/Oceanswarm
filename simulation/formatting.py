"""Human-readable formatting for tick summaries."""
from datetime import datetime


def format_tick_summary(summary: dict) -> str:
    tick = summary["tick"]
    now = datetime.now().strftime("%H:%M:%S")
    lines = [f"Tick {tick} @ {now}"]

    for a in summary.get("actions", []):
        name = a["agent_name"]
        action = a["action"]
        params = a.get("parameters") or {}

        if action == "move":
            action_str = f"move {params.get('direction', '')}".strip()
        elif action == "interact":
            action_str = f"interact({params.get('type', '')})"
        else:
            action_str = action

        x, y = a.get("x", "?"), a.get("y", "?")
        energy = a.get("energy")
        energy_str = f" ⚡{energy:.1f}" if energy is not None else ""
        line = f"  {name} ({x},{y}){energy_str}: {action_str}"

        msg = a.get("message")
        if msg:
            truncated = msg[:80] + "…" if len(msg) > 80 else msg
            line += f' "{truncated}"'

        if a.get("llm_error"):
            line += f" [ERROR: {a['llm_error']}]"

        lines.append(line)

    return "\n".join(lines)

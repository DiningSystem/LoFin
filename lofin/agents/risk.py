from __future__ import annotations

from lofin.agents.base import Agent, next_message
from lofin.agents.messages import AgentMessage


class RiskAgent(Agent):
    name = "risk"

    async def handle(self, message: AgentMessage) -> list[AgentMessage]:
        filtered = []
        for item in message.payload.get("ranked", []):
            score = float(item.get("score", 0))
            velocity = float(item.get("velocity", 0))
            risk_flags = []
            if velocity > 8:
                risk_flags.append("coordinated_hype_possible")
            if score < 0.25:
                risk_flags.append("low_signal")
            filtered.append({**item, "risk_flags": risk_flags, "risk_score": min(1.0, len(risk_flags) * 0.35)})
        return [next_message("risk", "summarization", "risk.updated", {"ranked": filtered}, message.correlation_id)]

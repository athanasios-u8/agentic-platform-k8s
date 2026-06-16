from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentSpec:
    slug: str
    name: str
    description: str
    role: str
    port: int
    mcp_servers: dict[str, str] = field(default_factory=dict)
    subagents: dict[str, str] = field(default_factory=dict)
    instructions: str = ""

    def card(self, url: str) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "url": url,
            "role": self.role,
            "capabilities": {
                "streaming": True,
                "a2a_json_rpc": True,
                "mcp_servers": list(self.mcp_servers),
                "subagents": list(self.subagents),
            },
        }

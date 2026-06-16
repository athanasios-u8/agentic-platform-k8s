from typing import Any

try:
    from fastmcp import Client
except Exception:  # pragma: no cover - dependency may not be installed during static checks
    Client = None  # type: ignore[assignment]


class MCPClient:
    def __init__(self, servers: dict[str, str]):
        self.servers = servers

    async def list_tools(self) -> dict[str, list[dict[str, Any]]]:
        if Client is None:
            return {name: [] for name in self.servers}
        discovered: dict[str, list[dict[str, Any]]] = {}
        for name, url in self.servers.items():
            try:
                async with Client(url) as client:
                    tools = await client.list_tools()
                    discovered[name] = [
                        {
                            "name": tool.name,
                            "description": getattr(tool, "description", None),
                            "input_schema": getattr(tool, "inputSchema", None),
                        }
                        for tool in tools
                    ]
            except Exception as exc:
                discovered[name] = [{"error": str(exc)}]
        return discovered

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> Any:
        if Client is None:
            raise RuntimeError("fastmcp is not installed.")
        url = self.servers[server_name]
        async with Client(url) as client:
            result = await client.call_tool(tool_name, arguments)
            return getattr(result, "data", result)

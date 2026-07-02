import uvicorn
from fastapi import FastAPI
from fastmcp import FastMCP

from bookstore_agents.common.config import get_port
from bookstore_agents.mcp_servers.upcoming_releases.tools import register_tools


def create_app() -> FastAPI:
    mcp = FastMCP("Upcoming Releases MCP")
    register_tools(mcp)
    mcp_app = mcp.http_app(path="/")

    app = FastAPI(title="Upcoming Releases MCP", lifespan=mcp_app.lifespan)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "upcoming-releases-mcp"}

    @app.get("/readyz")
    async def readyz() -> dict[str, str]:
        return {"status": "ready", "service": "upcoming-releases-mcp"}

    app.mount("/mcp", mcp_app)
    return app


app = create_app()


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=get_port("UPCOMING_RELEASES_MCP_PORT", 8104))


if __name__ == "__main__":
    main()

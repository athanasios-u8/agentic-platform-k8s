import uvicorn
from fastapi import FastAPI
from fastmcp import FastMCP

from bookstore_agents.common.config import get_port
from bookstore_agents.mcp_servers.store_operations.tools import register_tools


def create_app() -> FastAPI:
    mcp = FastMCP("Store Operations MCP")
    register_tools(mcp)
    mcp_app = mcp.http_app(path="/")

    app = FastAPI(title="Store Operations MCP", lifespan=mcp_app.lifespan)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "store-operations-mcp"}

    @app.get("/readyz")
    async def readyz() -> dict[str, str]:
        return {"status": "ready", "service": "store-operations-mcp"}

    app.mount("/mcp", mcp_app)
    return app


app = create_app()


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=get_port("STORE_OPERATIONS_MCP_PORT", 8103))


if __name__ == "__main__":
    main()

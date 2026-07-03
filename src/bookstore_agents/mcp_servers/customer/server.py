import uvicorn
from fastapi import FastAPI
from fastmcp import FastMCP

from bookstore_agents.common.config import get_port
from bookstore_agents.common.observability import instrument_fastapi_app
from bookstore_agents.mcp_servers.customer.tools import register_tools


def create_app() -> FastAPI:
    mcp = FastMCP("Customer MCP")
    register_tools(mcp)
    mcp_app = mcp.http_app(path="/")

    app = FastAPI(title="Customer MCP", lifespan=mcp_app.lifespan)
    instrument_fastapi_app(app, "customer-mcp")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "customer-mcp"}

    @app.get("/readyz")
    async def readyz() -> dict[str, str]:
        return {"status": "ready", "service": "customer-mcp"}

    app.mount("/mcp", mcp_app)
    return app


app = create_app()


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=get_port("CUSTOMER_MCP_PORT", 8102))


if __name__ == "__main__":
    main()

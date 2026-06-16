from bookstore_agents.agents.common.server import create_agent_app, run_app
from bookstore_agents.agents.customer_concierge.agent import get_spec
from bookstore_agents.common.config import get_port

app = create_agent_app(get_spec())


def main() -> None:
    run_app(app, get_port("CUSTOMER_CONCIERGE_AGENT_PORT", 8201))


if __name__ == "__main__":
    main()

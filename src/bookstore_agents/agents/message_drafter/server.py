from bookstore_agents.agents.common.server import create_agent_app, run_app
from bookstore_agents.agents.message_drafter.agent import get_spec
from bookstore_agents.common.config import get_port

app = create_agent_app(get_spec())


def main() -> None:
    run_app(app, get_port("MESSAGE_DRAFTER_AGENT_PORT", 8205))


if __name__ == "__main__":
    main()

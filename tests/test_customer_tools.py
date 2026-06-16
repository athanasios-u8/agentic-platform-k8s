from bookstore_agents.common.schemas import Customer


def test_customer_schema_defaults_preferences() -> None:
    customer = Customer(id=1, name="Maria", email="maria@example.com", loyalty_tier="gold")
    assert customer.preferences == []

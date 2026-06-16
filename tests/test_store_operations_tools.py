from bookstore_agents.common.approvals import WRITE_TOOLS


def test_write_tools_are_approval_gated() -> None:
    assert "create_reservation" in WRITE_TOOLS
    assert "cancel_reservation" in WRITE_TOOLS
    assert "mark_reservation_picked_up" in WRITE_TOOLS
    assert "adjust_inventory" in WRITE_TOOLS
    assert "update_customer_preferences" in WRITE_TOOLS

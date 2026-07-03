from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from bookstore_agents.common.config import get_settings
from bookstore_agents.common.observability import (
    generation_attributes,
    resource_attributes,
    serialize_payload,
    set_span_output,
    start_span,
    tool_attributes,
    workflow_attributes,
)


def _test_tracer():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter, provider.get_tracer("tests")


def test_observability_is_enabled_by_default(monkeypatch):
    monkeypatch.delenv("OBSERVABILITY_ENABLED", raising=False)
    get_settings.cache_clear()

    try:
        assert get_settings().observability_enabled is True
        assert get_settings().observability_capture_content is True
        assert get_settings().observability_content_max_chars == 6000
    finally:
        get_settings.cache_clear()


def test_observability_disabled_is_noop(monkeypatch):
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "false")
    get_settings.cache_clear()
    exporter, tracer = _test_tracer()

    try:
        with start_span("disabled.span", tracer=tracer):
            pass

        assert exporter.get_finished_spans() == ()
    finally:
        get_settings.cache_clear()


def test_resource_attributes_include_service_and_environment(monkeypatch):
    monkeypatch.setenv(
        "OTEL_RESOURCE_ATTRIBUTES",
        "deployment.environment=test,custom.attribute=demo",
    )

    attributes = resource_attributes("catalog-mcp")

    assert attributes["service.name"] == "catalog-mcp"
    assert attributes["service.namespace"] == "bookstore-agents"
    assert attributes["deployment.environment"] == "test"
    assert attributes["custom.attribute"] == "demo"


def test_payload_redaction_and_truncation(monkeypatch):
    monkeypatch.setenv("OBSERVABILITY_CONTENT_MAX_CHARS", "80")
    get_settings.cache_clear()

    try:
        rendered = serialize_payload(
            {
                "api_key": "sk-secret",
                "nested": {"password": "bookstore"},
                "text": "x" * 200,
            }
        )

        assert rendered is not None
        assert "sk-secret" not in rendered
        assert "bookstore" not in rendered
        assert "[REDACTED]" in rendered
        assert rendered.endswith("...[truncated]")
    finally:
        get_settings.cache_clear()


def test_workflow_tool_and_generation_spans_capture_expected_attributes(monkeypatch):
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "true")
    monkeypatch.setenv("OBSERVABILITY_CONTENT_MAX_CHARS", "1000")
    get_settings.cache_clear()
    exporter, tracer = _test_tracer()

    try:
        with start_span(
            "agent.run",
            workflow_attributes(
                agent="customer-concierge",
                event="agent.run",
                input_value="Find a book.",
                session_id="session-demo",
            ),
            tracer=tracer,
        ) as span:
            set_span_output(span, "Done.", trace_output=True)

        with start_span(
            "tool.call",
            tool_attributes(
                server="catalog",
                tool="recommend_books",
                arguments={"prompt": "Find a book."},
            ),
            tracer=tracer,
        ) as span:
            set_span_output(span, [{"title": "Example"}])

        with start_span(
            "llm.openai.responses",
            generation_attributes(
                provider="openai",
                model="gpt-5.5",
                input_value="Prompt",
                agent="Message Drafter",
                operation="responses",
            ),
            tracer=tracer,
        ) as span:
            set_span_output(span, "Polished answer.")

        spans = {span.name: span for span in exporter.get_finished_spans()}
        assert spans["agent.run"].attributes["bookstore.agent"] == "customer-concierge"
        assert spans["agent.run"].attributes["langfuse.session.id"] == "session-demo"
        assert spans["agent.run"].attributes["langfuse.trace.output"] == '"Done."'
        assert spans["tool.call"].attributes["bookstore.tool.name"] == "recommend_books"
        assert spans["tool.call"].attributes["bookstore.mcp.server"] == "catalog"
        assert spans["llm.openai.responses"].attributes["gen_ai.system"] == "openai"
        assert (
            spans["llm.openai.responses"].attributes["langfuse.observation.type"]
            == "generation"
        )
    finally:
        get_settings.cache_clear()

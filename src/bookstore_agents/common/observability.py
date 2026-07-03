import inspect
import json
import logging
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import wraps
from importlib.metadata import PackageNotFoundError, version
from typing import Any, TypeVar

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span, Status, StatusCode, Tracer

from bookstore_agents.common.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_OTLP_TRACES_ENDPOINT = "http://otel-collector:4318/v1/traces"
SERVICE_NAMESPACE = "bookstore-agents"
_REDACTED = "[REDACTED]"
_SENSITIVE_KEY_PARTS = (
    "api_key",
    "authorization",
    "credential",
    "password",
    "secret",
    "token",
)

F = TypeVar("F", bound=Callable[..., Any])

_configured = False
_httpx_instrumented = False


def configure_observability(service_name: str) -> bool:
    global _configured

    settings = get_settings()
    if not settings.observability_enabled:
        return False
    if _configured:
        return True

    try:
        provider = TracerProvider(resource=Resource.create(resource_attributes(service_name)))
        exporter = OTLPSpanExporter(endpoint=_otlp_traces_endpoint())
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _configured = True
        instrument_httpx()
        return True
    except Exception as exc:  # pragma: no cover - defensive startup guard
        logger.warning("OpenTelemetry setup failed for %s: %s", service_name, exc)
        return False


def instrument_fastapi_app(app: FastAPI, service_name: str) -> None:
    configure_observability(service_name)
    if not get_settings().observability_enabled:
        return
    if getattr(app.state, "_bookstore_otel_instrumented", False):
        return
    try:
        FastAPIInstrumentor.instrument_app(app)
        app.state._bookstore_otel_instrumented = True
    except Exception as exc:  # pragma: no cover - defensive startup guard
        logger.warning("FastAPI OpenTelemetry instrumentation failed for %s: %s", service_name, exc)


def instrument_httpx() -> None:
    global _httpx_instrumented

    if _httpx_instrumented or not get_settings().observability_enabled:
        return
    try:
        HTTPXClientInstrumentor().instrument()
        _httpx_instrumented = True
    except Exception as exc:  # pragma: no cover - defensive startup guard
        logger.warning("HTTPX OpenTelemetry instrumentation failed: %s", exc)


def resource_attributes(service_name: str) -> dict[str, str]:
    attributes = _parse_resource_attributes(os.getenv("OTEL_RESOURCE_ATTRIBUTES", ""))
    attributes.setdefault("service.name", service_name)
    attributes.setdefault("service.namespace", SERVICE_NAMESPACE)
    attributes.setdefault("deployment.environment", os.getenv("DEPLOYMENT_ENVIRONMENT", "demo"))
    attributes.setdefault("service.version", _package_version())
    return attributes


def serialize_payload(value: Any) -> str | None:
    settings = get_settings()
    if not settings.observability_capture_content:
        return None

    redacted = _redact(value)
    try:
        rendered = json.dumps(redacted, default=str, ensure_ascii=False, sort_keys=True)
    except TypeError:
        rendered = str(redacted)

    max_chars = max(settings.observability_content_max_chars, 0)
    if max_chars and len(rendered) > max_chars:
        return f"{rendered[:max_chars]}...[truncated]"
    return rendered


@contextmanager
def start_span(
    name: str,
    attributes: dict[str, Any] | None = None,
    *,
    tracer: Tracer | None = None,
) -> Iterator[Span | None]:
    if not get_settings().observability_enabled:
        yield None
        return

    active_tracer = tracer or trace.get_tracer("bookstore_agents")
    with active_tracer.start_as_current_span(name) as span:
        set_span_attributes(span, attributes or {})
        try:
            yield span
        except Exception as exc:
            mark_span_error(span, exc)
            raise


def workflow_attributes(
    *,
    agent: str | None = None,
    event: str | None = None,
    input_value: Any | None = None,
    session_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {}
    if agent:
        attributes["bookstore.agent"] = agent
        attributes["langfuse.trace.name"] = f"{agent}.workflow"
    if event:
        attributes["bookstore.workflow.event"] = event
    if session_id:
        attributes["session.id"] = session_id
        attributes["langfuse.session.id"] = session_id
    if input_value is not None:
        payload = serialize_payload(input_value)
        attributes["bookstore.input"] = payload
        attributes["langfuse.trace.input"] = payload
    if extra:
        attributes.update(extra)
    return attributes


def tool_attributes(
    *,
    server: str,
    tool: str,
    arguments: Any | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = serialize_payload(arguments) if arguments is not None else None
    attributes: dict[str, Any] = {
        "bookstore.mcp.server": server,
        "bookstore.tool.name": tool,
        "gen_ai.tool.name": tool,
        "langfuse.observation.type": "span",
    }
    if payload is not None:
        attributes["bookstore.tool.arguments"] = payload
        attributes["langfuse.observation.input"] = payload
    if extra:
        attributes.update(extra)
    return attributes


def generation_attributes(
    *,
    provider: str,
    model: str,
    input_value: Any,
    agent: str | None = None,
    operation: str = "chat",
) -> dict[str, Any]:
    payload = serialize_payload(input_value)
    attributes: dict[str, Any] = {
        "gen_ai.system": provider,
        "gen_ai.operation.name": operation,
        "gen_ai.request.model": model,
        "langfuse.observation.type": "generation",
        "langfuse.observation.model.name": model,
    }
    if agent:
        attributes["bookstore.agent"] = agent
    if payload is not None:
        attributes["gen_ai.prompt"] = payload
        attributes["langfuse.observation.input"] = payload
    return attributes


def set_span_attributes(span: Span | None, attributes: dict[str, Any]) -> None:
    if span is None or not span.is_recording():
        return
    for key, value in attributes.items():
        if value is None:
            continue
        try:
            span.set_attribute(key, _attribute_value(value))
        except Exception:
            logger.debug("Skipping unsupported span attribute %s", key, exc_info=True)


def set_span_output(span: Span | None, value: Any, *, trace_output: bool = False) -> None:
    payload = serialize_payload(value)
    if payload is None:
        return
    attributes = {
        "bookstore.output": payload,
        "langfuse.observation.output": payload,
    }
    if trace_output:
        attributes["langfuse.trace.output"] = payload
    set_span_attributes(span, attributes)


def mark_span_error(span: Span | None, exc: BaseException) -> None:
    if span is None or not span.is_recording():
        return
    span.record_exception(exc)
    span.set_status(Status(StatusCode.ERROR, str(exc)))


def trace_mcp_tool(server: str, tool: str) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        signature = inspect.signature(func)

        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                arguments = _bind_arguments(signature, args, kwargs)
                attributes = tool_attributes(server=server, tool=tool, arguments=arguments)
                with start_span(f"mcp.tool.{tool}", attributes) as span:
                    result = await func(*args, **kwargs)
                    set_span_output(span, result)
                    return result

            return async_wrapper  # type: ignore[return-value]

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            arguments = _bind_arguments(signature, args, kwargs)
            attributes = tool_attributes(server=server, tool=tool, arguments=arguments)
            with start_span(f"mcp.tool.{tool}", attributes) as span:
                result = func(*args, **kwargs)
                set_span_output(span, result)
                return result

        return wrapper  # type: ignore[return-value]

    return decorator


def _otlp_traces_endpoint() -> str:
    traces_endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    if traces_endpoint:
        return traces_endpoint

    base_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if base_endpoint:
        return f"{base_endpoint.rstrip('/')}/v1/traces"

    return DEFAULT_OTLP_TRACES_ENDPOINT


def _parse_resource_attributes(raw: str) -> dict[str, str]:
    attributes: dict[str, str] = {}
    for item in raw.split(","):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip()
        if key:
            attributes[key] = value.strip()
    return attributes


def _package_version() -> str:
    try:
        return version("bookstore-agents")
    except PackageNotFoundError:
        return "0.1.0"


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key).lower()
            if any(part in key_text for part in _SENSITIVE_KEY_PARTS):
                redacted[str(key)] = _REDACTED
            else:
                redacted[str(key)] = _redact(item)
        return redacted
    if isinstance(value, list | tuple):
        return [_redact(item) for item in value]
    return value


def _attribute_value(value: Any) -> str | bool | int | float | list[str | bool | int | float]:
    if isinstance(value, str | bool | int | float):
        return value
    if isinstance(value, list) and all(
        isinstance(item, str | bool | int | float) for item in value
    ):
        return value
    return str(value)


def _bind_arguments(
    signature: inspect.Signature,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    try:
        bound = signature.bind_partial(*args, **kwargs)
        bound.apply_defaults()
        return dict(bound.arguments)
    except Exception:
        return {"args": args, "kwargs": kwargs}

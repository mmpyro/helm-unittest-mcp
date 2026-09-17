import json
from dataclasses import asdict, is_dataclass
from functools import wraps
from threading import Lock
from typing import Any, Callable, TypeVar

from mcp.server.mcpserver import MCPServer
from mcp_types import ToolAnnotations


F = TypeVar("F", bound=Callable[..., Any])


def _strip_titles(obj: Any) -> Any:
    """Recursively drop auto-generated ``title`` keys from a JSON schema.

    Pydantic derives a title for every property ("Chart Path" for ``chart_path``),
    which carries no information the property name does not already carry and
    costs ~2 kB across the tool surface.
    """
    if isinstance(obj, dict):
        return {k: _strip_titles(v) for k, v in obj.items() if k != "title"}
    if isinstance(obj, list):
        return [_strip_titles(v) for v in obj]
    return obj


def _json_default(o: Any) -> Any:
    if is_dataclass(o) and not isinstance(o, type):
        return asdict(o)
    return str(o)


def to_compact_json(result: Any) -> str:
    """Serialize a tool result as compact JSON.

    The SDK would otherwise pretty-print with ``indent=2`` and additionally send
    the same data again as ``structuredContent``. Returning a ``str`` from the
    registered callable, with ``structured_output=False``, sends it exactly once.
    """
    if isinstance(result, str):
        return result
    return json.dumps(result, default=_json_default, separators=(",", ":"))


class Server:
    _instance = None
    _lock = Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not Server._initialized:
            with Server._lock:
                if not Server._initialized:
                    self._mcp = MCPServer("Helm unittest service")
                    Server._initialized = True

    @property
    def mcp(self) -> MCPServer:
        """Access the underlying MCPServer instance."""
        return self._mcp

    # Convenience methods to access MCPServer functionality directly
    def __getattr__(self, name):
        """Delegate attribute access to the MCPServer instance."""
        return getattr(self._mcp, name)


def tool(
    *,
    read_only: bool = False,
    destructive: bool = False,
    idempotent: bool = False,
) -> Callable[[F], F]:
    """Register a function as an MCP tool with a token-frugal wire format.

    Differs from a bare ``@mcp.tool()`` in three ways:

    * ``structured_output=False`` so no ``outputSchema`` is advertised and the
      result is not serialized a second time as ``structuredContent``.
    * The registered callable returns compact JSON instead of the SDK's
      ``indent=2`` pretty-print.
    * ``title`` keys are stripped from the generated input schema.

    The *original* function is returned to the defining module, so callers and
    tests keep getting the DTOs back rather than a JSON string.
    """

    def decorator(fn: F) -> F:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> str:
            return to_compact_json(fn(*args, **kwargs))

        mcp = Server().mcp
        mcp.add_tool(
            wrapper,
            name=fn.__name__,
            structured_output=False,
            annotations=ToolAnnotations(
                read_only_hint=read_only,
                destructive_hint=destructive,
                idempotent_hint=idempotent,
            ),
        )

        registered = mcp._tool_manager.get_tool(fn.__name__)
        if registered is not None:
            registered.parameters = _strip_titles(registered.parameters)

        return fn

    return decorator

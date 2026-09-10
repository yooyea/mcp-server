"""Tool-scope filtering for the HiAgent Knowledge MCP server.

A deployment may only want a subset of the tools exposed (e.g. restrict a host
to the Wiki tools so the agent reliably searches the Wiki). This module resolves
which tool names stay enabled from an optional allowlist and denylist; the server
registers every tool and then removes the ones this resolver excludes.

Both filters take exact tool names (comma-separated on the CLI / environment):
- allowlist selects the base set (``None`` / empty means "all tools");
- denylist is then subtracted from that base set.

Unknown names are rejected so a typo fails fast instead of silently doing
nothing.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence


def parse_tool_list(raw: str | None) -> list[str] | None:
    """Parse a comma-separated tool list from a CLI value / environment variable.

    Returns ``None`` when unset (argument omitted / empty), so the caller can tell
    "not provided" apart from an explicit empty selection. Surrounding whitespace
    is trimmed and blank entries are dropped.
    """

    if raw is None:
        return None
    names = [name.strip() for name in raw.split(",")]
    return [name for name in names if name]


def resolve_enabled_tools(
    all_tools: Sequence[str],
    *,
    enabled: Iterable[str] | None = None,
    disabled: Iterable[str] | None = None,
) -> list[str]:
    """Resolve the enabled tool names from an allowlist and denylist.

    - ``enabled`` (allowlist) picks the base set; ``None`` means all tools.
    - ``disabled`` (denylist) is subtracted from the base set.

    The returned list preserves ``all_tools`` order. Raises ``ValueError`` listing
    every unknown name found in either filter (so a typo fails fast).
    """

    known = set(all_tools)

    enabled_set = set(enabled) if enabled is not None else None
    disabled_set = set(disabled or ())

    unknown = sorted(((enabled_set or set()) | disabled_set) - known)
    if unknown:
        raise ValueError(
            "unknown tool name(s): "
            + ", ".join(unknown)
            + "; known tools: "
            + ", ".join(all_tools)
        )

    base = list(all_tools) if enabled_set is None else [
        name for name in all_tools if name in enabled_set
    ]
    return [name for name in base if name not in disabled_set]

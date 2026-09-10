from __future__ import annotations

import pytest

from mcp_server_hiagent_knowledge.versions.v3_1_0.tools.filtering import (
    parse_tool_list,
    resolve_enabled_tools,
)

ALL = ("a", "b", "c", "d")


def test_parse_tool_list_none_when_unset() -> None:
    assert parse_tool_list(None) is None


def test_parse_tool_list_splits_and_trims() -> None:
    assert parse_tool_list(" a, b ,c") == ["a", "b", "c"]


def test_parse_tool_list_drops_blank_entries() -> None:
    # An explicit empty / all-blank value yields an empty selection, not None.
    assert parse_tool_list("") == []
    assert parse_tool_list(" , ,") == []


def test_resolve_none_allowlist_keeps_all() -> None:
    assert resolve_enabled_tools(ALL) == ["a", "b", "c", "d"]


def test_resolve_allowlist_selects_base_set_in_original_order() -> None:
    # Order follows all_tools, not the allowlist argument order.
    assert resolve_enabled_tools(ALL, enabled=["c", "a"]) == ["a", "c"]


def test_resolve_empty_allowlist_selects_nothing() -> None:
    assert resolve_enabled_tools(ALL, enabled=[]) == []


def test_resolve_denylist_subtracts() -> None:
    assert resolve_enabled_tools(ALL, disabled=["b", "d"]) == ["a", "c"]


def test_resolve_allowlist_then_denylist() -> None:
    assert resolve_enabled_tools(ALL, enabled=["a", "b", "c"], disabled=["b"]) == [
        "a",
        "c",
    ]


def test_resolve_unknown_enabled_raises() -> None:
    with pytest.raises(ValueError, match="unknown tool name"):
        resolve_enabled_tools(ALL, enabled=["a", "zzz"])


def test_resolve_unknown_disabled_raises() -> None:
    with pytest.raises(ValueError, match="unknown tool name"):
        resolve_enabled_tools(ALL, disabled=["zzz"])


def test_resolve_unknown_error_lists_all_offenders() -> None:
    with pytest.raises(ValueError) as excinfo:
        resolve_enabled_tools(ALL, enabled=["x"], disabled=["y"])
    message = str(excinfo.value)
    assert "x" in message and "y" in message

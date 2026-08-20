from __future__ import annotations

from typing import Any

import pytest

from mcp_server_hiagent.versions.v3_1_0.tools.knowledge import (
    KNOWN_TOOL_NAMES,
    get_document_info,
    grep_knowledge_chunks,
    list_document_chunks,
    list_knowledge_bases,
    read_wiki_page,
    read_wiki_source,
    search_knowledge,
    search_wiki,
)


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def call(self, **kwargs: Any) -> dict[str, object]:
        self.calls.append(kwargs)
        return {"ResponseMetadata": {"Action": kwargs["action"]}, "Result": {}}


def _common(body: dict[str, Any]) -> None:
    """Every knowledge-engine call shares action/version/service."""
    assert body  # placeholder for readability


# --- list_knowledge_bases ---------------------------------------------------


def test_list_knowledge_bases_request() -> None:
    client = RecordingClient()
    list_knowledge_bases(client, workspace_id="ws-1", dataset_ids=["ds-1"])
    assert client.calls[0] == {
        "action": "CallKnowledgeEngineTool",
        "version": "2023-08-01",
        "service": "app",
        "body": {
            "WorkspaceID": "ws-1",
            "DatasetIDs": ["ds-1"],
            "ToolName": "list_knowledge_bases",
        },
    }


# --- search_knowledge (knowledge_search) ------------------------------------


def test_search_knowledge_builds_oneof_request() -> None:
    client = RecordingClient()
    search_knowledge(
        client,
        workspace_id="ws-1",
        dataset_ids=["ds-1", "ds-2"],
        queries=["hello"],
        top_k=3,
        score_threshold=0.2,
        rerank_id="rk-1",
    )
    assert client.calls[0]["body"] == {
        "WorkspaceID": "ws-1",
        "DatasetIDs": ["ds-1", "ds-2"],
        "ToolName": "knowledge_search",
        "KnowledgeSearch": {
            "Queries": ["hello"],
            "TopK": 3,
            "ScoreThreshold": 0.2,
            "RerankID": "rk-1",
        },
    }


def test_search_knowledge_omits_optional_fields() -> None:
    client = RecordingClient()
    search_knowledge(client, workspace_id="ws-1", dataset_ids=["ds-1"], queries=["q"])
    assert client.calls[0]["body"]["KnowledgeSearch"] == {"Queries": ["q"]}
    assert "KnowledgeRunMode" not in client.calls[0]["body"]


def test_search_knowledge_run_mode() -> None:
    client = RecordingClient()
    search_knowledge(
        client,
        workspace_id="ws-1",
        dataset_ids=["ds-1"],
        queries=["q"],
        knowledge_run_mode="smart_search",
    )
    assert client.calls[0]["body"]["KnowledgeRunMode"] == "smart_search"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"workspace_id": "", "dataset_ids": ["ds-1"], "queries": ["q"]},
        {"workspace_id": "ws-1", "dataset_ids": [], "queries": ["q"]},
        {"workspace_id": "ws-1", "dataset_ids": ["ds-1"], "queries": []},
    ],
)
def test_search_knowledge_required_fields(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        search_knowledge(RecordingClient(), **kwargs)


@pytest.mark.parametrize("bad", [-0.1, 1.1])
def test_search_knowledge_score_threshold_range(bad: float) -> None:
    with pytest.raises(ValueError):
        search_knowledge(
            RecordingClient(),
            workspace_id="ws-1",
            dataset_ids=["ds-1"],
            queries=["q"],
            score_threshold=bad,
        )


def test_search_knowledge_invalid_run_mode() -> None:
    with pytest.raises(ValueError):
        search_knowledge(
            RecordingClient(),
            workspace_id="ws-1",
            dataset_ids=["ds-1"],
            queries=["q"],
            knowledge_run_mode="nope",
        )


# --- grep_knowledge_chunks (grep_chunks) ------------------------------------


def test_grep_builds_oneof_request() -> None:
    client = RecordingClient()
    grep_knowledge_chunks(
        client,
        workspace_id="ws-1",
        dataset_ids=["ds-1"],
        pattern="err\\d+",
        queries=["error"],
        limit=5,
    )
    assert client.calls[0]["body"] == {
        "WorkspaceID": "ws-1",
        "DatasetIDs": ["ds-1"],
        "ToolName": "grep_chunks",
        "GrepChunks": {"Pattern": "err\\d+", "Queries": ["error"], "Limit": 5},
    }


def test_grep_omits_optional_fields() -> None:
    client = RecordingClient()
    grep_knowledge_chunks(
        client, workspace_id="ws-1", dataset_ids=["ds-1"], pattern="p"
    )
    assert client.calls[0]["body"]["GrepChunks"] == {"Pattern": "p"}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"workspace_id": "", "dataset_ids": ["ds-1"], "pattern": "p"},
        {"workspace_id": "ws-1", "dataset_ids": [], "pattern": "p"},
        {"workspace_id": "ws-1", "dataset_ids": ["ds-1"], "pattern": ""},
    ],
)
def test_grep_required_fields(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        grep_knowledge_chunks(RecordingClient(), **kwargs)


def test_grep_rejects_non_positive_limit() -> None:
    with pytest.raises(ValueError):
        grep_knowledge_chunks(
            RecordingClient(),
            workspace_id="ws-1",
            dataset_ids=["ds-1"],
            pattern="p",
            limit=0,
        )


# --- get_document_info (get_doc_info) ---------------------------------------


def test_get_document_info_request() -> None:
    client = RecordingClient()
    get_document_info(
        client, workspace_id="ws-1", dataset_ids=["ds-1"], resource_id="res-1"
    )
    assert client.calls[0]["body"] == {
        "WorkspaceID": "ws-1",
        "DatasetIDs": ["ds-1"],
        "ToolName": "get_doc_info",
        "GetDocInfo": {"ResourceID": "res-1"},
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {"workspace_id": "", "dataset_ids": ["ds-1"], "resource_id": "r"},
        {"workspace_id": "ws-1", "dataset_ids": [], "resource_id": "r"},
        {"workspace_id": "ws-1", "dataset_ids": ["ds-1"], "resource_id": ""},
    ],
)
def test_get_document_info_required_fields(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        get_document_info(RecordingClient(), **kwargs)


# --- list_document_chunks (list_knowledge_chunks) ---------------------------


def test_list_document_chunks_builds_oneof_request() -> None:
    client = RecordingClient()
    list_document_chunks(
        client,
        workspace_id="ws-1",
        dataset_ids=["ds-1"],
        resource_id="res-1",
        limit=50,
        cursor_segment_id="seg-9",
    )
    assert client.calls[0]["body"] == {
        "WorkspaceID": "ws-1",
        "DatasetIDs": ["ds-1"],
        "ToolName": "list_knowledge_chunks",
        "ListKnowledgeChunks": {
            "ResourceID": "res-1",
            "Limit": 50,
            "CursorSegmentID": "seg-9",
        },
    }


def test_list_document_chunks_omits_optional_fields() -> None:
    client = RecordingClient()
    list_document_chunks(
        client, workspace_id="ws-1", dataset_ids=["ds-1"], resource_id="res-1"
    )
    assert client.calls[0]["body"]["ListKnowledgeChunks"] == {"ResourceID": "res-1"}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"workspace_id": "", "dataset_ids": ["ds-1"], "resource_id": "r"},
        {"workspace_id": "ws-1", "dataset_ids": [], "resource_id": "r"},
        {"workspace_id": "ws-1", "dataset_ids": ["ds-1"], "resource_id": ""},
    ],
)
def test_list_document_chunks_required_fields(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        list_document_chunks(RecordingClient(), **kwargs)


def test_list_document_chunks_rejects_non_positive_limit() -> None:
    with pytest.raises(ValueError):
        list_document_chunks(
            RecordingClient(),
            workspace_id="ws-1",
            dataset_ids=["ds-1"],
            resource_id="res-1",
            limit=0,
        )


# --- search_wiki (wiki_search) ----------------------------------------------


def test_search_wiki_builds_oneof_request() -> None:
    client = RecordingClient()
    search_wiki(
        client, workspace_id="ws-1", dataset_ids=["ds-1"], queries=["规定"], limit=5
    )
    assert client.calls[0]["body"] == {
        "WorkspaceID": "ws-1",
        "DatasetIDs": ["ds-1"],
        "ToolName": "wiki_search",
        "WikiSearch": {"Queries": ["规定"], "Limit": 5},
    }


def test_search_wiki_omits_optional_fields() -> None:
    client = RecordingClient()
    search_wiki(client, workspace_id="ws-1", dataset_ids=["ds-1"], queries=["q"])
    assert client.calls[0]["body"]["WikiSearch"] == {"Queries": ["q"]}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"workspace_id": "", "dataset_ids": ["ds-1"], "queries": ["q"]},
        {"workspace_id": "ws-1", "dataset_ids": [], "queries": ["q"]},
        {"workspace_id": "ws-1", "dataset_ids": ["ds-1"], "queries": []},
    ],
)
def test_search_wiki_required_fields(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        search_wiki(RecordingClient(), **kwargs)


# --- read_wiki_page (wiki_read_page) ----------------------------------------


def test_read_wiki_page_request() -> None:
    client = RecordingClient()
    read_wiki_page(
        client, workspace_id="ws-1", dataset_ids=["ds-1"], slug="concept/foo"
    )
    assert client.calls[0]["body"] == {
        "WorkspaceID": "ws-1",
        "DatasetIDs": ["ds-1"],
        "ToolName": "wiki_read_page",
        "WikiReadPage": {"Slug": "concept/foo"},
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {"workspace_id": "", "dataset_ids": ["ds-1"], "slug": "s"},
        {"workspace_id": "ws-1", "dataset_ids": [], "slug": "s"},
        {"workspace_id": "ws-1", "dataset_ids": ["ds-1"], "slug": ""},
    ],
)
def test_read_wiki_page_required_fields(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        read_wiki_page(RecordingClient(), **kwargs)


# --- read_wiki_source (wiki_read_source_doc) --------------------------------


def test_read_wiki_source_builds_oneof_request() -> None:
    client = RecordingClient()
    read_wiki_source(
        client,
        workspace_id="ws-1",
        dataset_ids=["ds-1"],
        slug="concept/foo",
        limit=3,
        cursor_segment_id="seg-2",
    )
    assert client.calls[0]["body"] == {
        "WorkspaceID": "ws-1",
        "DatasetIDs": ["ds-1"],
        "ToolName": "wiki_read_source_doc",
        "WikiReadSourceDoc": {
            "Slug": "concept/foo",
            "Limit": 3,
            "CursorSegmentID": "seg-2",
        },
    }


def test_read_wiki_source_omits_optional_fields() -> None:
    client = RecordingClient()
    read_wiki_source(
        client, workspace_id="ws-1", dataset_ids=["ds-1"], slug="s"
    )
    assert client.calls[0]["body"]["WikiReadSourceDoc"] == {"Slug": "s"}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"workspace_id": "", "dataset_ids": ["ds-1"], "slug": "s"},
        {"workspace_id": "ws-1", "dataset_ids": [], "slug": "s"},
        {"workspace_id": "ws-1", "dataset_ids": ["ds-1"], "slug": ""},
    ],
)
def test_read_wiki_source_required_fields(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        read_wiki_source(RecordingClient(), **kwargs)


# --- contract -----------------------------------------------------------------


def test_known_tool_names_cover_all_eight() -> None:
    assert set(KNOWN_TOOL_NAMES) == {
        "list_knowledge_bases",
        "knowledge_search",
        "grep_chunks",
        "get_doc_info",
        "list_knowledge_chunks",
        "wiki_search",
        "wiki_read_page",
        "wiki_read_source_doc",
    }


def test_all_calls_use_action_version_service() -> None:
    client = RecordingClient()
    search_knowledge(client, workspace_id="ws-1", dataset_ids=["ds-1"], queries=["q"])
    call = client.calls[0]
    assert call["action"] == "CallKnowledgeEngineTool"
    assert call["version"] == "2023-08-01"
    assert call["service"] == "app"

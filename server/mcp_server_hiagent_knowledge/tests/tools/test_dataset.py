from __future__ import annotations

from typing import Any

import pytest

from mcp_server_hiagent_knowledge.versions.v3_1_0.tools.dataset import (
    get_dataset,
    list_datasets,
)


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.response = {
            "Result": {"ListDatasets": {
                "Items": [
                    {"DatasetID": "own-1", "WorkspaceID": "ws-1", "IndexTypes": ["Fulltext", "Vector"]},
                    {"DatasetID": "shared-1", "WorkspaceID": "ws-source", "IndexTypes": ["Wiki"]},
                ],
                "NextCursor": "opaque-next",
            }},
        }

    def call(self, **kwargs: Any) -> dict[str, object]:
        self.calls.append(kwargs)
        return self.response


def test_discovery_without_workspace_auto_discovers() -> None:
    client = RecordingClient()
    result = list_datasets(client)
    assert result is client.response
    assert client.calls == [{
        "action": "CallKnowledgeEngineTool",
        "version": "2023-08-01",
        "service": "app",
        "body": {
            "ToolName": "list_datasets",
            "ListDatasets": {},
        },
    }]


@pytest.mark.parametrize("workspace_id", ["", "   "])
def test_discovery_treats_blank_workspace_as_unspecified(workspace_id: str) -> None:
    client = RecordingClient()
    list_datasets(client, workspace_id=workspace_id)
    assert "WorkspaceID" not in client.calls[0]["body"]


def test_discovery_with_workspace_scopes_request() -> None:
    client = RecordingClient()
    list_datasets(client, workspace_id="ws-1")
    assert client.calls[0]["body"] == {
        "WorkspaceID": "ws-1",
        "ToolName": "list_datasets",
        "ListDatasets": {},
    }


def test_discovery_cursor_filter_and_identity() -> None:
    client = RecordingClient()
    list_datasets(
        client, workspace_id="ws-1", user_id="iam-user-1",
        keyword="finance", limit=10, cursor="opaque-next",
    )
    assert client.calls[0]["body"] == {
        "WorkspaceID": "ws-1",
        "ToolName": "list_datasets",
        "UserInfo": {"UserID": "iam-user-1", "UserChannel": "IAM"},
        "ListDatasets": {
            "Filter": {"Keyword": "finance"}, "Limit": 10, "Cursor": "opaque-next",
        },
    }


@pytest.mark.parametrize("ids", [[], ["ds-2", "ds-1", "ds-2"]])
def test_discovery_ids_preserve_empty_and_order(ids: list[str]) -> None:
    client = RecordingClient()
    list_datasets(client, ids=ids)
    assert client.calls[0]["body"]["ListDatasets"] == {"IDs": ids}


def test_discovery_empty_filter_and_cursor_are_forwarded() -> None:
    client = RecordingClient()
    list_datasets(client, keyword="", cursor="")
    assert client.calls[0]["body"]["ListDatasets"] == {
        "Filter": {"Keyword": ""}, "Cursor": "",
    }


@pytest.mark.parametrize("limit", [0, 101])
def test_discovery_leaves_value_validation_to_backend(limit: int) -> None:
    client = RecordingClient()
    list_datasets(client, ids=[], limit=limit)
    assert client.calls[0]["body"]["ListDatasets"] == {"IDs": [], "Limit": limit}


@pytest.mark.parametrize("user_id", ["", "   "])
def test_discovery_rejects_empty_explicit_identity(user_id: str) -> None:
    client = RecordingClient()
    with pytest.raises(ValueError, match="user_id"):
        list_datasets(client, workspace_id="ws-1", user_id=user_id)
    assert not client.calls


def test_discovery_never_sends_removed_shared_tool() -> None:
    """v3.3.0 已删除 list_datasets_with_shared，任何参数组合都不得再发该 ToolName。"""

    client = RecordingClient()
    list_datasets(client, workspace_id="ws-1", keyword="k", limit=5, ids=None)
    body = client.calls[0]["body"]
    assert "ListDatasetsWithShared" not in body
    assert body["ToolName"] != "list_datasets_with_shared"


def test_get_dataset_builds_request() -> None:
    client = RecordingClient()

    get_dataset(client, workspace_id="ws-1", dataset_id="ds-1")

    assert client.calls[0] == {
        "action": "GetDataset",
        "version": "2023-08-01",
        "service": "app",
        "body": {"WorkspaceID": "ws-1", "Id": "ds-1"},
    }


@pytest.mark.parametrize("workspace_id,dataset_id", [("", "ds-1"), ("ws-1", "")])
def test_get_dataset_requires_ids(workspace_id: str, dataset_id: str) -> None:
    with pytest.raises(ValueError):
        get_dataset(RecordingClient(), workspace_id=workspace_id, dataset_id=dataset_id)

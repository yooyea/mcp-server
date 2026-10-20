"""HiAgent Dataset (knowledge base) OpenAPI tools.

These are dependency tools for the knowledge engine: they let callers discover
the ``DatasetIDs`` (and default retrieval parameters) required by the
knowledge-engine capability tools (``search_knowledge`` / ``list_document_chunks``).
"""

from __future__ import annotations

from fastmcp import FastMCP

from mcp_server_hiagent_knowledge.versions.v3_1_0.tools._common import (
    OPENAPI_SERVICE,
    OPENAPI_VERSION,
    OpenAPIClient,
)

# Tool names registered by ``register_dataset_tools`` (single source of truth for
# tool-scope filtering).
DATASET_TOOL_NAMES = ("list_datasets_with_shared", "get_dataset")


def list_datasets_with_shared(
    client: OpenAPIClient,
    *,
    workspace_id: str,
    user_id: str | None = None,
    keyword: str | None = None,
    limit: int | None = None,
    cursor: str | None = None,
    ids: list[str] | None = None,
) -> dict[str, object]:
    """列出当前 Workspace 中 IAM 用户可访问的自有及共享知识库。

    可选值原样交给服务端校验；None 表示不发送，空 IDs 保持为空数组。
    未指定 user_id 时，由服务端解析凭证对应的 IAM 用户。
    """
    if not workspace_id:
        raise ValueError("workspace_id is required")

    arguments: dict[str, object] = {}
    if keyword is not None:
        arguments["Filter"] = {"Keyword": keyword}
    if limit is not None:
        arguments["Limit"] = limit
    if cursor is not None:
        arguments["Cursor"] = cursor
    if ids is not None:
        arguments["IDs"] = ids

    body: dict[str, object] = {
        "WorkspaceID": workspace_id,
        "ToolName": "list_datasets_with_shared",
        "ListDatasetsWithShared": arguments,
    }
    if user_id is not None:
        if not user_id.strip():
            raise ValueError("user_id must be non-empty when provided")
        body["UserInfo"] = {"UserID": user_id, "UserChannel": "IAM"}
    return client.call(
        action="CallKnowledgeEngineTool",
        version=OPENAPI_VERSION,
        service=OPENAPI_SERVICE,
        body=body,
    )


def get_dataset(
    client: OpenAPIClient,
    *,
    workspace_id: str,
    dataset_id: str,
) -> dict[str, object]:
    """Get one dataset, including default retrieval parameters."""

    if not workspace_id:
        raise ValueError("workspace_id is required")
    if not dataset_id:
        raise ValueError("dataset_id is required")
    return client.call(
        action="GetDataset",
        version=OPENAPI_VERSION,
        service=OPENAPI_SERVICE,
        body={"WorkspaceID": workspace_id, "Id": dataset_id},
    )


def register_dataset_tools(mcp: FastMCP, client: OpenAPIClient) -> None:
    """Register dataset tools on a FastMCP server."""

    @mcp.tool(name="list_datasets_with_shared")
    def list_datasets_with_shared_tool(
        workspace_id: str,
        user_id: str | None = None,
        keyword: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        ids: list[str] | None = None,
    ) -> dict[str, object]:
        """发现当前 Workspace 中 IAM 用户可访问的自有及共享知识库。

        返回 Result.ListDatasetsWithShared.Items（含 DatasetID、WorkspaceID、
        IndexTypes）及可选 NextCursor；不返回 Total。后续检索使用返回的 DatasetID。

        参数：
        - workspace_id：当前 Workspace，必填。
        - user_id：可选 IAM 用户 ID；身份渠道固定为 IAM。不传则由服务端解析凭证身份。
        - keyword：可选名称/描述关键词。
        - limit：每页数量，服务端默认 100，范围 1..100。
        - cursor：上一页的 NextCursor；续页保持用户、Workspace、关键词和 limit 不变。
        - ids：可选知识库 ID 列表；空数组返回空，不能与 limit/cursor 同传。

        需要服务端支持知识引擎子工具 list_datasets_with_shared。
        """
        return list_datasets_with_shared(
            client,
            workspace_id=workspace_id,
            user_id=user_id,
            keyword=keyword,
            limit=limit,
            cursor=cursor,
            ids=ids,
        )

    @mcp.tool(name="get_dataset")
    def get_dataset_tool(
        workspace_id: str,
        dataset_id: str,
    ) -> dict[str, object]:
        """获取单个 HiAgent 知识库的详情，含其默认检索参数。"""

        return get_dataset(
            client,
            workspace_id=workspace_id,
            dataset_id=dataset_id,
        )

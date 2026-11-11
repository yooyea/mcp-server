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
DATASET_TOOL_NAMES = ("list_datasets", "get_dataset")


def list_datasets(
    client: OpenAPIClient,
    *,
    workspace_id: str | None = None,
    user_id: str | None = None,
    keyword: str | None = None,
    limit: int | None = None,
    cursor: str | None = None,
    ids: list[str] | None = None,
) -> dict[str, object]:
    """发现调用身份可访问的知识库（自有库 + 可见共享库）。

    传 ``workspace_id`` 时查该空间的自有及可见共享库；不传或只传空白时，
    按调用身份合并其加入的 HiAgent 空间及旧个人空间，并包含这些空间可见的
    共享库，同一 ``DatasetID`` 只返回一次。

    可选值原样交给服务端校验；None 表示不发送，空 ``ids`` 保持为空数组。
    未指定 ``user_id`` 时，由服务端解析凭证对应的 IAM 用户。
    """
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
        "ToolName": "list_datasets",
        "ListDatasets": arguments,
    }
    # 空白与不传等价：服务端只在 WorkspaceID 非空时按指定空间查询。
    if workspace_id is not None and workspace_id.strip():
        body["WorkspaceID"] = workspace_id
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

    @mcp.tool(name="list_datasets")
    def list_datasets_tool(
        workspace_id: str | None = None,
        user_id: str | None = None,
        keyword: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        ids: list[str] | None = None,
    ) -> dict[str, object]:
        """发现调用身份可访问的知识库（自有库与可见共享库），用于取得后续检索
        所需的 ``dataset_ids``。

        返回 Result.ListDatasets.Items（含 DatasetID、Name、Description、
        WorkspaceID、Icon、IndexingTechnique、IndexTypes）及可选 NextCursor；
        不返回 Total。共享库的 WorkspaceID 为源空间。

        参数：
        - workspace_id：可选。传则查该空间的自有及可见共享库；不传或留空时，
          按调用身份自动发现其加入空间及个人空间可见的全部知识库。
        - user_id：可选 IAM 用户 ID；身份渠道固定为 IAM。不传则由服务端解析凭证身份。
        - keyword：可选名称/描述关键词。
        - limit：每页数量，服务端默认 100，范围 1..100。
        - cursor：上一页的 NextCursor；续页保持用户、WorkspaceID、关键词和 limit
          不变，不能复用其它工具或其它参数组合下的游标。
        - ids：可选知识库 ID 列表；空数组返回空，与显式 limit/cursor 互斥。

        需要服务端为 HiAgent v3.3.0 及以上（该版本已把共享库发现并入
        list_datasets，list_datasets_with_shared 子工具已删除）。
        """
        return list_datasets(
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

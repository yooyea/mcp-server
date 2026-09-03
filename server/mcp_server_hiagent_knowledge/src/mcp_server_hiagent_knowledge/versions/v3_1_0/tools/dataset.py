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


def list_datasets(
    client: OpenAPIClient,
    *,
    workspace_id: str,
    page_number: int = 1,
    page_size: int = 20,
) -> dict[str, object]:
    """List datasets (knowledge bases) in a workspace."""

    if not workspace_id:
        raise ValueError("workspace_id is required")
    return client.call(
        action="ListDatasets",
        version=OPENAPI_VERSION,
        service=OPENAPI_SERVICE,
        body={
            "WorkspaceID": workspace_id,
            "PageNumber": page_number,
            "PageSize": page_size,
        },
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
        workspace_id: str,
        page_number: int = 1,
        page_size: int = 20,
    ) -> dict[str, object]:
        """列出某个 workspace 下的 HiAgent 知识库（dataset），供调用方获取知识引擎所需的 DatasetIDs。"""

        return list_datasets(
            client,
            workspace_id=workspace_id,
            page_number=page_number,
            page_size=page_size,
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

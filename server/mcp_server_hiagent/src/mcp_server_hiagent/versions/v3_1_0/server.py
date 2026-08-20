"""FastMCP server definition for HiAgent."""

from __future__ import annotations

from fastmcp import FastMCP

from mcp_server_hiagent.versions.v3_1_0.client import HiAgentOpenAPIClient
from mcp_server_hiagent.versions.v3_1_0.config import load_hiagent_config
from mcp_server_hiagent.versions.v3_1_0.tools import (
    OpenAPIClient,
    register_dataset_tools,
    register_knowledge_tools,
)


def create_mcp_server(client: OpenAPIClient | None = None) -> FastMCP:
    """Create the HiAgent MCP server.

    Credentials are loaded from environment variables at startup (single
    identity). Passing ``client`` injects a fixed OpenAPI client (used by
    tests) instead of building one from the environment.
    """

    hiagent_config = load_hiagent_config()
    openapi_client = client or HiAgentOpenAPIClient(hiagent_config)

    mcp = FastMCP(
        name="hiagent-mcp-server",
        instructions=(
            "HiAgent MCP Server wraps HiAgent Platform OpenAPI capabilities as "
            "MCP tools. Each tool is named after the user-facing capability it "
            "provides rather than the raw OpenAPI action. It provides dataset "
            "discovery (list_datasets, get_dataset, list_knowledge_bases) and the "
            "full knowledge-engine tool set (search_knowledge, "
            "grep_knowledge_chunks, list_document_infos, list_document_chunks, "
            "search_wiki, read_wiki_page, read_wiki_source). It supports stdio "
            "and streamable-http transports and AK/SK authentication only. "
            "Credentials are provided via environment variables "
            "(HIAGENT_TOP_HOST, HIAGENT_ACCESS_KEY_ID, HIAGENT_SECRET_ACCESS_KEY)."
        ),
    )

    @mcp.tool()
    def health_check() -> dict[str, object]:
        """
        检查 HiAgent MCP Server 是否运行、以及必需的 HiAgent OpenAPI 配置是否齐备。
        仅返回状态与各项是否已配置的布尔值，不回显任何凭证明文。
        """

        return {
            "status": "ok",
            "auth": "aksk",
            "configured": hiagent_config.is_configured,
            "top_host_configured": bool(hiagent_config.top_host),
            "account_id_configured": bool(hiagent_config.account_id),
            "access_key_configured": bool(hiagent_config.access_key_id),
            "secret_key_configured": bool(hiagent_config.secret_access_key),
            "region": hiagent_config.region,
            "service": hiagent_config.service,
        }

    register_dataset_tools(mcp, openapi_client)
    register_knowledge_tools(mcp, openapi_client)

    return mcp

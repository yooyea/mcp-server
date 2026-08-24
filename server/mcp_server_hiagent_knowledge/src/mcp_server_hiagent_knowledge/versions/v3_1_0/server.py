"""FastMCP server definition for HiAgent."""

from __future__ import annotations

from fastmcp import FastMCP

from mcp_server_hiagent_knowledge.versions.v3_1_0.client import HiAgentOpenAPIClient
from mcp_server_hiagent_knowledge.versions.v3_1_0.config import load_hiagent_config
from mcp_server_hiagent_knowledge.versions.v3_1_0.tools import (
    OpenAPIClient,
    register_dataset_tools,
    register_knowledge_tools,
)


def create_mcp_server(client: OpenAPIClient | None = None) -> FastMCP:
    """Create the HiAgent Knowledge MCP server.

    Credentials are loaded from environment variables at startup (single
    identity). Passing ``client`` injects a fixed OpenAPI client (used by
    tests) instead of building one from the environment.
    """

    hiagent_config = load_hiagent_config()
    openapi_client = client or HiAgentOpenAPIClient(hiagent_config)

    mcp = FastMCP(
        name="hiagent-knowledge-mcp-server",
        instructions=(
            "HiAgent Knowledge MCP Server exposes a knowledge base (knowledge "
            "engine) as MCP tools. It is scoped to knowledge retrieval — not the "
            "full HiAgent platform — and the knowledge base may evolve into a "
            "standalone product. Each tool is named after the user-facing "
            "capability it provides. It offers knowledge base discovery "
            "(list_datasets, get_dataset, list_knowledge_bases) and the full "
            "knowledge-engine tool set (search_knowledge, grep_knowledge_chunks, "
            "list_document_infos, list_document_chunks, search_wiki, "
            "read_wiki_page, read_wiki_source). It supports stdio and "
            "streamable-http transports and AK/SK authentication only. "
            "Credentials are provided via environment variables "
            "(HIAGENT_TOP_HOST, HIAGENT_ACCESS_KEY_ID, HIAGENT_SECRET_ACCESS_KEY)."
        ),
    )

    @mcp.tool()
    def health_check() -> dict[str, object]:
        """
        Check whether the HiAgent Knowledge MCP server is running and whether
        the required knowledge base OpenAPI configuration is present.
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

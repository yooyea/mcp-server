"""HiAgent Knowledge Engine OpenAPI tools.

The HiAgent OpenAPI exposes knowledge-engine capabilities through a single
``CallKnowledgeEngineTool`` action that behaves as a *oneof dispatcher*: the
``ToolName`` field selects a sub-tool and the request carries a same-named
PascalCase parameter object (e.g. ``KnowledgeSearch``, ``GrepChunks``).

Rather than surface that dispatcher shape verbatim, this module maps each
``(ToolName, parameter-object)`` combination to a **separate MCP tool named after
the user-facing capability**, with a flat argument schema; the handler assembles
the oneof request body with field names kept strictly identical to the OpenAPI
contract (verified against a live top server on 2026-08-20).

Capability tool  -> ToolName            -> parameter object
  list_knowledge_bases  -> list_knowledge_bases  (no argument object)
  search_knowledge      -> knowledge_search      -> KnowledgeSearch
  grep_knowledge_chunks -> grep_chunks           -> GrepChunks
  get_document_info     -> get_doc_info          -> GetDocInfo
  list_document_chunks  -> list_knowledge_chunks -> ListKnowledgeChunks
  search_wiki           -> wiki_search           -> WikiSearch
  read_wiki_page        -> wiki_read_page        -> WikiReadPage
  read_wiki_source      -> wiki_read_source_doc  -> WikiReadSourceDoc
"""

from __future__ import annotations

from collections.abc import Sequence

from fastmcp import FastMCP

from mcp_server_hiagent.versions.v3_1_0.tools._common import (
    OPENAPI_SERVICE,
    OPENAPI_VERSION,
    OpenAPIClient,
)


# The single OpenAPI action every knowledge-engine capability dispatches through.
KNOWLEDGE_ENGINE_ACTION = "CallKnowledgeEngineTool"

# All knowledge-engine sub-tools, keyed by the OpenAPI ``ToolName`` value. All
# eight are implemented and verified against a live top server.
KNOWN_TOOL_NAMES = (
    "list_knowledge_bases",
    "knowledge_search",
    "grep_chunks",
    "get_doc_info",
    "list_knowledge_chunks",
    "wiki_search",
    "wiki_read_page",
    "wiki_read_source_doc",
)

# Valid values for the optional KnowledgeRunMode field.
KNOWLEDGE_RUN_MODES = ("quick", "smart_search", "wiki_search")


def _call_knowledge_engine(
    client: OpenAPIClient,
    *,
    workspace_id: str,
    dataset_ids: Sequence[str],
    tool_name: str,
    parameter_field: str | None = None,
    parameter_object: dict[str, object] | None = None,
    knowledge_run_mode: str | None = None,
    top: int | None = None,
) -> dict[str, object]:
    """Assemble and send a ``CallKnowledgeEngineTool`` oneof request.

    Shared by every capability handler. ``parameter_object`` is placed under the
    PascalCase ``parameter_field`` (e.g. ``KnowledgeSearch``); callers pass the
    already-built object so field names stay strictly aligned with the OpenAPI
    contract. ``list_knowledge_bases`` carries no parameter object.
    """

    if not workspace_id:
        raise ValueError("workspace_id is required")
    if not dataset_ids:
        raise ValueError("dataset_ids must contain at least one dataset id")
    if tool_name not in KNOWN_TOOL_NAMES:
        raise ValueError(
            f"unknown tool_name {tool_name!r}; known tools: {KNOWN_TOOL_NAMES}"
        )
    if knowledge_run_mode is not None and knowledge_run_mode not in KNOWLEDGE_RUN_MODES:
        raise ValueError(f"knowledge_run_mode must be one of {KNOWLEDGE_RUN_MODES}")

    body: dict[str, object] = {
        "WorkspaceID": workspace_id,
        "DatasetIDs": list(dataset_ids),
        "ToolName": tool_name,
    }
    if parameter_field is not None and parameter_object is not None:
        body[parameter_field] = parameter_object
    if knowledge_run_mode is not None:
        body["KnowledgeRunMode"] = knowledge_run_mode
    if top is not None:
        body["Top"] = top

    return client.call(
        action=KNOWLEDGE_ENGINE_ACTION,
        version=OPENAPI_VERSION,
        service=OPENAPI_SERVICE,
        body=body,
    )


# --- capability handlers ----------------------------------------------------


def list_knowledge_bases(
    client: OpenAPIClient,
    *,
    workspace_id: str,
    dataset_ids: Sequence[str],
) -> dict[str, object]:
    """List knowledge bases and the sub-tools each one supports
    (CallKnowledgeEngineTool/list_knowledge_bases).

    Returns each base's ``DatasetID``, ``IndexTypes`` and ``AvailableTools`` so
    callers can discover which capabilities a dataset supports.
    """

    return _call_knowledge_engine(
        client,
        workspace_id=workspace_id,
        dataset_ids=dataset_ids,
        tool_name="list_knowledge_bases",
    )


def search_knowledge(
    client: OpenAPIClient,
    *,
    workspace_id: str,
    dataset_ids: Sequence[str],
    queries: Sequence[str],
    top_k: int | None = None,
    score_threshold: float | None = None,
    rerank_id: str | None = None,
    knowledge_run_mode: str | None = None,
) -> dict[str, object]:
    """Semantic knowledge retrieval (CallKnowledgeEngineTool/knowledge_search)."""

    if not queries:
        raise ValueError("queries must contain at least one query")
    if score_threshold is not None and not 0 <= score_threshold <= 1:
        raise ValueError("score_threshold must be between 0 and 1")

    search: dict[str, object] = {"Queries": list(queries)}
    if top_k is not None:
        search["TopK"] = top_k
    if score_threshold is not None:
        search["ScoreThreshold"] = score_threshold
    if rerank_id:
        search["RerankID"] = rerank_id

    return _call_knowledge_engine(
        client,
        workspace_id=workspace_id,
        dataset_ids=dataset_ids,
        tool_name="knowledge_search",
        parameter_field="KnowledgeSearch",
        parameter_object=search,
        knowledge_run_mode=knowledge_run_mode,
    )


def grep_knowledge_chunks(
    client: OpenAPIClient,
    *,
    workspace_id: str,
    dataset_ids: Sequence[str],
    pattern: str,
    queries: Sequence[str] | None = None,
    limit: int | None = None,
) -> dict[str, object]:
    """Match knowledge chunks by RE2 regex (CallKnowledgeEngineTool/grep_chunks).

    Narrows candidates through retrieval, then applies ``pattern``. Not an
    exhaustive full-dataset scan.
    """

    if not pattern:
        raise ValueError("pattern is required")
    if limit is not None and limit < 1:
        raise ValueError("limit must be at least 1")

    grep: dict[str, object] = {"Pattern": pattern}
    if queries:
        grep["Queries"] = list(queries)
    if limit is not None:
        grep["Limit"] = limit

    return _call_knowledge_engine(
        client,
        workspace_id=workspace_id,
        dataset_ids=dataset_ids,
        tool_name="grep_chunks",
        parameter_field="GrepChunks",
        parameter_object=grep,
    )


def get_document_info(
    client: OpenAPIClient,
    *,
    workspace_id: str,
    dataset_ids: Sequence[str],
    resource_id: str,
) -> dict[str, object]:
    """Read one document's metadata (CallKnowledgeEngineTool/get_doc_info).

    Returns title/type/size/status/segment count/timestamps. Metadata only, not
    document content.
    """

    if not resource_id:
        raise ValueError("resource_id is required")

    return _call_knowledge_engine(
        client,
        workspace_id=workspace_id,
        dataset_ids=dataset_ids,
        tool_name="get_doc_info",
        parameter_field="GetDocInfo",
        parameter_object={"ResourceID": resource_id},
    )


def list_document_chunks(
    client: OpenAPIClient,
    *,
    workspace_id: str,
    dataset_ids: Sequence[str],
    resource_id: str,
    limit: int | None = None,
    cursor_segment_id: str | None = None,
) -> dict[str, object]:
    """List one document's chunks in reading order
    (CallKnowledgeEngineTool/list_knowledge_chunks).

    Walks a single ``resource_id`` sequentially, paging with
    ``cursor_segment_id``.
    """

    if not resource_id:
        raise ValueError("resource_id is required")
    if limit is not None and limit < 1:
        raise ValueError("limit must be at least 1")

    chunks: dict[str, object] = {"ResourceID": resource_id}
    if limit is not None:
        chunks["Limit"] = limit
    if cursor_segment_id:
        chunks["CursorSegmentID"] = cursor_segment_id

    return _call_knowledge_engine(
        client,
        workspace_id=workspace_id,
        dataset_ids=dataset_ids,
        tool_name="list_knowledge_chunks",
        parameter_field="ListKnowledgeChunks",
        parameter_object=chunks,
    )


def search_wiki(
    client: OpenAPIClient,
    *,
    workspace_id: str,
    dataset_ids: Sequence[str],
    queries: Sequence[str],
    limit: int | None = None,
) -> dict[str, object]:
    """Search generated Wiki pages (CallKnowledgeEngineTool/wiki_search).

    Returns Wiki page candidates (with ``Slug``) for navigation, not final
    evidence. Read a page with ``read_wiki_page`` / ``read_wiki_source``.
    """

    if not queries:
        raise ValueError("queries must contain at least one query")
    if limit is not None and limit < 1:
        raise ValueError("limit must be at least 1")

    wiki: dict[str, object] = {"Queries": list(queries)}
    if limit is not None:
        wiki["Limit"] = limit

    return _call_knowledge_engine(
        client,
        workspace_id=workspace_id,
        dataset_ids=dataset_ids,
        tool_name="wiki_search",
        parameter_field="WikiSearch",
        parameter_object=wiki,
    )


def read_wiki_page(
    client: OpenAPIClient,
    *,
    workspace_id: str,
    dataset_ids: Sequence[str],
    slug: str,
) -> dict[str, object]:
    """Read one generated Wiki page by slug
    (CallKnowledgeEngineTool/wiki_read_page).

    Wiki pages are generated navigation material; read the original sources with
    ``read_wiki_source`` before answering with facts.
    """

    if not slug:
        raise ValueError("slug is required")

    return _call_knowledge_engine(
        client,
        workspace_id=workspace_id,
        dataset_ids=dataset_ids,
        tool_name="wiki_read_page",
        parameter_field="WikiReadPage",
        parameter_object={"Slug": slug},
    )


def read_wiki_source(
    client: OpenAPIClient,
    *,
    workspace_id: str,
    dataset_ids: Sequence[str],
    slug: str,
    limit: int | None = None,
    cursor_segment_id: str | None = None,
) -> dict[str, object]:
    """Read the original source chunks referenced by a Wiki page
    (CallKnowledgeEngineTool/wiki_read_source_doc).

    These chunks are the final evidence for facts/numbers/quotes. Page forward
    with ``cursor_segment_id``.
    """

    if not slug:
        raise ValueError("slug is required")
    if limit is not None and limit < 1:
        raise ValueError("limit must be at least 1")

    src: dict[str, object] = {"Slug": slug}
    if limit is not None:
        src["Limit"] = limit
    if cursor_segment_id:
        src["CursorSegmentID"] = cursor_segment_id

    return _call_knowledge_engine(
        client,
        workspace_id=workspace_id,
        dataset_ids=dataset_ids,
        tool_name="wiki_read_source_doc",
        parameter_field="WikiReadSourceDoc",
        parameter_object=src,
    )


def register_knowledge_tools(mcp: FastMCP, client: OpenAPIClient) -> None:
    """Register the knowledge-engine capability tools on a FastMCP server.

    Each capability of the ``CallKnowledgeEngineTool`` dispatcher is exposed as a
    distinct, capability-named MCP tool rather than one generic tool keyed by a
    raw OpenAPI ``ToolName``.
    """

    @mcp.tool(name="list_knowledge_bases")
    def list_knowledge_bases_tool(
        workspace_id: str,
        dataset_ids: list[str],
    ) -> dict[str, object]:
        """List knowledge bases and the sub-tools each supports.

        Returns each base's index types and ``AvailableTools`` (which of
        search_knowledge / grep_knowledge_chunks / get_document_info /
        list_document_chunks / search_wiki / read_wiki_page / read_wiki_source
        it supports).
        """

        return list_knowledge_bases(
            client, workspace_id=workspace_id, dataset_ids=dataset_ids
        )

    @mcp.tool(name="search_knowledge")
    def search_knowledge_tool(
        workspace_id: str,
        dataset_ids: list[str],
        queries: list[str],
        top_k: int | None = None,
        score_threshold: float | None = None,
        rerank_id: str | None = None,
        knowledge_run_mode: str | None = None,
    ) -> dict[str, object]:
        """Search knowledge across datasets and return the most relevant chunks.

        Use ``list_datasets`` / ``list_knowledge_bases`` to discover dataset ids.

        Parameters:
        - workspace_id: workspace the datasets belong to.
        - dataset_ids: dataset ids to search, at least one.
        - queries: natural-language query strings, at least one.
        - top_k: max number of chunks to return.
        - score_threshold: minimum relevance score to keep (0~1).
        - rerank_id: optional rerank model id.
        - knowledge_run_mode: quick / smart_search / wiki_search.
        """

        return search_knowledge(
            client,
            workspace_id=workspace_id,
            dataset_ids=dataset_ids,
            queries=queries,
            top_k=top_k,
            score_threshold=score_threshold,
            rerank_id=rerank_id,
            knowledge_run_mode=knowledge_run_mode,
        )

    @mcp.tool(name="grep_knowledge_chunks")
    def grep_knowledge_chunks_tool(
        workspace_id: str,
        dataset_ids: list[str],
        pattern: str,
        queries: list[str] | None = None,
        limit: int | None = None,
    ) -> dict[str, object]:
        """Match knowledge chunks by an RE2 regular expression.

        Use for exact tokens (error codes, function names, identifiers, fixed
        phrases) when semantic search is insufficient. Narrows candidates first,
        then applies ``pattern`` — not an exhaustive full-dataset scan.

        Parameters:
        - workspace_id: workspace the datasets belong to.
        - dataset_ids: dataset ids to search, at least one.
        - pattern: one RE2 regular expression (no backreferences/lookarounds).
        - queries: optional queries to narrow the candidate set.
        - limit: max number of matches.
        """

        return grep_knowledge_chunks(
            client,
            workspace_id=workspace_id,
            dataset_ids=dataset_ids,
            pattern=pattern,
            queries=queries,
            limit=limit,
        )

    @mcp.tool(name="get_document_info")
    def get_document_info_tool(
        workspace_id: str,
        dataset_ids: list[str],
        resource_id: str,
    ) -> dict[str, object]:
        """Get one document's metadata (title, type, size, status, segment
        count, timestamps). Metadata only — not document content.

        Parameters:
        - workspace_id: workspace the datasets belong to.
        - dataset_ids: dataset ids the document belongs to, at least one.
        - resource_id: the document/resource id (from an earlier tool result).
        """

        return get_document_info(
            client,
            workspace_id=workspace_id,
            dataset_ids=dataset_ids,
            resource_id=resource_id,
        )

    @mcp.tool(name="list_document_chunks")
    def list_document_chunks_tool(
        workspace_id: str,
        dataset_ids: list[str],
        resource_id: str,
        limit: int | None = None,
        cursor_segment_id: str | None = None,
    ) -> dict[str, object]:
        """List one document's knowledge chunks in reading order.

        Unlike ``search_knowledge`` (relevance-ranked), this reads one
        ``resource_id`` sequentially. Page forward with the last returned
        segment id as ``cursor_segment_id``.

        Parameters:
        - workspace_id: workspace the datasets belong to.
        - dataset_ids: dataset ids the resource belongs to, at least one.
        - resource_id: the document/resource whose chunks to list.
        - limit: max number of chunks per page.
        - cursor_segment_id: segment id to continue paging from.
        """

        return list_document_chunks(
            client,
            workspace_id=workspace_id,
            dataset_ids=dataset_ids,
            resource_id=resource_id,
            limit=limit,
            cursor_segment_id=cursor_segment_id,
        )

    @mcp.tool(name="search_wiki")
    def search_wiki_tool(
        workspace_id: str,
        dataset_ids: list[str],
        queries: list[str],
        limit: int | None = None,
    ) -> dict[str, object]:
        """Search generated Wiki pages for concepts and topic pages.

        Returns Wiki page candidates (with ``Slug``) for navigation, not final
        evidence. Read a page with ``read_wiki_page``, then trace originals with
        ``read_wiki_source``.

        Parameters:
        - workspace_id: workspace the datasets belong to.
        - dataset_ids: dataset ids to search, at least one.
        - queries: natural-language query strings, at least one.
        - limit: max number of pages.
        """

        return search_wiki(
            client,
            workspace_id=workspace_id,
            dataset_ids=dataset_ids,
            queries=queries,
            limit=limit,
        )

    @mcp.tool(name="read_wiki_page")
    def read_wiki_page_tool(
        workspace_id: str,
        dataset_ids: list[str],
        slug: str,
    ) -> dict[str, object]:
        """Read one generated Wiki page by slug (structure, summary, content).

        Wiki pages are generated navigation material, not final evidence; read
        original sources with ``read_wiki_source`` before answering with facts.

        Parameters:
        - workspace_id: workspace the datasets belong to.
        - dataset_ids: dataset ids the page belongs to, at least one.
        - slug: the Wiki page slug (from ``search_wiki``).
        """

        return read_wiki_page(
            client,
            workspace_id=workspace_id,
            dataset_ids=dataset_ids,
            slug=slug,
        )

    @mcp.tool(name="read_wiki_source")
    def read_wiki_source_tool(
        workspace_id: str,
        dataset_ids: list[str],
        slug: str,
        limit: int | None = None,
        cursor_segment_id: str | None = None,
    ) -> dict[str, object]:
        """Read the original source chunks referenced by a Wiki page.

        These chunks are the final evidence for facts, numbers, quotations and
        code. Page forward with ``cursor_segment_id``.

        Parameters:
        - workspace_id: workspace the datasets belong to.
        - dataset_ids: dataset ids the page belongs to, at least one.
        - slug: the Wiki page slug whose sources to read.
        - limit: max number of source chunks per page.
        - cursor_segment_id: segment id to continue paging from.
        """

        return read_wiki_source(
            client,
            workspace_id=workspace_id,
            dataset_ids=dataset_ids,
            slug=slug,
            limit=limit,
            cursor_segment_id=cursor_segment_id,
        )

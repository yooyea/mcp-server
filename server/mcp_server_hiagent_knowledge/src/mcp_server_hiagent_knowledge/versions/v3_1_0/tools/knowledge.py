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
  search_knowledge      -> knowledge_search      -> KnowledgeSearch
  grep_knowledge_chunks -> grep_chunks           -> GrepChunks
  list_document_infos   -> list_doc_infos         -> ListDocInfos
  list_document_chunks  -> list_knowledge_chunks -> ListKnowledgeChunks
  search_wiki           -> wiki_search           -> WikiSearch
  read_wiki_page        -> wiki_read_page        -> WikiReadPage
  read_wiki_source      -> wiki_read_source_chunk -> WikiReadSourceChunk

Every sub-tool also accepts an optional ``user_info`` (the OpenAPI ``UserInfo``
end-user identity, ``{"UserID": ..., "UserChannel": ...}``) forwarded verbatim.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from fastmcp import FastMCP

from mcp_server_hiagent_knowledge.versions.v3_1_0.tools._common import (
    OPENAPI_SERVICE,
    OPENAPI_VERSION,
    OpenAPIClient,
)


# The single OpenAPI action every knowledge-engine capability dispatches through.
KNOWLEDGE_ENGINE_ACTION = "CallKnowledgeEngineTool"

# All knowledge-engine sub-tools, keyed by the OpenAPI ``ToolName`` value.
KNOWN_TOOL_NAMES = (
    "knowledge_search",
    "grep_chunks",
    "list_doc_infos",
    "list_knowledge_chunks",
    "wiki_search",
    "wiki_read_page",
    "wiki_read_source_chunk",
)


def _call_knowledge_engine(
    client: OpenAPIClient,
    *,
    workspace_id: str,
    dataset_ids: Sequence[str],
    tool_name: str,
    parameter_field: str | None = None,
    parameter_object: dict[str, object] | None = None,
    user_info: Mapping[str, object] | None = None,
    top: int | None = None,
) -> dict[str, object]:
    """Assemble and send a ``CallKnowledgeEngineTool`` oneof request.

    Shared by every capability handler. ``parameter_object`` is placed under the
    PascalCase ``parameter_field`` (e.g. ``KnowledgeSearch``); callers pass the
    already-built object so field names stay strictly aligned with the OpenAPI
    contract. ``user_info`` is forwarded verbatim as the top-level ``UserInfo``
    end-user identity when provided.

    Argument *values* are not validated here: field ranges, enums and
    cross-field rules are the OpenAPI (KBS) layer's responsibility and are
    version-specific, so the server's ``InvalidParameter.*`` errors are passed
    through to the caller rather than duplicated locally. Only the presence of
    the fields this server must always send (``WorkspaceID`` / ``DatasetIDs`` /
    a known ``ToolName``) is asserted.
    """

    if not workspace_id:
        raise ValueError("workspace_id is required")
    if not dataset_ids:
        raise ValueError("dataset_ids must contain at least one dataset id")
    if tool_name not in KNOWN_TOOL_NAMES:
        raise ValueError(
            f"unknown tool_name {tool_name!r}; known tools: {KNOWN_TOOL_NAMES}"
        )

    body: dict[str, object] = {
        "WorkspaceID": workspace_id,
        "DatasetIDs": list(dataset_ids),
        "ToolName": tool_name,
    }
    if parameter_field is not None and parameter_object is not None:
        body[parameter_field] = parameter_object
    if user_info:
        body["UserInfo"] = dict(user_info)
    if top is not None:
        body["Top"] = top

    return client.call(
        action=KNOWLEDGE_ENGINE_ACTION,
        version=OPENAPI_VERSION,
        service=OPENAPI_SERVICE,
        body=body,
    )


# --- capability handlers ----------------------------------------------------

def search_knowledge(
    client: OpenAPIClient,
    *,
    workspace_id: str,
    dataset_ids: Sequence[str],
    queries: Sequence[str],
    top_k: int | None = None,
    score_threshold: float | None = None,
    rerank_id: str | None = None,
    user_info: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Semantic knowledge retrieval (CallKnowledgeEngineTool/knowledge_search)."""

    if not queries:
        raise ValueError("queries must contain at least one query")

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
        user_info=user_info,
    )


def grep_knowledge_chunks(
    client: OpenAPIClient,
    *,
    workspace_id: str,
    dataset_ids: Sequence[str],
    pattern: str,
    queries: Sequence[str] | None = None,
    limit: int | None = None,
    grep_type: str | None = None,
    resource_ids: Sequence[str] | None = None,
    user_info: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Match knowledge chunks by RE2 regex (CallKnowledgeEngineTool/grep_chunks).

    Narrows candidates through retrieval, then applies ``pattern``. Not an
    exhaustive full-dataset scan. ``grep_type`` selects the scan scope
    (``dataset_ids`` default, or ``resource_ids`` to restrict to specific
    documents named in ``resource_ids``); scope rules are enforced by the
    OpenAPI layer.
    """

    if not pattern:
        raise ValueError("pattern is required")

    grep: dict[str, object] = {"Pattern": pattern}
    if queries:
        grep["Queries"] = list(queries)
    if limit is not None:
        grep["Limit"] = limit
    if grep_type:
        grep["GrepType"] = grep_type
    if resource_ids:
        grep["ResourceIDs"] = list(resource_ids)

    return _call_knowledge_engine(
        client,
        workspace_id=workspace_id,
        dataset_ids=dataset_ids,
        tool_name="grep_chunks",
        parameter_field="GrepChunks",
        parameter_object=grep,
        user_info=user_info,
    )


def list_document_infos(
    client: OpenAPIClient,
    *,
    workspace_id: str,
    dataset_ids: Sequence[str],
    resource_ids: Mapping[str, Sequence[str]],
    user_info: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Read metadata for documents, batched by dataset
    (CallKnowledgeEngineTool/list_doc_infos).

    ``resource_ids`` maps each dataset id to the resource ids to describe; its
    keys must be within ``dataset_ids``. Returns each document's title/type/size/
    status/segment count/timestamps. Metadata only, not document content.
    """

    if not resource_ids:
        raise ValueError("resource_ids must contain at least one dataset entry")
    normalized: dict[str, list[str]] = {}
    for dataset_id, ids in resource_ids.items():
        if not dataset_id:
            raise ValueError("resource_ids keys (dataset ids) must be non-empty")
        id_list = list(ids)
        if not id_list:
            raise ValueError(
                f"resource_ids[{dataset_id!r}] must contain at least one resource id"
            )
        normalized[dataset_id] = id_list

    return _call_knowledge_engine(
        client,
        workspace_id=workspace_id,
        dataset_ids=dataset_ids,
        tool_name="list_doc_infos",
        parameter_field="ListDocInfos",
        parameter_object={"ResourceIDs": normalized},
        user_info=user_info,
    )


def list_document_chunks(
    client: OpenAPIClient,
    *,
    workspace_id: str,
    dataset_ids: Sequence[str],
    resource_id: str,
    limit: int | None = None,
    cursor_segment_id: str | None = None,
    user_info: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """List one document's chunks in reading order
    (CallKnowledgeEngineTool/list_knowledge_chunks).

    Walks a single ``resource_id`` sequentially, paging with
    ``cursor_segment_id``.
    """

    if not resource_id:
        raise ValueError("resource_id is required")

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
        user_info=user_info,
    )


def search_wiki(
    client: OpenAPIClient,
    *,
    workspace_id: str,
    dataset_ids: Sequence[str],
    queries: Sequence[str],
    limit: int | None = None,
    user_info: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Search generated Wiki pages (CallKnowledgeEngineTool/wiki_search).

    Returns Wiki page candidates (with ``Slug``) for navigation, not final
    evidence. Read a page with ``read_wiki_page`` / ``read_wiki_source``.
    """

    if not queries:
        raise ValueError("queries must contain at least one query")

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
        user_info=user_info,
    )


def read_wiki_page(
    client: OpenAPIClient,
    *,
    workspace_id: str,
    dataset_ids: Sequence[str],
    slug: str,
    user_info: Mapping[str, object] | None = None,
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
        user_info=user_info,
    )


def read_wiki_source(
    client: OpenAPIClient,
    *,
    workspace_id: str,
    dataset_ids: Sequence[str],
    slug: str,
    limit: int | None = None,
    overlap: int | None = None,
    cursor_segment_id: str | None = None,
    user_info: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Read the original source chunks referenced by a Wiki page
    (CallKnowledgeEngineTool/wiki_read_source_chunk).

    These chunks are the final evidence for facts/numbers/quotes. ``overlap``
    expands each referenced chunk with adjacent segments for more context. Page
    forward with ``cursor_segment_id``.
    """

    if not slug:
        raise ValueError("slug is required")

    src: dict[str, object] = {"Slug": slug}
    if limit is not None:
        src["Limit"] = limit
    if overlap is not None:
        src["Overlap"] = overlap
    if cursor_segment_id:
        src["CursorSegmentID"] = cursor_segment_id

    return _call_knowledge_engine(
        client,
        workspace_id=workspace_id,
        dataset_ids=dataset_ids,
        tool_name="wiki_read_source_chunk",
        parameter_field="WikiReadSourceChunk",
        parameter_object=src,
        user_info=user_info,
    )


def register_knowledge_tools(mcp: FastMCP, client: OpenAPIClient) -> None:
    """Register the knowledge-engine capability tools on a FastMCP server.

    Each capability of the ``CallKnowledgeEngineTool`` dispatcher is exposed as a
    distinct, capability-named MCP tool rather than one generic tool keyed by a
    raw OpenAPI ``ToolName``.
    """

    @mcp.tool(name="search_knowledge")
    def search_knowledge_tool(
        workspace_id: str,
        dataset_ids: list[str],
        queries: list[str],
        top_k: int | None = None,
        score_threshold: float | None = None,
        rerank_id: str | None = None,
        user_info: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """在一个或多个知识库中检索，返回最相关的知识片段。

        用 ``list_datasets`` 获取知识库 id。

        参数：
        - workspace_id：知识库所属的 workspace。
        - dataset_ids：要检索的知识库 id 列表，至少 1 个。
        - queries：自然语言查询词，至少 1 条。
        - top_k：返回的最大片段数。
        - score_threshold：保留结果的最小相关性分数。
        - rerank_id：可选的重排模型 id。
        - user_info：可选的终端用户身份，{"UserID": ..., "UserChannel": ...}。
        """

        return search_knowledge(
            client,
            workspace_id=workspace_id,
            dataset_ids=dataset_ids,
            queries=queries,
            top_k=top_k,
            score_threshold=score_threshold,
            rerank_id=rerank_id,
            user_info=user_info,
        )

    @mcp.tool(name="grep_knowledge_chunks")
    def grep_knowledge_chunks_tool(
        workspace_id: str,
        dataset_ids: list[str],
        pattern: str,
        queries: list[str] | None = None,
        limit: int | None = None,
        grep_type: str | None = None,
        resource_ids: list[str] | None = None,
        user_info: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """用一条 RE2 正则匹配知识片段。

        用于语义检索不足时的精确 token 定位（错误码、函数名、标识符、固定短语）。
        先召回候选再应用 ``pattern`` —— 不是对全库的穷尽扫描。

        参数：
        - workspace_id：知识库所属的 workspace。
        - dataset_ids：要检索的知识库 id 列表，至少 1 个。
        - pattern：一条 RE2 正则（不支持反向引用/前后瞻）。
        - queries：可选，用于缩小候选集的查询词。
        - limit：命中上限。
        - grep_type：扫描范围，``dataset_ids``（默认）或 ``resource_ids``。
        - resource_ids：限定扫描的文档/资源 id 列表；当 ``grep_type`` 为
          ``resource_ids`` 时必填。
        - user_info：可选的终端用户身份，{"UserID": ..., "UserChannel": ...}。
        """

        return grep_knowledge_chunks(
            client,
            workspace_id=workspace_id,
            dataset_ids=dataset_ids,
            pattern=pattern,
            queries=queries,
            limit=limit,
            grep_type=grep_type,
            resource_ids=resource_ids,
            user_info=user_info,
        )

    @mcp.tool(name="list_document_infos")
    def list_document_infos_tool(
        workspace_id: str,
        dataset_ids: list[str],
        resource_ids: dict[str, list[str]],
        user_info: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """按知识库批量获取一个或多个文档的元数据。

        返回每个文档的标题、类型、大小、状态、分段数与时间戳。仅元数据，非文档内容。

        参数：
        - workspace_id：知识库所属的 workspace。
        - dataset_ids：涉及的知识库 id 列表，至少 1 个。
        - resource_ids：知识库 id -> 该库下文档/资源 id 列表 的映射；
          其 key 必须在 ``dataset_ids`` 内。
        - user_info：可选的终端用户身份，{"UserID": ..., "UserChannel": ...}。
        """

        return list_document_infos(
            client,
            workspace_id=workspace_id,
            dataset_ids=dataset_ids,
            resource_ids=resource_ids,
            user_info=user_info,
        )

    @mcp.tool(name="list_document_chunks")
    def list_document_chunks_tool(
        workspace_id: str,
        dataset_ids: list[str],
        resource_id: str,
        limit: int | None = None,
        cursor_segment_id: str | None = None,
        user_info: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """按阅读顺序列出单个文档的知识片段。

        与 ``search_knowledge``（按相关性排序）不同，本工具顺序遍历一个
        ``resource_id``。用上一页返回的 segment id 作为 ``cursor_segment_id`` 续页。

        参数：
        - workspace_id：知识库所属的 workspace。
        - dataset_ids：资源所属的知识库 id 列表，至少 1 个。
        - resource_id：要列出分片的文档/资源。
        - limit：每页最大片段数。
        - cursor_segment_id：续页游标。
        - user_info：可选的终端用户身份，{"UserID": ..., "UserChannel": ...}。
        """

        return list_document_chunks(
            client,
            workspace_id=workspace_id,
            dataset_ids=dataset_ids,
            resource_id=resource_id,
            limit=limit,
            cursor_segment_id=cursor_segment_id,
            user_info=user_info,
        )

    @mcp.tool(name="search_wiki")
    def search_wiki_tool(
        workspace_id: str,
        dataset_ids: list[str],
        queries: list[str],
        limit: int | None = None,
        user_info: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """搜索生成的 Wiki 页面，用于概念与主题页导航。

        返回 Wiki 页面候选（含 ``Slug``），用于导航而非最终证据。用
        ``read_wiki_page`` 阅读页面，再用 ``read_wiki_source`` 溯源原文。

        参数：
        - workspace_id：知识库所属的 workspace。
        - dataset_ids：要检索的知识库 id 列表，至少 1 个。
        - queries：自然语言查询词，至少 1 条。
        - limit：返回页面上限。
        - user_info：可选的终端用户身份，{"UserID": ..., "UserChannel": ...}。
        """

        return search_wiki(
            client,
            workspace_id=workspace_id,
            dataset_ids=dataset_ids,
            queries=queries,
            limit=limit,
            user_info=user_info,
        )

    @mcp.tool(name="read_wiki_page")
    def read_wiki_page_tool(
        workspace_id: str,
        dataset_ids: list[str],
        slug: str,
        user_info: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """按 slug 读取单个生成的 Wiki 页面（结构、摘要、内容）。

        Wiki 页面是生成的导航材料，非最终证据；在给出事实前先用
        ``read_wiki_source`` 读取原始来源。

        参数：
        - workspace_id：知识库所属的 workspace。
        - dataset_ids：页面所属的知识库 id 列表，至少 1 个。
        - slug：Wiki 页面 slug（来自 ``search_wiki``）。
        - user_info：可选的终端用户身份，{"UserID": ..., "UserChannel": ...}。
        """

        return read_wiki_page(
            client,
            workspace_id=workspace_id,
            dataset_ids=dataset_ids,
            slug=slug,
            user_info=user_info,
        )

    @mcp.tool(name="read_wiki_source")
    def read_wiki_source_tool(
        workspace_id: str,
        dataset_ids: list[str],
        slug: str,
        limit: int | None = None,
        overlap: int | None = None,
        cursor_segment_id: str | None = None,
        user_info: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """读取某个 Wiki 页面引用的原始文档切片。

        这些切片是事实、数字、引文与代码的最终证据。用 ``cursor_segment_id`` 续页。

        参数：
        - workspace_id：知识库所属的 workspace。
        - dataset_ids：页面所属的知识库 id 列表，至少 1 个。
        - slug：要读取来源的 Wiki 页面 slug。
        - limit：每页最大源切片数。
        - overlap：每个引用切片前后各扩展的邻近分段数，用于补充上下文（0 表示不扩展）。
        - cursor_segment_id：续页游标。
        - user_info：可选的终端用户身份，{"UserID": ..., "UserChannel": ...}。
        """

        return read_wiki_source(
            client,
            workspace_id=workspace_id,
            dataset_ids=dataset_ids,
            slug=slug,
            limit=limit,
            overlap=overlap,
            cursor_segment_id=cursor_segment_id,
            user_info=user_info,
        )

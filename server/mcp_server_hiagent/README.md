# HiAgent MCP Server

This MCP server wraps HiAgent Platform OpenAPI capabilities as MCP tools. Each tool is named after the user-facing **capability** it provides rather than the raw OpenAPI action, so the same OpenAPI action can surface as several distinct capability tools. It provides dataset discovery and the full HiAgent knowledge-engine tool set (semantic search, regex grep, document metadata/chunks, and Wiki search/read), and will keep adding more HiAgent OpenAPI capabilities over time.

## Features

- List knowledge bases (datasets) in a workspace, and inspect a single dataset
- Discover a knowledge base's supported sub-tools (`list_knowledge_bases`)
- Search knowledge across datasets by relevance (`search_knowledge`)
- Match chunks by RE2 regex (`grep_knowledge_chunks`)
- Read a document's metadata (`get_document_info`) and its chunks in order (`list_document_chunks`)
- Search generated Wiki pages (`search_wiki`), read a page (`read_wiki_page`), and trace its original source chunks (`read_wiki_source`)
- Report MCP server and OpenAPI configuration state

### Capability-based tool naming

The HiAgent OpenAPI exposes the knowledge engine through a single `CallKnowledgeEngineTool` action that acts as a dispatcher: its `ToolName` field selects a sub-tool and the request carries a same-named PascalCase parameter object. Instead of surfacing that dispatcher shape, this server maps each `(ToolName, parameter object)` combination to its own capability-named MCP tool with a flat argument schema (all eight verified against a live top server on 2026-08-20):

| MCP tool | OpenAPI action | `ToolName` | Parameter object | Capability |
|---|---|---|---|---|
| `list_knowledge_bases` | `CallKnowledgeEngineTool` | `list_knowledge_bases` | — | List KBs + their `AvailableTools` |
| `search_knowledge` | `CallKnowledgeEngineTool` | `knowledge_search` | `KnowledgeSearch` | Relevance search across datasets |
| `grep_knowledge_chunks` | `CallKnowledgeEngineTool` | `grep_chunks` | `GrepChunks` | RE2 regex match over candidate chunks |
| `get_document_info` | `CallKnowledgeEngineTool` | `get_doc_info` | `GetDocInfo` | One document's metadata |
| `list_document_chunks` | `CallKnowledgeEngineTool` | `list_knowledge_chunks` | `ListKnowledgeChunks` | Sequential read of one document's chunks |
| `search_wiki` | `CallKnowledgeEngineTool` | `wiki_search` | `WikiSearch` | Search generated Wiki pages |
| `read_wiki_page` | `CallKnowledgeEngineTool` | `wiki_read_page` | `WikiReadPage` | Read a Wiki page by slug |
| `read_wiki_source` | `CallKnowledgeEngineTool` | `wiki_read_source_doc` | `WikiReadSourceDoc` | Read a Wiki page's original source chunks |

> Note: in HiAgent a *dataset* is a *knowledge base*, so `list_datasets` / `get_dataset` are the "list/inspect knowledge base" capabilities (`list_knowledge_bases` additionally reports each base's `AvailableTools`).

## Setup

### Prerequisites

- Python 3.11 or higher
- API credentials (AK/SK)

### Installation

Run directly from the repository with uvx (recommended):

```bash
uvx --from "git+https://github.com/volcengine/mcp-server#subdirectory=server/mcp_server_hiagent" mcp-server-hiagent
```

Or with uv, from the compatibility path:

```bash
cd mcp-server/server/mcp_server_hiagent
uv run mcp-server-hiagent
```

### Configuration

The server requires the following environment variables:

- `HIAGENT_TOP_HOST`: HiAgent Platform API (volc-top) gateway address, including scheme and port
- `HIAGENT_ACCESS_KEY_ID`: Your HiAgent access key id
- `HIAGENT_SECRET_ACCESS_KEY`: Your HiAgent secret access key

Optional environment variables:

- `HIAGENT_VERSION`: HiAgent OpenAPI compatibility version to use. Defaults to the latest registered version (currently `v3.1.0`). Can also be set per-run with the `--hiagent-version` CLI flag, which takes precedence. Selects a self-contained implementation under `versions/`; supported values: `v3.1.0`
- `HIAGENT_ACCOUNT_ID`: Main account id sent as the `X-Account-Id` query parameter, defaults to `1000000000`
- `HIAGENT_REGION`: Region used in AK/SK V4 signing (not a network address), defaults to `cn-north-1`
- `FASTMCP_CHECK_FOR_UPDATES`: Set to `off` to skip FastMCP's startup update check, which otherwise makes an outbound request and can fail startup in restricted networks
- `MCP_SERVER_HOST`: Bind host for the FastMCP server, streamable-http only (default: `127.0.0.1`)
- `MCP_SERVER_PORT`: Bind port for the FastMCP server, streamable-http only (default: `8000`)
- `STREAMABLE_HTTP_PATH`: Streamable HTTP endpoint path (default: `/mcp`)

## Usage

### Running the Server

The server can be run with either stdio transport (for MCP integration, e.g. the HiAgent STDIO plugin) or streamable-http transport:

```bash
python -m mcp_server_hiagent.main --transport stdio
```

Or:

```bash
python -m mcp_server_hiagent.main --transport streamable-http
```

Select a specific HiAgent OpenAPI version explicitly with `--hiagent-version`
(overrides the `HIAGENT_VERSION` environment variable; defaults to the latest
registered version):

```bash
python -m mcp_server_hiagent.main --hiagent-version v3.1.0
```

### Available Tools

#### health_check

Report the MCP server and OpenAPI configuration state.

```python
health_check()
```

#### list_datasets

List knowledge bases (datasets) in a workspace, so callers can obtain the `DatasetIDs` required by the knowledge engine.

```python
list_datasets(
    workspace_id="workspace_id",
    page_number=1,
    page_size=20,
)
```

Parameters:
- `workspace_id` (required): the workspace id to list datasets for.
- `page_number` (optional): page number (default: 1).
- `page_size` (optional): page size (default: 20).

#### get_dataset

Get information about a single dataset, including its default retrieval parameters.

```python
get_dataset(
    workspace_id="workspace_id",
    dataset_id="dataset_id",
)
```

Parameters:
- `workspace_id` (required): the workspace id the dataset belongs to.
- `dataset_id` (required): the id of the dataset to inspect.

#### list_knowledge_bases

List knowledge bases and the sub-tools each one supports (`AvailableTools`), plus its index types.

```python
list_knowledge_bases(workspace_id="workspace_id", dataset_ids=["dataset_id"])
```

Parameters:
- `workspace_id` (required): the workspace id the datasets belong to.
- `dataset_ids` (required): dataset ids to describe, at least one.

#### search_knowledge

Search knowledge across one or more datasets and return the chunks most relevant to your queries.

```python
search_knowledge(
    workspace_id="workspace_id",
    dataset_ids=["dataset_id"],
    queries=["How to reset my password?"],
    top_k=3,
    score_threshold=0.2,
)
```

Parameters:
- `workspace_id` (required): the workspace id the datasets belong to.
- `dataset_ids` (required): list of dataset ids to search, at least one.
- `queries` (required): list of natural-language query strings, at least one.
- `top_k` (optional): maximum number of results to return.
- `score_threshold` (optional): minimum relevance score to keep (0~1).
- `rerank_id` (optional): rerank model id.
- `knowledge_run_mode` (optional): run mode, one of `quick` / `smart_search` / `wiki_search`.

#### grep_knowledge_chunks

Match knowledge chunks by one RE2 regular expression. Use for exact tokens (error codes, identifiers, fixed phrases) when semantic search is insufficient. Narrows candidates first, then applies the pattern — not an exhaustive full-dataset scan.

```python
grep_knowledge_chunks(
    workspace_id="workspace_id",
    dataset_ids=["dataset_id"],
    pattern="ERR\\d+",
    queries=["error code"],
    limit=10,
)
```

Parameters:
- `workspace_id` (required): the workspace id the datasets belong to.
- `dataset_ids` (required): dataset ids to search, at least one.
- `pattern` (required): one RE2 regular expression (no backreferences/lookarounds).
- `queries` (optional): queries to narrow the candidate set.
- `limit` (optional): maximum number of matches.

#### get_document_info

Get one document's metadata (title, type, size, status, segment count, timestamps). Metadata only — not document content.

```python
get_document_info(
    workspace_id="workspace_id",
    dataset_ids=["dataset_id"],
    resource_id="resource_id",
)
```

Parameters:
- `workspace_id` (required): the workspace id the datasets belong to.
- `dataset_ids` (required): dataset ids the document belongs to, at least one.
- `resource_id` (required): the document/resource id (from an earlier tool result).

#### list_document_chunks

List the knowledge chunks of a single document/resource in reading order. Unlike `search_knowledge` (relevance-ranked for a query), this walks one resource sequentially — useful for browsing a document's full content.

```python
list_document_chunks(
    workspace_id="workspace_id",
    dataset_ids=["dataset_id"],
    resource_id="resource_id",
    limit=50,
)
```

Parameters:
- `workspace_id` (required): the workspace id the datasets belong to.
- `dataset_ids` (required): list of dataset ids the resource belongs to, at least one.
- `resource_id` (required): the document/resource whose chunks to list.
- `limit` (optional): maximum number of chunks per page.
- `cursor_segment_id` (optional): segment id to continue paging from (pass the last returned segment id).

#### search_wiki

Search generated Wiki pages for concepts and topic pages. Returns page candidates (with `Slug`) for navigation, not final evidence.

```python
search_wiki(
    workspace_id="workspace_id",
    dataset_ids=["dataset_id"],
    queries=["reverse acquisition"],
    limit=5,
)
```

Parameters:
- `workspace_id` (required): the workspace id the datasets belong to.
- `dataset_ids` (required): dataset ids to search, at least one.
- `queries` (required): natural-language query strings, at least one.
- `limit` (optional): maximum number of pages.

#### read_wiki_page

Read one generated Wiki page by slug (structure, summary, content). Wiki pages are generated navigation material, not final evidence.

```python
read_wiki_page(
    workspace_id="workspace_id",
    dataset_ids=["dataset_id"],
    slug="concept/reverse-acquisition",
)
```

Parameters:
- `workspace_id` (required): the workspace id the datasets belong to.
- `dataset_ids` (required): dataset ids the page belongs to, at least one.
- `slug` (required): the Wiki page slug (from `search_wiki`).

#### read_wiki_source

Read the original source chunks referenced by a Wiki page — the final evidence for facts, numbers, quotations and code.

```python
read_wiki_source(
    workspace_id="workspace_id",
    dataset_ids=["dataset_id"],
    slug="concept/reverse-acquisition",
    limit=5,
)
```

Parameters:
- `workspace_id` (required): the workspace id the datasets belong to.
- `dataset_ids` (required): dataset ids the page belongs to, at least one.
- `slug` (required): the Wiki page slug whose sources to read.
- `limit` (optional): maximum number of source chunks per page.
- `cursor_segment_id` (optional): segment id to continue paging from.

## MCP Integration

To add this server to your MCP configuration, add the following to your MCP settings file:

```json
{
  "mcpServers": {
    "hiagent": {
      "command": "uvx",
        "args": [
          "--from",
          "git+https://github.com/volcengine/mcp-server#subdirectory=server/mcp_server_hiagent",
          "mcp-server-hiagent"
        ],
      "env": {
        "HIAGENT_TOP_HOST": "http://your-top-host:30040",
        "HIAGENT_ACCESS_KEY_ID": "your-access-key",
        "HIAGENT_SECRET_ACCESS_KEY": "your-secret-key",
        "HIAGENT_ACCOUNT_ID": "1000000000",
        "HIAGENT_REGION": "cn-north-1",
        "FASTMCP_CHECK_FOR_UPDATES": "off"
      }
    }
  }
}
```

This uses the STDIO transport (the default), which the HiAgent MCP plugin launches locally and injects credentials into via its environment-variable table.

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify your AK/SK credentials are correct
   - Check that you have the necessary permissions for the workspace and datasets

2. **Startup Failure in Restricted Networks**
   - Set `FASTMCP_CHECK_FOR_UPDATES=off` to skip FastMCP's outbound update check

3. **Empty or Denied Results**
   - Verify the `workspace_id` and `dataset_ids` are correct
   - Confirm `HIAGENT_TOP_HOST` points to the HiAgent Platform API (volc-top) gateway, not the web or Agent API address

### Logging

The server uses Python's logging module with INFO level by default. You can see detailed logs in the console when running the server.

## License

volcengine/mcp-server is licensed under the [MIT License](https://github.com/volcengine/mcp-server/blob/main/LICENSE).

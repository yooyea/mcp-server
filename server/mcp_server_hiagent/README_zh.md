# HiAgent MCP Server

## 产品描述

HiAgent MCP Server 是一个模型上下文协议（Model Context Protocol）服务器，将 HiAgent 平台 OpenAPI 的能力封装为标准 MCP 工具，供 MCP 客户端（如 Claude Desktop、Cursor，以及 HiAgent 平台的 MCP 插件）使用。每个工具都按其对用户暴露的**能力**命名，而非直接照搬 OpenAPI 的 action 名，因此同一个 OpenAPI action 可以按不同参数组合暴露为多个能力工具。本 Server 持续接入 HiAgent 平台的各类 OpenAPI 能力，当前已提供知识引擎相关工具：列出指定 workspace 下的知识库、查看知识库详情、按相关性检索知识片段，以及按顺序列出某个文档的知识分片；后续将陆续扩展更多能力。

## 分类

其他

## 功能

- 列出指定 workspace 下的知识库列表，并查看单个知识库详情
- 查看某知识库支持的子工具（`list_knowledge_bases`，返回 `AvailableTools`）
- 在一个或多个知识库中按相关性检索知识片段（`search_knowledge`）
- 按 RE2 正则匹配切片（`grep_knowledge_chunks`）
- 批量读取文档元数据（`list_document_infos`）与按顺序读取文档切片（`list_document_chunks`）
- 搜索生成的 Wiki 页面（`search_wiki`）、读取 Wiki 页面（`read_wiki_page`）、溯源 Wiki 引用的原始文档切片（`read_wiki_source`）
- 查看 MCP Server 与 OpenAPI 的配置状态

### 面向能力的工具命名

HiAgent OpenAPI 通过单个 `CallKnowledgeEngineTool` action 以「分发器」形态暴露知识引擎：`ToolName` 字段选择子工具，请求体携带同名 PascalCase 参数对象。本 Server 不直接暴露这种分发器形态，而是把每个 `(ToolName, 参数对象)` 组合映射为一个面向能力命名、参数扁平的独立 MCP 工具（8 个子工具均已在真实 top 服务实测，2026-08-20）：

| MCP 工具 | OpenAPI action | `ToolName` | 参数对象 | 能力 |
|---|---|---|---|---|
| `list_knowledge_bases` | `CallKnowledgeEngineTool` | `list_knowledge_bases` | — | 列知识库及其 `AvailableTools` |
| `search_knowledge` | `CallKnowledgeEngineTool` | `knowledge_search` | `KnowledgeSearch` | 跨知识库按相关性检索 |
| `grep_knowledge_chunks` | `CallKnowledgeEngineTool` | `grep_chunks` | `GrepChunks` | 候选切片内 RE2 正则匹配 |
| `list_document_infos` | `CallKnowledgeEngineTool` | `list_doc_infos` | `ListDocInfos` | 按知识库批量查文档元数据 |
| `list_document_chunks` | `CallKnowledgeEngineTool` | `list_knowledge_chunks` | `ListKnowledgeChunks` | 顺序读取单个文档的分片 |
| `search_wiki` | `CallKnowledgeEngineTool` | `wiki_search` | `WikiSearch` | 搜索生成的 Wiki 页面 |
| `read_wiki_page` | `CallKnowledgeEngineTool` | `wiki_read_page` | `WikiReadPage` | 按 slug 读取 Wiki 页面 |
| `read_wiki_source` | `CallKnowledgeEngineTool` | `wiki_read_source_doc` | `WikiReadSourceDoc` | 读取 Wiki 页引用的原始切片 |

> 说明：HiAgent 中 dataset 即知识库，故 `list_datasets` / `get_dataset` 是「列/查知识库」能力（`list_knowledge_bases` 额外返回各库的 `AvailableTools`）。

## 使用指南

### 前置准备

- Python 3.11+
- UV
- API credentials (AK/SK)

### 安装

克隆仓库：

```bash
git clone git@github.com:volcengine/mcp-server.git
```

### 使用方法

启动服务器：

#### UV

```bash
cd mcp-server/server/mcp_server_hiagent
uv run mcp-server-hiagent

# 使用 streamable-http 模式启动（默认为 stdio）
uv run mcp-server-hiagent -t streamable-http

# 显式指定 HiAgent OpenAPI 版本（覆盖 HIAGENT_VERSION 环境变量；不填默认用最新）
uv run mcp-server-hiagent --hiagent-version v3.1.0
```

使用客户端与服务器交互：

```
Trae | Cursor | Claude Desktop | Cline | HiAgent MCP 插件 | ...
```

## 配置

### 环境变量

以下环境变量可用于配置 MCP 服务器：

| 环境变量 | 描述 | 默认值 |
|---|---|---|
| `HIAGENT_TOP_HOST` | HiAgent Platform API（volc-top）网关地址，含 scheme 与端口 | - |
| `HIAGENT_ACCESS_KEY_ID` | HiAgent 账号 AccessKey ID | - |
| `HIAGENT_SECRET_ACCESS_KEY` | HiAgent 账号 SecretAccessKey | - |
| `HIAGENT_ACCOUNT_ID` | 作为 `X-Account-Id` 查询参数发送的主账号 ID | `1000000000` |
| `HIAGENT_VERSION` | 使用的 HiAgent OpenAPI 兼容版本，对应 `versions/` 下的自包含实现；不填默认使用最新已注册版本（当前为 `v3.1.0`）。也可用 `--hiagent-version` 命令行参数按次指定，且优先级更高；当前支持 `v3.1.0` | 最新（`v3.1.0`） |
| `HIAGENT_REGION` | 用于 AK/SK V4 签名的 Region（非网络地址） | `cn-north-1` |
| `FASTMCP_CHECK_FOR_UPDATES` | 设为 `off`，否则 FastMCP 启动时的联网版本检查在受限网络下可能导致启动失败 | - |
| `MCP_SERVER_HOST` | MCP server 绑定 host（streamable-http） | `127.0.0.1` |
| `MCP_SERVER_PORT` | MCP server 监听端口（streamable-http） | `8000` |

## 可用工具

HiAgent MCP Server 提供以下功能：

- `health_check`: 返回 MCP server 与 OpenAPI 的配置状态
- `list_datasets`: 列出指定 workspace 下的知识库列表
- `get_dataset`: 获取单个知识库的详细信息
- `list_knowledge_bases`: 列出知识库及其支持的子工具（`AvailableTools`）
- `search_knowledge`: 在一个或多个知识库中按相关性检索知识片段
- `grep_knowledge_chunks`: 按 RE2 正则匹配知识切片
- `list_document_infos`: 按知识库批量获取文档元数据
- `list_document_chunks`: 按顺序列出单个文档/资源的知识分片
- `search_wiki`: 搜索生成的 Wiki 页面
- `read_wiki_page`: 按 slug 读取 Wiki 页面
- `read_wiki_source`: 读取 Wiki 页引用的原始文档切片

#### health_check

```python
health_check()
```

#### list_datasets

```python
list_datasets(
    workspace_id="workspace_id",
    page_number=1,
    page_size=20,
)
```

Parameters:
- `workspace_id` (必须): 要列出知识库的 workspace ID
- `page_number` (可选): 页码（默认值：1）
- `page_size` (可选): 每页数量（默认值：20）

#### get_dataset

```python
get_dataset(
    workspace_id="workspace_id",
    dataset_id="dataset_id",
)
```

Parameters:
- `workspace_id` (必须): 知识库所属的 workspace ID
- `dataset_id` (必须): 要获取信息的知识库 ID

#### list_knowledge_bases

```python
list_knowledge_bases(workspace_id="workspace_id", dataset_ids=["dataset_id"])
```

Parameters:
- `workspace_id` (必须): 知识库所属的 workspace ID
- `dataset_ids` (必须): 要描述的知识库 ID 列表，至少 1 个

#### search_knowledge

```python
search_knowledge(
    workspace_id="workspace_id",
    dataset_ids=["dataset_id"],
    queries=["如何重置密码？"],
    top_k=3,
    score_threshold=0.2,
)
```

Parameters:
- `workspace_id` (必须): 知识库所属的 workspace ID
- `dataset_ids` (必须): 要检索的知识库 ID 列表，至少 1 个
- `queries` (必须): 检索查询词列表，至少 1 个
- `top_k` (可选): 返回的最大结果数
- `score_threshold` (可选): 保留结果的最小相关性分数（0~1）
- `rerank_id` (可选): 重排模型 ID
- `knowledge_run_mode` (可选): 运行模式，枚举 `quick` / `smart_search` / `wiki_search`

#### grep_knowledge_chunks

按一条 RE2 正则匹配知识切片；用于错误码、标识符、固定短语等精确定位。先召回候选再匹配，不是全库扫描。

```python
grep_knowledge_chunks(
    workspace_id="workspace_id",
    dataset_ids=["dataset_id"],
    pattern="ERR\\d+",
    queries=["错误码"],
    limit=10,
)
```

Parameters:
- `workspace_id` (必须): 知识库所属的 workspace ID
- `dataset_ids` (必须): 要检索的知识库 ID 列表，至少 1 个
- `pattern` (必须): 一条 RE2 正则（不支持反向引用/前后瞻）
- `queries` (可选): 用于缩小候选集的查询词
- `limit` (可选): 命中上限

#### list_document_infos

按知识库批量获取一个或多个文档的元数据（标题、类型、大小、状态、分段数、时间戳）。仅元数据，非文档内容。

```python
list_document_infos(
    workspace_id="workspace_id",
    dataset_ids=["dataset_id"],
    resource_ids={"dataset_id": ["resource_id_1", "resource_id_2"]},
)
```

Parameters:
- `workspace_id` (必须): 知识库所属的 workspace ID
- `dataset_ids` (必须): 涉及的知识库 ID 列表，至少 1 个
- `resource_ids` (必须): 知识库 ID → 该库下文档/资源 ID 列表的映射；key 必须在 `dataset_ids` 内

#### list_document_chunks

按阅读顺序列出单个文档/资源的知识分片；与 `search_knowledge`（按查询相关性排序）不同，本工具顺序遍历一个资源，适合浏览文档全文。

```python
list_document_chunks(
    workspace_id="workspace_id",
    dataset_ids=["dataset_id"],
    resource_id="resource_id",
    limit=50,
)
```

Parameters:
- `workspace_id` (必须): 知识库所属的 workspace ID
- `dataset_ids` (必须): 资源所属的知识库 ID 列表，至少 1 个
- `resource_id` (必须): 要列出分片的文档/资源 ID
- `limit` (可选): 每页返回的最大分片数
- `cursor_segment_id` (可选): 续页游标，传入上一页返回的最后一个 segment ID

#### search_wiki

搜索生成的 Wiki 页面，返回页面候选（含 `Slug`）用于导航，不作为最终证据。

```python
search_wiki(
    workspace_id="workspace_id",
    dataset_ids=["dataset_id"],
    queries=["反向购买"],
    limit=5,
)
```

Parameters:
- `workspace_id` (必须): 知识库所属的 workspace ID
- `dataset_ids` (必须): 要检索的知识库 ID 列表，至少 1 个
- `queries` (必须): 检索查询词列表，至少 1 个
- `limit` (可选): 返回页面上限

#### read_wiki_page

按 slug 读取单个 Wiki 页面（结构、摘要、内容）。Wiki 页面是生成的导航材料，非最终证据。

```python
read_wiki_page(
    workspace_id="workspace_id",
    dataset_ids=["dataset_id"],
    slug="concept/reverse-acquisition",
)
```

Parameters:
- `workspace_id` (必须): 知识库所属的 workspace ID
- `dataset_ids` (必须): 页面所属的知识库 ID 列表，至少 1 个
- `slug` (必须): Wiki 页面 slug（来自 `search_wiki`）

#### read_wiki_source

读取 Wiki 页引用的原始文档切片——事实、数字、引文、代码的最终证据来源。

```python
read_wiki_source(
    workspace_id="workspace_id",
    dataset_ids=["dataset_id"],
    slug="concept/reverse-acquisition",
    limit=5,
)
```

Parameters:
- `workspace_id` (必须): 知识库所属的 workspace ID
- `dataset_ids` (必须): 页面所属的知识库 ID 列表，至少 1 个
- `slug` (必须): 要读取来源的 Wiki 页面 slug
- `limit` (可选): 每页返回的最大源切片数
- `cursor_segment_id` (可选): 续页游标

## 最佳实践与测试 Prompt

推荐的使用顺序，以及每个透出方法的自然语言测试 Prompt 与期望结果——这些 Prompt 也可作为接入 MCP 客户端后的手工冒烟测试。

**推荐流程：** `health_check`（确认配置）→ `list_datasets` / `list_knowledge_bases`（获取 `DatasetIDs` 及各库 `AvailableTools`）→ 用 `search_knowledge` / `grep_knowledge_chunks` 检索，或用 `search_wiki` → `read_wiki_page` → `read_wiki_source` 导航溯源；用 `list_document_infos` / `list_document_chunks` 查看或阅读指定文档。`WorkspaceID` 无法通过本 Server 列举，需从 HiAgent 控制台网页 URL（`.../workspace/<id>/...`）获取。

#### health_check

- **最佳实践：** 在任何需要凭证的工具之前先调用，确认 Server 已读到 AK/SK 与 top host。不调用 OpenAPI、不回显凭证，只返回布尔值。
- **测试 Prompt：** “检查 HiAgent MCP Server 是否健康、配置是否齐备。”
- **期望结果：** `status="ok"`、`auth="aksk"`，环境变量齐备时 `configured=true` 且各 `*_configured` 为 true；不返回任何凭证明文。

#### list_datasets

- **最佳实践：** 用它获取知识引擎工具所需的 `DatasetIDs`；用 `page_number`/`page_size`（1~100）分页。dataset 即知识库。
- **测试 Prompt：** “列出 workspace `<workspace_id>` 下的知识库。”
- **期望结果：** 分页的知识库列表，每项含 id 与名称。

#### get_dataset

- **最佳实践：** 需要某库默认检索参数（如 `RetrievalTopK`、`RetrievalScoreThreshold`）时调用，使 `search_knowledge` 入参与该库配置一致。
- **测试 Prompt：** “展示 workspace `<workspace_id>` 下知识库 `<dataset_id>` 的详情与默认检索设置。”
- **期望结果：** 该知识库的元数据，含默认检索参数。

#### list_knowledge_bases

- **最佳实践：** 选检索工具前先看某库支持哪些子工具（`AvailableTools`）与 `IndexTypes`——例如只在 `IndexTypes` 含 `wiki` 的库上用 Wiki 类工具。
- **测试 Prompt：** “workspace `<workspace_id>` 下知识库 `<dataset_id>` 支持哪些知识引擎工具？”
- **期望结果：** `KnowledgeBases[]`，每项含 `DatasetID`、`IndexTypes`、`AvailableTools`。

#### search_knowledge

- **最佳实践：** 传 1~5 条简短、可独立理解的 `queries`（不要传整段对话）；`top_k` 从小值（如 3）起步、`score_threshold` 取适中值（如 0.2）再调优。概念/概览类问题优先用它。
- **测试 Prompt：** “在 workspace `<workspace_id>` 的知识库 `[<dataset_id>]` 中检索「如何重置密码？」，返回前 3 个切片。”
- **期望结果：** `KnowledgeSearch.Hits[]`，每个 hit 含 `DatasetID` / `DocumentID` / `ResourceID` / `SegmentID` / `Content` / `Score`；`queries` 为空或 `score_threshold` 越界触发校验错误。

#### grep_knowledge_chunks

- **最佳实践：** 仅用于语义检索找不到的精确 token（错误码、标识符、固定短语）；多候选用 `|` 合并进一条 RE2 `pattern`，可用 `queries` 缩小候选。它在召回候选内匹配，不保证全库查全。
- **测试 Prompt：** “在 workspace `<workspace_id>` 的知识库 `[<dataset_id>]` 中，匹配正则 `ERR\\d{3}` 的切片。”
- **期望结果：** `GrepChunks.Hits[]`（含 resource/segment/content）；缺 `pattern` 触发校验错误。

#### list_document_infos

- **最佳实践：** 一次性按知识库批量取多个文档的元数据；`resource_ids` 的 key 必须在 `dataset_ids` 内。仅元数据，不替代读正文。
- **测试 Prompt：** “展示 workspace `<workspace_id>` 知识库 `<dataset_id>` 下文档 `<res_1>`、`<res_2>` 的标题、类型、大小与状态。”
- **期望结果：** `ListDocInfos.Documents[]`，每项含 `DatasetID` / `ResourceID` / `Title` / `Size` / `Type` / `Status` / `SegmentCount` / 时间戳。

#### list_document_chunks

- **最佳实践：** 在别的工具给出 `resource_id` 后，当你需要上下文或顺序阅读（而非相关性排序）时使用；用返回的 `cursor_segment_id` 续页。
- **测试 Prompt：** “按顺序读取 workspace `<workspace_id>` 知识库 `<dataset_id>` 下文档 `<resource_id>` 的前 20 个切片。”
- **期望结果：** 有序的 `ListKnowledgeChunks.Chunks[]`（含 `Position` / `DocumentName`），未读完时带 `NextCursorSegmentID`。

#### search_wiki

- **最佳实践：** 用简短自然语言 `queries` 定位 Wiki 页面做概念导航；结果是页面候选（含 `Slug`），非最终证据，需再读页面。
- **测试 Prompt：** “在 workspace `<workspace_id>` 知识库 `<dataset_id>` 的 Wiki 中搜索「反向购买」。”
- **期望结果：** `WikiSearch.Pages[]`，每项含 `Slug` / `Title` / `PageType` / `Summary` / `Score`。

#### read_wiki_page

- **最佳实践：** 用 `search_wiki` 返回的 `Slug` 读取页面结构、摘要与关联；页面内容属生成的导航材料，非最终事实证据。
- **测试 Prompt：** “打开 workspace `<workspace_id>` 知识库 `<dataset_id>` 的 Wiki 页面 `concept/reverse-acquisition`。”
- **期望结果：** `WikiReadPage.Page`，含 `Content`、`Aliases`、`InLinks`/`OutLinks`、`SourceRefs`。

#### read_wiki_source

- **最佳实践：** 确定相关 Wiki 页面后，用其 `Slug` 读取原始文档切片——事实、数字、引文、代码的最终证据来源；用 `cursor_segment_id` 续页。
- **测试 Prompt：** “读取 workspace `<workspace_id>` 知识库 `<dataset_id>` 中 Wiki 页面 `concept/reverse-acquisition` 背后的原始文档切片。”
- **期望结果：** `WikiReadSourceDoc.Hits[]`（原始切片），未读完时带 `NextCursorSegmentID`。

### uvx 启动

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

## 证书

volcengine/mcp-server is licensed under the [MIT License](https://github.com/volcengine/mcp-server/blob/main/LICENSE).

# RAG 测评平台

[English](README.md) | **简体中文**

这是一个基于 [deepeval](https://github.com/confident-ai/deepeval) 的浏览器端 RAG 自动化测评平台。用户按照“配置与上传 → 审核测试样本 → 运行评估 → 查看结果”四个步骤，即可完成知识库文档测试样本生成、RAG 服务调用、五项指标评分、结果分析与导出。

## 演示视频

[▶ 观看 RAG-Bench 完整使用演示（MP4，58 MB）](https://github.com/Comui520/RAG-Bench/releases/download/v0.1.0/rag-bench-demo.mp4)

视频展示了模型配置、文档上传、测试样本审核、实时评估进度、结果分析与导出，以及历史任务管理的完整流程。

## 主要功能

- 全中文四步引导式工作流
- 自定义被测 RAG 服务、评测 LLM、Embedding 模型、Base URL、模型名和 API Key
- 评测 LLM 支持 OpenAI Chat Completions、OpenAI Responses 和 Anthropic Messages 三种协议
- 根据上传文档自动生成测试样本（问题 + 期望答案）
- 测试样本支持编辑、删除和手动添加
- 自动从 `message.contexts`、`message.citations`、顶层 `contexts` 或 `context` 提取检索依据
- SSE 实时展示生成与评估进度
- 支持任务自定义命名、分页历史记录、历史任务删除
- 评估结果支持 CSV / JSON 导出
- 浏览器自动记忆常用模型和 RAG 配置
- 内置 mini RAG，便于本地演示完整流程

> **安全提示：** 配置记忆使用浏览器 `localStorage`，保存配置时会包含 API Key。请仅在可信的本地浏览器环境中使用；共享电脑或录屏结束后，可以在新建评估页点击“清除”删除已保存配置。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + SQLite + httpx |
| 评估引擎 | deepeval 4.0.7 |
| 前端 | React 19 + TypeScript + Tailwind CSS + TanStack Query + Recharts |
| 通知 | sonner |
| 测试 | pytest + Vitest + Testing Library + MSW |

## 快速开始

### 环境要求

- Python 3.11+，推荐使用 conda
- Node.js 18+
- 可用的评测 LLM 端点：OpenAI Chat、OpenAI Responses 或 Anthropic Messages 格式
- OpenAI 兼容的 Embedding 接口，例如 SiliconFlow BAAI/bge-m3、OpenAI 或本地 Ollama

### 启动后端

```powershell
cd D:\rag-llm-test
conda create -n rag-eval python=3.11 -y
conda activate rag-eval
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

验证后端：

```text
http://127.0.0.1:8000/health
```

应返回：

```json
{"status": "ok"}
```

### 启动前端

打开另一个 PowerShell 窗口：

```powershell
cd D:\rag-llm-test\frontend
npm install
npm run dev
```

浏览器访问：

```text
http://localhost:5173
```

> 前端通过 `VITE_API_BASE` 读取后端地址，默认值为 `http://localhost:8000/api`。如需修改，可创建 `frontend/.env.local`：
>
> ```text
> VITE_API_BASE=http://127.0.0.1:8000/api
> ```

## 使用内置 mini RAG 演示

mini RAG 使用 `tests/fixtures/test_doc.txt` 作为 WidgetX 产品知识库，并调用 DeepSeek 生成答案。

### 启动 mini RAG

打开新的 PowerShell 窗口：

```powershell
cd D:\rag-llm-test
conda activate rag-eval
$env:DEEPSEEK_API_KEY = "你的-DeepSeek-API-Key"
python mini_rag.py
```

mini RAG 默认监听：

```text
http://127.0.0.1:8001
```

### 前端填写方式

被测服务配置：

```text
Base URL: http://127.0.0.1:8001
API Key:  sk-local
Model:    deepseek-v4-flash
```

mini RAG 不校验传入的占位 API Key，但它会被平台放进 HTTP `Authorization` 请求头，因此必须使用 ASCII 字符。不要填写“本地测试”“无需填写”等中文内容，否则会出现：

```text
'ascii' codec can't encode characters ...
```

评测模型和嵌入模型仍需填写真实可用的 API Key。

## 使用流程

### 第一步：配置与上传

1. 可选填写任务名称，例如“WidgetX 第一轮回归测试”
2. 配置被测 RAG 服务
3. 配置评测模型和 API 协议
4. 配置 Embedding 模型
5. 保存配置
6. 上传知识库文档
7. 点击“开始评估”

平台会自动记忆最后一次保存的配置，下次打开自动填入。

### 第二步：审核测试样本

平台通过 deepeval Synthesizer 读取文档并生成问题和期望答案。用户可以：

- 编辑问题和期望答案
- 查看或编辑来源片段
- 删除不合适的测试样本
- 手动添加测试样本
- 确认样本并开始正式评估

### 第三步：运行评估

平台逐条请求被测 RAG 服务，获取：

- RAG 实际答案
- 检索依据 chunks

随后运行五项 deepeval 指标，并通过 SSE 实时展示当前阶段和进度。

### 第四步：查看结果

结果页包含：

- 各项指标平均分
- 雷达图
- 总样本数、通过数、失败数和通过率
- 每条问题的期望答案、实际答案、检索依据和指标分数
- 长文本展开 / 收起
- CSV / JSON 导出

历史记录页采用分页卡片布局，每页显示 8 条，支持：

- 任务自定义名称
- 查看创建时间和完成时间
- 查看历史结果
- 删除已完成或失败的任务

删除历史任务会同时清理该任务的上传文档、测试样本和评估结果。运行中的任务不能删除。

## 评估指标

### 检索侧指标

- **Contextual Relevancy**：检索内容与问题是否相关
- **Contextual Recall**：检索内容是否覆盖期望答案所需信息
- **Contextual Precision**：高相关内容是否排在前面，检索内容是否精确

### 生成侧指标

- **Answer Relevancy**：实际答案是否回答了问题
- **Faithfulness**：实际答案是否忠实于检索依据，是否存在无依据内容

## 被测 RAG 的接口约定

平台通过 OpenAI 风格接口调用被测 RAG：

```http
POST {base_url}/chat/completions
```

请求体示例：

```json
{
  "model": "your-rag-model",
  "messages": [
    {"role": "user", "content": "用户问题"}
  ]
}
```

答案从以下位置读取：

```text
choices[0].message.content
```

检索依据按以下顺序自动识别：

1. `choices[0].message.contexts`
2. `choices[0].message.citations` 中的 `text` 或 `content`
3. 顶层 `contexts`
4. 顶层 `context`

推荐响应示例：

```json
{
  "choices": [
    {
      "message": {
        "content": "根据知识库生成的答案",
        "contexts": [
          "检索到的文档片段 1",
          "检索到的文档片段 2"
        ]
      }
    }
  ]
}
```

检索类指标依赖这些依据片段。如果没有返回 contexts / citations，平台会发出警告，因为 Contextual Relevancy、Recall 和 Precision 无法被正确评估。

## 评测模型协议

`CustomOpenAIModel` 支持三种 `api_format`：

| `api_format` | 协议 | 请求端点 | JSON 输出方式 | 适用场景 |
|--------------|------|----------|---------------|----------|
| `openai_chat` | OpenAI Chat Completions | `POST {base}/chat/completions` | `response_format=json_object` + 自动降级 | DeepSeek、SiliconFlow、vLLM、llama.cpp、LM Studio、Ollama 和大多数 OpenAI 兼容网关 |
| `openai_json` | OpenAI Responses API | `POST {base}/responses` | `text.format.type=json_object` | 新版 OpenAI Responses API |
| `anthropic` | Anthropic Messages API | `POST {base}/messages` | Prompt JSON 指令 + 容错解析 + 重试 | Anthropic Claude 和兼容 `/v1/messages` 的代理 |

Embedding 模型始终使用 OpenAI 兼容的：

```http
POST {base}/embeddings
```

Anthropic Messages 和 OpenAI Responses 本身不提供 Embedding 端点，因此嵌入模型配置不会显示协议选择器。

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/upload` | 上传知识库文件并创建任务 |
| `POST` | `/api/evaluate` | 使用模型配置启动评估 |
| `GET` | `/api/task/{id}` | 获取任务状态 |
| `GET` | `/api/task/{id}/stream` | SSE 实时进度 |
| `GET` | `/api/models` | 获取 OpenAI 兼容端点的模型列表 |
| `GET` | `/api/goldens/{task_id}` | 获取任务测试样本 |
| `POST` | `/api/goldens/{task_id}` | 手动添加测试样本 |
| `PUT` | `/api/goldens/{golden_id}` | 编辑测试样本 |
| `DELETE` | `/api/goldens/{golden_id}` | 删除测试样本 |
| `POST` | `/api/goldens/{task_id}/confirm` | 确认样本并继续评估 |
| `GET` | `/api/results/{task_id}` | 获取评估结果 |
| `GET` | `/api/history` | 获取历史任务列表 |
| `DELETE` | `/api/tasks/{task_id}` | 删除已完成或失败任务及其本地数据 |

## 测试

### 后端离线测试

```powershell
python -m pytest tests\ -q --ignore=tests\test_pipeline_goldens.py --ignore=tests\test_pipeline_evaluate.py
```

最近验证结果：

```text
106 passed, 1 skipped
```

### 后端真实 API 集成测试

```powershell
$env:DEEPSEEK_API_KEY = "sk-..."
$env:EMBEDDING_API_KEY = "sk-..."
$env:EMBEDDING_BASE_URL = "https://api.siliconflow.cn/v1"
$env:EMBEDDING_MODEL = "BAAI/bge-m3"
python -m pytest tests\test_pipeline_goldens.py tests\test_pipeline_evaluate.py -v
```

### 前端测试与构建

```powershell
cd frontend
npm test
npm run build
```

最近验证结果：

```text
25 passed
production build passed
```

## deepeval 已知问题适配

### #2885：自定义模型返回值契约

deepeval 的非原生模型调用路径要求：

- 有 schema 时返回 schema 实例
- 无 schema 时返回字符串

如果返回 `(result, cost)` 元组，Synthesizer 的 `_generate_schema`、`_generate` 或 `ContextGenerator.evaluate_chunk` 可能失败并静默生成 0 条测试样本。

本项目的 `CustomOpenAIModel.generate()` / `a_generate()` 始终返回单值，不返回元组。

### #2884：未知模型成本为 None

部分未知定价模型会让 `calculate_cost()` 返回 `None`，导致 deepeval 内部执行 `total_cost += None` 时抛出异常。

本项目在无法确定定价时返回 `0.0`，避免该问题。

### JSON 输出兼容

不同兼容端点对 JSON 模式支持不一致。本项目实现多层降级：

1. 优先使用 JSON mode
2. 端点拒绝时去掉 `response_format` 重试
3. 输出不是 JSON 时追加明确的 JSON 输出指令再次重试

这保证了 Synthesizer evolution prompt 和五项指标能够使用 DeepSeek 等 OpenAI 兼容端点。

详细说明见：[docs/deepeval-bug-report.md](docs/deepeval-bug-report.md)。

## 项目结构

```text
rag-llm-test/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 服务端配置
│   ├── models.py            # Pydantic 请求/响应模型
│   ├── db.py                # SQLite CRUD 与数据库迁移
│   ├── storage.py           # 上传文件存储与任务目录清理
│   ├── embedder.py          # OpenAI 兼容 Embedding 适配器
│   ├── custom_model.py      # 三协议评测 LLM 适配器
│   ├── rag_client.py        # 被测 RAG 调用与 contexts 提取
│   ├── task_manager.py      # 任务状态与 SSE 事件队列
│   ├── pipeline.py          # deepeval 评估流程
│   └── routes.py            # FastAPI 接口
├── frontend/
│   └── src/
│       ├── pages/           # 配置、样本审核、进度、结果、历史记录
│       ├── components/      # 模型选择、步骤引导、长文本展开、图表等
│       ├── api/client.ts    # API 客户端
│       ├── hooks/useApi.ts  # TanStack Query 和 SSE Hooks
│       ├── utils/storage.ts # 浏览器配置记忆
│       ├── mocks/           # MSW 测试 Mock
│       └── __tests__/       # 前端测试
├── tests/                   # 后端测试
├── scripts/
│   ├── smoke_real_eval.py   # 真实 API 冒烟测试
│   └── smoke_formats_e2e.py # 三协议本地端到端测试
├── mini_rag.py              # 本地演示 RAG 服务
├── requirements.txt
└── README.md
```

## 数据与隐私

以下内容默认被 `.gitignore` 排除，不会上传到 GitHub：

- `.env`
- SQLite 数据库及 WAL 文件
- `data/` 上传文档目录
- `.deepeval/`
- Python 缓存
- Node.js 依赖和构建产物
- uvicorn 日志

请不要把真实 API Key 写入源码、README、测试脚本或提交历史。建议通过前端本地配置、环境变量或未跟踪的本地配置文件提供。

## Commit 约定

| 前缀 | 用途 |
|------|------|
| `feat:` | 新功能 |
| `fix:` | Bug 修复 |
| `test:` | 测试 |
| `docs:` | 文档 |
| `chore:` | 工具或依赖维护 |
| `refactor:` | 重构 |

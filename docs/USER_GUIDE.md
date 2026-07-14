# RAG Evaluation Platform — User Guide

## 环境准备

### 1. 安装 Conda 环境

```bash
conda create -n rag-eval python=3.11 -y
conda activate rag-eval
pip install -r requirements.txt
```

### 2. 安装前端依赖

```bash
cd frontend
npm install
```

### 3. 获取 API Key

| 用途 | 供应商 | 获取地址 |
|------|--------|---------|
| 评测模型 | DeepSeek | https://platform.deepseek.com/api_keys |
| 嵌入模型 | SiliconFlow | https://siliconflow.cn (免费额度 2000 万 tokens) |

> 也可用 OpenAI、vLLM、Ollama 等任意 OpenAI 兼容 API。

## 启动

需要**三个终端**：

**终端 1 — 后端：**

```bash
conda activate rag-eval
uvicorn app.main:app --reload --port 8000
```

**终端 2 — 前端：**

```bash
cd frontend
npm run dev
```

**终端 3 — 测试用 RAG 服务（可选）：**

```bash
conda activate rag-eval
export DEEPSEEK_API_KEY=你的key
python mini_rag.py
```

> mini_rag.py 是一个玩具 RAG 服务（端口 8001），用它可以不依赖外部 RAG 服务测试完整流程。

## 使用流程

### 第一步：配置模型

打开 `http://localhost:5173`，看到三张配置卡片：

**① RAG Service（被测服务）**
- Base URL：你的 RAG 服务地址。测试用填 `http://localhost:8001`
- API Key：RAG 服务的 key。mini_rag 不校验，随便填
- Model Name：RAG 服务用的模型名，默认即可

**② Evaluation Model（评测模型）**
- Provider：选 `DeepSeek`
- API Key：你的 DeepSeek API Key
- Model：推荐 `deepseek-chat`

**③ Embedding Model（嵌入模型）**
- Provider：选 `SiliconFlow`
- API Key：你的 SiliconFlow API Key
- Model：`BAAI/bge-m3`

> 点 "获取模型" 按钮可以实时拉取供应商的可用模型列表。

### 第二步：上传文档

拖拽或点击上传知识库文件。支持 `.txt` `.md` `.pdf` `.json` `.csv`。

测试用：`tests/fixtures/test_doc.txt` 或 `tests/fixtures/common_knowledge.txt`。

### 第三步：开始评测

点 **Start Evaluation**。后端开始：
1. 用嵌入模型对文档分块
2. 用评测模型生成 goldens（问答对）

### 第四步：确认 Goldens

Goldens 生成完毕后自动跳转。浏览生成的问答对，确认后点 **Confirm & Run Evaluation**。

### 第五步：查看结果

评测完成后自动跳转结果仪表盘：

- **分数卡片**：每个指标的总体平均分
- **雷达图**：所有指标的对比视图
- **详情表**：每条 golden 的逐项得分（点击展开）

### 评分说明

| 指标 | 衡量什么 | 满分要求 |
|------|---------|---------|
| AnswerRelevancy | 答案是否切题 | RAG 回答与问题相关 |
| Faithfulness | 答案是否忠于检索内容 | 不编造、不偏离上下文 |
| ContextualRelevancy | 检索是否相关 | RAG 检索到了正确文档 |
| ContextualRecall | 检索是否全面 | RAG 检索到了所有相关内容 |
| ContextualPrecision | 检索是否精准 | RAG 没检索无关内容 |

> Contextual 系列指标需要 RAG 服务在响应中返回 `contexts` 字段。mini_rag.py 已支持。

## 网络架构

```
浏览器 (localhost:5173)
    │
    ├── REST API ──→ 后端 (localhost:8000)
    │                   │
    │                   ├── DeepSeek API (评测模型)
    │                   ├── SiliconFlow API (嵌入模型)
    │                   ├── 你的 RAG 服务 (被测)
    │                   └── SQLite + 磁盘文件
    │
    └── SSE  ────────→ 实时进度推送
```

## 常见问题

**Q: 上传后显示 "No goldens were generated"？**

文档太短或内容太少，Synthetizer 无法提取有效问答对。换个内容更丰富、结构更清晰的文档。

**Q: 评测分数全是 0？**

检查 RAG Base URL 是否正确、API Key 是否有效。查看后端终端日志。

**Q: Contextual 系列指标全是 0？**

你的 RAG 服务响应里没有返回 `contexts`（检索到的文档片段）。需要 RAG 服务在 `message.contexts` 里提供。

**Q: 想用自己的嵌入模型？**

嵌入模型卡里选"自定义"，填任意 OpenAI 兼容嵌入 API 的地址和 key。

**Q: Anthropic 能用吗？**

暂时不行。Anthropic 协议和 OpenAI 不兼容，需要单独适配（计划中）。

## 测试

```bash
# 后端所有测试 (75 个)
pytest tests/ -v --ignore=tests/test_pipeline_goldens.py --ignore=tests/test_pipeline_evaluate.py

# 前端所有测试 (22 个)
cd frontend && npm test
```

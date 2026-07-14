# RAG Evaluation Platform v2 — Design Spec

> Date: 2026-07-14
> Status: draft
> Supersedes: 2026-07-08-rag-evaluation-platform-design.md (v1)

## Overview

v1 平台已实现核心评测流水线（70 测试全过）。v2 聚焦三个改进方向：

1. **模型可配置** — 评测模型、嵌入模型、RAG 模型全部从前端选择，不再硬编码
2. **实时进度** — SSE 推送评测进度，替代轮询
3. **前端交互** — 按钮反馈、toast 通知、错误处理、防重复提交

## Architecture Changes

```
Frontend                          Backend
─────────                         ───────
ModelSelector (评测/嵌入/RAG)  →  POST /api/evaluate  (加锁防重)
                               →  GET  /api/models?url=&key=  (代理获取模型列表)
ProgressPage (SSE 监听)        ←  GET  /api/task/{id}/stream  (SSE 事件流)
                               ←  pipeline 内部回调 → task_manager → SSE 推送
```

## Feature Details

### 1. Model Configuration

**后端 `app/models.py`** — 新增 `ModelConfig`：

```python
class ModelConfig(BaseModel):
    provider: str = "custom"     # deepseek|openai|anthropic|siliconflow|custom
    model_name: str
    api_key: str
    base_url: str
```

`EvaluateRequest` 扩展为三个模型配置字段：

```python
class EvaluateRequest(BaseModel):
    rag_base_url: str
    rag_api_key: str
    rag_model: str = "deepseek-chat"
    eval_model: ModelConfig
    embed_model: ModelConfig
    task_id: Optional[str] = None
```

**后端 `GET /api/models`** — 新增端点，代理查询供应商可用模型：

```
GET /api/models?base_url=https://api.deepseek.com&api_key=sk-xxx
→ 转发 GET {base_url}/models (OpenAI 兼容)
→ 返回 [{id: "deepseek-chat", ...}, ...]
→ 失败时返回 502 + 错误信息
```

**前端** — `RagConfigForm` 拆为三张配置卡片，每张含：
- 供应商下拉（DeepSeek / OpenAI / Anthropic / SiliconFlow / 自定义）
- base_url（选供应商后自动填充，可手动改）
- API Key（密码输入框 + 显示/隐藏切换）
- Model 选择（下拉 + "获取模型"按钮 + 手动输入 fallback）
- 供应商预设数据（未获取模型时的默认列表）

**`app/config.py`** — 移除评测模型和嵌入模型的硬编码默认值，仅保留基础设施配置（chunk size、timeout、data dir、db path）。

**`app/embedder.py`** — `build_embedder()` 改为接收 `ModelConfig` 参数，动态构建任意 OpenAI 兼容嵌入端点。

**`app/pipeline.py`** — `build_evaluation_model()` 改为接收 `ModelConfig` 参数。

### 2. Real-Time Progress (SSE)

**后端 `GET /api/task/{task_id}/stream`** — 新 SSE 端点：

```
event: progress
data: {"phase": "GENERATING_GOLDENS", "progress": 0.3, "message": "正在分析文档..."}

event: progress
data: {"phase": "RUNNING_EVAL", "progress": 0.4, "message": "评测 2/6: AnswerRelevancy...", "current_golden": 2, "total_goldens": 6, "current_metric": "AnswerRelevancy"}

event: complete
data: {"status": "COMPLETED"}

event: error
data: {"status": "FAILED", "error": "Goldens 生成失败: ..."}
```

实现方式：`task_manager` 维护 `asyncio.Queue` 字典，pipeline 通过 `progress_callback` 写入事件，SSE 端点从 Queue 读取并 yield。

**前端 `ProgressPage`** — 改为 `EventSource` 监听 SSE：
- 实时渲染阶段图标 + 进度百分比
- 显示当前 golden 序号和指标名
- 完成后自动跳转 Results
- 连接断开时显示"重连中..."

### 3. Duplicate Submission Prevention

**后端** — `POST /api/evaluate` 入口检查：
- 同一 `task_id` 若已处于 `GENERATING_GOLDENS` / `RUNNING_EVAL` 状态 → 返回 409
- 用 `asyncio.Lock` 字典按 task_id 细粒度加锁

**前端** — 所有提交按钮：
- `loading` 状态时 `disabled` + spinner
- `active:scale-95` 点击缩放反馈
- mutation `onError` → toast 显示错误

### 4. Frontend UX Improvements

**Toast 通知** — 安装 `sonner`，全局 `<Toaster />`：
- 成功：上传完成、配置保存、评测开始/完成
- 错误：网络失败、API 错误、超时
- 替换所有 `alert()` 调用

**按钮反馈** — 所有操作按钮统一行为：
- `disabled`：`cursor-not-allowed opacity-60`
- `loading`：`<Loader2 className="animate-spin" />` + 文字变灰
- 点击：`active:scale-95 transition-transform duration-100`
- 成功瞬间：0.5s 绿色 `<CheckCircle />` 然后恢复

**FileUploader 改进**：
- XMLHttpRequest 上传进度条（百分比 + 填充色动画）
- 文件列表每项可删除（X 按钮）
- 拖拽悬停：放大 1.02x + 虚线变实线 + 蓝色背景

**错误处理**：
- 所有 `useMutation` 加 `onError` 回调
- 所有 `useQuery` 的 `isError` 状态渲染重试按钮
- `GoldensPage.handleConfirm` 加 try/catch
- API 客户端加请求超时（30s）+ AbortController（组件卸载时取消）

**ProgressPage 改进**：
- 加载状态：骨架屏代替 "Loading..."
- 失败状态：显示错误信息 + "重试"按钮 + "返回配置"链接
- 完成后：2 秒延迟自动跳转 Results（给用户看清 "完成" 状态的时间）

**ResultsPage 改进**：
- 加载状态：骨架屏
- 空状态：提示文案 + 返回按钮

## Testing Design

### Backend Tests (add to `tests/`)

| Test File | What It Covers |
|-----------|---------------|
| `tests/test_api_models.py` | `GET /api/models` — 正常返回模型列表、base_url 不可达返回 502、api_key 错误返回 401 |
| `tests/test_api_evaluate_v2.py` | `POST /api/evaluate` — 传入 ModelConfig 正常启动、重复提交返回 409、缺少模型配置返回 422 |
| `tests/test_api_stream.py` | `GET /api/task/{id}/stream` — SSE 事件流格式正确、任务不存在返回 404 |
| `tests/test_pipeline_v2.py` | `build_evaluation_model(config)` / `build_embedder(config)` 动态构建、progress_callback 被正确调用 |

### Frontend Tests (add to `frontend/src/__tests__/`)

| Test File | What It Covers |
|-----------|---------------|
| `ModelSelector.test.tsx` | 供应商切换自动填 base_url、获取模型按钮触发 API、手动输入模型名 |
| `RagConfigForm-v2.test.tsx` | 三张配置卡片渲染、保存/提交流程、表单验证 |
| `ProgressPage-v2.test.tsx` | SSE 事件渲染进度、完成后跳转、连接错误处理 |
| `FileUploader-v2.test.tsx` | 上传进度条、删除文件、拖拽状态 |

### Test Infrastructure

- 后端 SSE 测试用 `httpx.AsyncClient` + `aiter_lines()` 读取事件流
- 前端 SSE mock 用 MSW 的 `EventSource` polyfill 或手动触发事件
- 模型代理测试用 `responses` mock 外部 API

## Implementation Notes

- deepeval 4.0.7 的 `calculate_cost()` 仍对 `deepseek-v4-flash` 返回 `None`，pipeline 中 continue 使用 `deepseek-chat` 作为后备，待上游修复后再切
- `evaluate()` 在 deepeval 4.x 返回 `EvaluationResult`（非列表），`collect_metric_scores` 已适配
- SSE 使用标准 `text/event-stream`，不需要额外依赖
- sonner 是 React 生态最轻量的 toast 库（~2KB gzipped），零依赖

## Scope

### v2 (this spec)
- [x] 三种模型前端可配置（供应商预设 + 自定义 + 获取模型列表）
- [x] SSE 实时进度推送
- [x] 后端防重复提交锁
- [x] Toast 通知替代 alert
- [x] 按钮点击反馈（loading/disabled/缩放动画）
- [x] 上传进度条 + 文件删除
- [x] 全面错误处理（重试按钮、错误状态）

### Out of scope (v3+)
- [ ] Goldens 编辑/删除
- [ ] 评测取消功能
- [ ] 结果导出 CSV/PDF
- [ ] 历史趋势对比
- [ ] PDF 文档解析

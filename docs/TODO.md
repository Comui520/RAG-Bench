# RAG Evaluation Platform — TODO / Roadmap

> v2 已完成：模型可配置、SSE 实时进度、前端交互优化、97 测试全过。
> 以下为 v3+ 候选功能，按优先级分组。

---

##   P0 — 下次就该做

### 1. 自定义指标 + 预设指标组

**现状：** 5 个指标硬编码全跑，用户无法选择。

**目标：**

- 前端加指标选择面板：勾选要跑的指标
- 预设指标组（一键选）：
  | 预设 | 包含 |
  |------|------|
  | 完整评测 | 全部 5 个 |
  | 仅检索器 | ContextualRelevancy + Recall + Precision |
  | 仅生成器 | AnswerRelevancy + Faithfulness |
  | 快速检查 | AnswerRelevancy only |
- 用户自定义指标组：命名 + 保存到浏览器 localStorage
- 后端 `EvaluateRequest` 加 `metrics: list[str]` 字段

### 2. 评测取消功能

**现状：** 评测跑起来后无法中断。

**目标：**

- 后端 `asyncio.Event` 取消信号
- `POST /api/task/{id}/cancel` 端点
- 前端 ProgressPage 加"取消"按钮
- pipeline 关键步骤检查取消信号

### 3. Golden 编辑

**现状：** Goldens 只能看不能改。

**目标：**

- GoldenCard 加编辑模式（双击或 Edit 按钮）
- `PUT /api/goldens/{id}` 更新
- 删除单条 golden
- 手动添加 golden（加空白表单）

---

##   P1 — 明显提升体验

### 4. 结果导出

- CSV 导出（每个 golden 一行，指标分列）
- JSON 原始数据导出
- 一键复制评测摘要

### 5. 前端 Dark Mode

- Tailwind dark 类 + 手动切换或跟随系统
- 对评测类工具来说暗色模式很常用

### 6. 评估历史增强

- 搜索/筛选（按时间、状态、RAG URL）
- 删除旧任务
- 对比两次评估结果（并列展示分数）

### 7. 前端性能优化

- ResultsPage 大数据量分页（当前全量渲染）
- React.lazy 代码分割（按页面）
- 图表按需加载

---

##   P2 — 功能扩展

### 8. 更多模型预设

| 供应商 | 状态 |
|--------|------|
| DeepSeek | ✅ 已支持 |
| OpenAI | ✅ CustomOpenAIModel |
| SiliconFlow | ✅ CustomOpenAIModel |
| Anthropic | ❌ 协议不兼容，需单独适配 |
| Google Gemini | ❌ 同上 |
| 本地 Ollama | ✅ CustomOpenAIModel (填 localhost) |
| 本地 vLLM | ✅ CustomOpenAIModel |

优先做 Anthropic（用户量大）和 Ollama（本地测试方便）。

### 9. PDF 文档解析

- `pypdf` 或 `pdfplumber` 提取文本
- 前端上传时自动解析

### 10. 评测阈值自定义

- 用户设定每个指标的及格线（默认 0.5）
- 前端在 MetricScore 编辑阈值
- 结果页标记哪些指标未达标

### 11. 批量对比评测

- 一次对多个 RAG 配置跑同一知识库
- 结果页并列对比
- 适合调参场景（换 prompt、换模型、换 chunk 策略）

---

##   P3 — 长期方向

### 12. 用户认证

- 简单密码保护或 JWT
- 多用户隔离

### 13. 评测调度 + 通知

- 定时自动评测
- 邮件/Webhook 通知结果

### 14. 评测历史数据库分析

- 趋势图（同一 RAG 服务的多次评测变化）
- 回归检测（某次提交后 Faithfulness 下降 → 告警）

### 15. Confident AI 集成

- 可选同步到 Confident AI 云端
- 分享评测报告链接

---

##  修复中的技术债

- [x] ~~Windows 路径转义~~ (ec2ab03)
- [x] ~~deepeval 4.x API 适配~~ (eecaad3)
- [ ] `CustomOpenAIModel` 的 Synthesizer 兼容性 → 依赖 upstream 修 bug
- [ ] 前端 Hardcoded API URL (`localhost:8000`) → 改为 `.env` 变量
- [ ] `DeepEvalBaseLLM` 返回值 bug → 已上报, 等 upstream

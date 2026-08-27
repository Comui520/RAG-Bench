# RAG 测评平台前端现代化改版设计

日期: 2026-08-27
状态: 已批准

## 背景

用户反馈现有前端"所有东西都堆在一个页面，不美观也不现代"。同时提出两个核心需求：

1. **配置记忆**：embedding / LLM / RAG 服务配置不想每次重填（已确认：**连 API key 一起存 localStorage，自动记住上次配置**）。
2. **前端现代化**：分步骤工作流、历史记录页、金标可编辑、结果导出、现代极简视觉。

已确认的决策：
- 全中文 UI（RAG / API Key / 指标名等技术名词保留英文）
- 金标编辑需要动后端（一并做）
- 深色侧边栏 + 浅色内容区风格

## 产品文案通俗化

核心洞察：用户不知道 "goldens" 是什么。术语映射：

| 原词 | 通俗文案 |
|------|---------|
| goldens | 测试样本（问答对） |
| Evaluation | 评估 / 跑分 |
| GoldenCard | 测试样本卡片 |
| Confirm Goldens | 确认测试样本，开始评估 |

## 信息架构：4 步工作流

```
Step 1: 配置与上传  →  Step 2: 审核测试样本  →  Step 3: 运行评估  →  Step 4: 查看结果
  (首页 /)              (/task/:id/goldens)       (/task/:id/progress)   (/task/:id/results)
```

新增 `/history` 历史记录页（独立于工作流，从侧边栏进入）。

## 视觉风格

- 浅灰底 `#f8fafc` + 白色卡片（柔和阴影、圆角 12px、细边框）
- **深色侧边栏**（slate-900）：Logo + 图标导航 + 当前步骤高亮
- 主色 indigo/violet 渐变，CTA 大按钮
- 步骤指示器贯穿：完成=绿勾、当前=高亮、未来=灰

## 功能设计

### 1. 配置记忆（前端 localStorage）

- `frontend/src/utils/storage.ts`：
  - `loadSavedConfig()` → `FullConfig | null`（含 api_key）
  - `saveConfig(config: FullConfig)` → 写 localStorage
  - `clearSavedConfig()`
- `RagConfigForm`：
  - mount 时自动回填上次配置（若存在）
  - 点"保存配置"时写入 localStorage
  - 顶部记忆条：「已记住上次配置 [填入] [清除]」+ 提示文案"配置会自动保存，下次打开自动填入"

### 2. 分步骤工作流 + 步骤指示器

- 新组件 `components/StepIndicator.tsx`：接收 `current: 1|2|3|4`，渲染 4 步引导条
- `Layout.tsx` 重做：
  - 深色侧边栏（slate-900 bg，白字）
  - 顶部 Logo「RAG 评测平台」
  - 导航：新建评估（/）、历史记录（/history）
  - 内容区浅色
- 各页面顶部放 StepIndicator 说明当前位置与下一步

### 3. 历史记录页

- 新页面 `pages/HistoryPage.tsx`：
  - 任务表格：创建时间 / 状态徽章 / RAG 服务 / 操作（查看结果 / 删除）
  - 空态：「还没有评估记录，去创建第一个评估吧」
- 路由 `/history`
- 侧边栏"历史记录"入口（当前 Layout 只有被动列表，改为正式页面）
- 删除任务需要后端支持（见后端改动）

### 4. 金标可编辑

后端：
- `db.py`：
  - `update_golden(golden_id, input_text, expected_output, context)` → 更新
  - `delete_golden(golden_id)` → 删除（级联删 eval_results）
  - `add_golden` 已存在（手动添加复用）
- `routes.py`：
  - `PUT /api/goldens/{golden_id}` — 更新金标
  - `DELETE /api/goldens/{golden_id}` — 删除金标
  - `POST /api/goldens/{task_id}` — 手动添加金标

前端：
- `api/client.ts`：`updateGolden` / `deleteGolden` / `addGolden`
- `GoldenCard.tsx`：编辑态（问题/答案/来源文本可编辑）+ 删除按钮
- `GoldensPage.tsx`：底部「手动添加测试样本」表单（问题 + 期望答案）
- 文案改为「审核测试样本」

### 5. 结果导出

- `ResultsPage.tsx` 顶部加「导出 CSV」「导出 JSON」按钮
- 前端生成 Blob 下载，无需后端
- CSV 列：问题 / 期望答案 / 实际输出 / 各指标分 / 是否通过

### 6. 文案中文化（全站）

| 文件 | 改动 |
|------|------|
| ConfigPage | 「新建评估」「配置与上传」 |
| GoldensPage | 「审核测试样本」 |
| ProgressPage | 「运行评估」「正在生成测试样本…」 |
| ResultsPage | 「查看结果」「评估完成！」 |
| ProgressTracker | 阶段文案：上传文档 / 生成测试样本 / 审核测试样本 / 运行评估 / 完成 |

## 技术要点

- 前端保持 React 18 + TS + Tailwind + TanStack Query + Recharts + sonner（用户确认保留框架）
- 配置记忆用 localStorage（key 如 `rag-eval:last-config`），含 API key（用户已确认）
- 所有下载用 Blob + URL.createObjectURL
- 删除/编辑金标后 invalidateQueries 刷新列表

## 测试

- 更新受文案影响的现有测试（user-flows.test.tsx 断言 "save"/"start evaluation" 等）
- 新增：
  - 配置记忆：save/load/clear 单元测试（storage.ts）
  - 金标 CRUD：GoldenCard 编辑/删除、GoldensPage 手动添加
  - 历史页：渲染任务列表
- 后端新增金标 CRUD 路由测试

## 实施顺序

1. 后端金标 CRUD（db + routes + 测试）
2. 前端 storage.ts + RagConfigForm 记忆
3. Layout 重做 + StepIndicator
4. 各页面文案中文化 + 视觉现代化
5. GoldensPage 可编辑 + HistoryPage + ResultsPage 导出
6. 测试更新 + 全量回归

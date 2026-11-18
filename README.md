# 🎭 思政情景工坊 — 沉浸式思政实践智能体

> 全国计算机应用能力与数字素养大赛 · 第九届传智杯 AIWEB 网页开发挑战赛参赛作品

[![后端质量检查](https://github.com/Xcc682/eclass/actions/workflows/ci.yml/badge.svg)](https://github.com/Xcc682/eclass/actions/workflows/ci.yml)
[![仓库](https://img.shields.io/badge/GitHub-Xcc682%2Feclass-181717?logo=github)](https://github.com/Xcc682/eclass)
[![在线演示](https://img.shields.io/badge/在线演示-121.41.231.233%3A5667-brightgreen)](http://121.41.231.233:5667/)

**仓库地址：** <https://github.com/Xcc682/eclass> （公开仓库，可直接克隆）

```bash
git clone https://github.com/Xcc682/eclass.git
```

**在线演示：** <http://121.41.231.233:5667/> —— 用浏览器打开即可体验全部六大模块，首次使用以手机号与密码注册后登录（无需短信验证）。

---

## 📋 项目简介

思政情景工坊是一款面向高校思政实践场景的智能体应用。项目通过 **AI 情景实训** + **一站式成长社区** + **可配置易班适配器**，让思政学习从知识阅读延伸到沉浸式理解与实践训练。易班 OAuth 只有在学校提供应用参数和换票地址后才可启用，未配置时界面会明确显示不可用，不模拟登录成功。

**核心理念：** 角色扮演 → 情景模拟 → AI 个性化反馈 → 可视化成长轨迹

---

## 🚀 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| **前端框架** | Vue 3 + TypeScript + Vite | 响应式 UI |
| **H5 运行时** | Vue Router + 自研 uni-app Polyfill | 浏览器端路由与 API 兼容 |
| **后端** | Python FastAPI | 异步 API + AI 编排 |
| **数据库** | SQLite (开发) / PostgreSQL + pgvector (生产) | 关系数据 + 向量检索 |
| **向量检索** | pgvector + sentence-transformers (BAAI/bge-small-zh-v1.5) | RAG 语义搜索 |
| **全文搜索** | SQLite FTS5 / PostgreSQL pg_trgm | 关键词混合检索 |
| **AI 大模型** | DeepSeek API (deepseek-v4-flash) | 对话、评分、生成、Function Calling、图片理解 |
| **AI 工具协议** | OpenAI 兼容 Function Calling + MCP (stdio) | 自主检索 Agent、外部工具接入 |
| **检索增强** | 多查询改写 + 加权 RRF 融合（RAG-Fusion），可选 LLM 列表重排 | 扩大候选池、多路命中优先 |
| **语义缓存** | cachetools `TTLCache` + 嵌入余弦阈值 | 近义问题复用带引用答案 |
| **可靠性** | 熔断器 + 按用户日额度 + 调用指标 | LLM 网关可观测与保护 |
| **多模态** | 图片输入（PNG/JPEG/WebP）+ Edge 神经语音合成 | 手写稿识读、问答朗读 |
| **部署** | Docker Compose | 容器化一键部署 |

---

## 🎯 核心功能

### 1. 🎙️ 入党谈话模拟训练
AI 扮演党委组织委员，模拟完整入党谈话流程（积极分子→预备党员接收→转正→随机模拟）。每轮对话 AI 自动分析内容，完成 ≥2 轮后生成评估报告——
- **雷达图**：从思想认识、表达逻辑、入党动机、理论掌握、应变能力 5 维度评分
- **优势/不足**：基于对话记录 AI 自动提炼
- **改进建议**：针对性的学习计划推荐

### 2. 📜 党史情景互动学习
嘉兴红船、遵义会议、开国大典等 5 个党史场景。每个场景包含：
- 历史背景讲解
- 互动情景选择（多分支决策）
- AI 实时问答（支持追问）
- 完成进度记录

### 3. 🏛️ 红色研学智能导游
井冈山、延安、西柏坡等 5 个红色景点线上参观。AI 导游讲解历史背景，学生可随时提问，结束后 AI 自动生成研学心得报告。

### 4. 🎯 思政辩论赛陪练
内置 15 道辩题，并支持 AI 实时生成新辩题。学生可选择正方/反方与 AI 进行结构化辩论（立论→质询→驳论→总结），结束后 AI 裁判从逻辑严谨性、知识运用、思辨深度、语言表达、临场反应 5 维评分。

### 5. 👥 一站式思政成长社区
- 学习圈：帖子发布、回复、点赞
- 互助问答：老师与同学回复、提问者采纳答案
- 教师任务：发布/提交/批改
- 成长档案：AI 雷达图、成就徽章、活动时间线
- 我的报告：所有历史评估报告集中查看

### 6. 📚 思政知识库
- 资料上传（PDF/DOCX/TXT/MD）→ 自动解析 → 分块索引
- 混合检索（关键词 BM25 + 向量语义搜索）
- AI 智能问答（带引用追溯）
- 写作模板（入党申请书/思想汇报/心得体会/自传）→ AI 生成初稿

---

## 🧬 AI 技术架构

以下能力大多对标成熟开源实现（LangChain MultiQueryRetriever、RAG-Fusion、RankGPT、
GPTCache、RAGAS、pybreaker），哪些直接复用、哪些按公开算法自研以及取舍理由，
见 [`docs/AI_技术对标.md`](docs/AI_技术对标.md)。

### 自主检索 Agent（Function Calling）

知识问答由模型自行规划工具调用，而不是固定检索一次再总结：

| 工具 | 作用 |
|------|------|
| `search_knowledge` | 已审核资料混合检索，返回带编号片段 |
| `list_documents` / `read_chunk` | 查看资料目录 / 读取片段原文 |
| `get_learning_profile` | 本人学习档案：练习次数、平均分、最薄弱维度 |
| `list_my_practices` / `get_practice_detail` | 历史练习列表 / 单次练习问答与报告要点 |

- 一轮最多 3 步、每步最多 2 个并行调用；步数用尽强制收敛出答案
- 证据按首次出现编号，模型只能引用下发过的编号；学习档案不参与编号
- 任一环节失败自动回退固定检索，用户无感知
- 档案工具按登录身份取数，读详情时二次校验归属，跨用户记录一律视为不存在

### 学习档案与个性化

谈话考官开场前会读取本人历史练习与最薄弱维度（`app/services/learner_profile.py`），
针对性追问；知识问答里可直接问「我哪里薄弱、给我出几道题」，答案标注为「学习档案回答」。

### 检索增强：RAG-Fusion + 列表重排

固定检索链路在混合检索之上做了三层增强（`app/services/retrieval_advanced.py`）：

- 快模型把问题改写成 2 个同义检索式，与原问题并行检索
- 多组结果按 RRF（k=60）融合，原始查询加权（近似改写彼此相似，等权会淹没原话命中），同一文档最多取 3 个片段
- 可选列表重排（`RETRIEVAL_RERANK_ENABLED=true` 开启）：只回部分编号时按序前置、其余保序补全；默认走融合顺序以获得更低延迟

两套 24 题人工评测集（`backend/scripts/eval_retrieval.py`，23 题语料可答）：规范问法集上
基线 recall@1 已达 0.8696、增强保持一致；口语化问法集（"预备党员要熬多久才能转正"这类
学生真实提问）上，多查询改写把 recall@1 由 0.5217 提升到 0.6522、recall@6 由 0.6087
提升到 0.7391、MRR@6 由 0.5543 提升到 0.6848。

### 语义缓存与引用核验

- **语义缓存**（`app/services/semantic_cache.py`）：问题嵌入余弦 ≥0.93 直接复用带引用的
  回答，只缓存带引用、非降级的知识库答案；存储交给 cachetools `TTLCache`
- **引用核验**（`app/services/grounding.py`）：回答生成后逐块判断引用是否被原文支撑，
  剔除沾边引用并重新编号；核验失败保留原答案并标记，不让核验本身导致回答失败

### LLM 网关：可观测、熔断与额度

所有模型调用收敛到 `AIService._post_chat`：

- 每次调用记录模型、时延、token 与成败，`GET /api/v1/ai/observability` 可查
- 连续 5 次上游失败打开熔断 30 秒，冷却后半开试探；4xx 不计入失败
- 按用户自然日 30 万 token 限额，超额 429（管理员不受限）
- 意图路由、改写、重排、核验走快模型，问答与报告生成走主模型

### AI 安全网关

- 输入先做 NFKC 归一化并去掉空白与标点，再匹配中英文注入规则（抗拆字绕过）
- 指令覆盖/提示词窃取 → 400 拒绝；评分操控类表述只记审计不拦截
- 输出统一脱敏手机号、身份证号、银行卡号
- 拦截与脱敏计数可查询：`GET /api/v1/ai/security/stats`（管理员）

### 图片多模态

- 谈话、辩论、研学、书卷问答、知识问答五处对话均支持附带图片（data URL）
- 进入模型前校验格式（PNG/JPEG/WebP）、数量（≤2）与体积，非法输入直接 400
- 图片解读不附引用编号，与知识库回答分开展示

### MCP 工具服务器

`backend/mcp_server.py` 通过 MCP（stdio）暴露 `search_knowledge`、`list_documents`、
`get_document_outline` 三个工具，Claude Desktop / Claude Code 等客户端可直接把本项目
知识库接为检索工具：

```bash
cd backend && python mcp_server.py   # stdio 方式启动
```

### 语音合成

`POST /api/v1/media/tts` 将考官提问、讲解词转成语音（Edge 神经语音，免密钥），
结果按 `sha256(文本+语音)` 内容寻址缓存；上游失败返回 503，不写残缺缓存。

---

## 📁 项目结构

```text
eclass/
├── frontend/                         # Vue 3 前端（H5 运行时）
│   ├── src/
│   │   ├── pages/                     # 按业务模块组织页面
│   │   ├── components/                # 通用组件
│   │   ├── api/                        # 后端接口调用
│   │   └── store/                      # Pinia 状态管理
│   └── scripts/                       # 前端素材构建工具
├── backend/                          # FastAPI 后端与 Python 依赖
│   ├── app/
│   │   ├── main.py                     # 应用入口与路由注册
│   │   ├── routers/                    # API 路由
│   │   ├── services/                   # AI、检索、Agent、安全、档案、多模态、语音、积分
│   │   ├── models/                     # SQLAlchemy 数据模型
│   │   └── seed.py                     # 应用启动时使用的种子数据
│   ├── mcp_server.py                  # MCP（stdio）知识库工具服务器
│   ├── migrations/                    # Alembic 数据库迁移
│   ├── scripts/                       # 索引、媒体和数据库维护工具
│   ├── storage/                       # 上传文件与运行时媒体
│   └── tests/                         # 自动化测试
├── scripts/                          # 从项目根目录使用的独立运维工具
├── docs/                             # 知识库与沉浸式媒体说明
├── DEPLOYMENT.md                     # Linux 部署说明
├── docker-compose.yml                # 本地开发基础服务
├── docker-compose.quick.yml          # 试用与演示环境部署
├── docker-compose.production.yml     # 正式环境部署
└── .env.production.example          # 正式部署环境变量模板
```

`output/` 用于存放本地交付材料与导出文件。旧迁移包、浏览器测试产物和日志可以归档到 Git 忽略的 `_backup/`。

---

## 🔧 本地开发

### 前置要求

- Node.js ≥ 20、npm ≥ 10
- Python ≥ 3.11
- Docker Desktop（可选，用于向量数据库）
- DeepSeek API Key

### 快速启动

```bash
# 从项目根目录进入后端。已有 .env 时跳过复制。
cd backend
cp .env.example .env
# Windows PowerShell 可使用 Copy-Item .env.example .env
# 编辑当前目录下的 .env，填写 JWT_SECRET_KEY 和 LLM_API_KEY。
# 如需纯 SQLite 开发，将两个 DATABASE_URL 值都设为 sqlite:///./dev.db，
# 并清空 VECTOR_DATABASE_URL。
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

```bash
# 新开终端，从项目根目录进入前端
cd frontend
npm ci
npm run dev:h5
```

### Docker 基础服务（默认不启动容器后端）

```bash
# 启动 pgvector、Redis 与 MinIO（Docker Desktop 需运行）
# 从项目根目录运行。FastAPI 使用 backend/.env 中配置的数据库。
docker compose up -d

# 验证
docker ps
# 应看到 db、redis 和 minio；默认不应启动 eclass-backend-1。

# 仅在明确测试完整容器部署时才启动容器后端：
docker compose --profile container-backend up -d backend
```

Linux 服务器的启动与更新命令见 [部署说明](DEPLOYMENT.md)。

### 生产构建

```bash
cd frontend
npm run build:h5        # 构建 H5 生产包到 dist/build/h5
```

---

## 📖 API 概览

| 前缀 | 模块 | 端点数量 |
|------|------|:-------:|
| `/api/v1/auth/*` | 认证登录 | 5 |
| `/api/v1/users/*` | 用户资料 | 7 |
| `/api/v1/interviews/*` | 谈话训练 | 9 |
| `/api/v1/history/*` | 党史情景 | 6 |
| `/api/v1/tours/*` | 红色研学 | 8 |
| `/api/v1/debates/*` | 辩论赛 | 9 |
| `/api/v1/knowledge/*` | 知识库与问答 | 30 |
| `/api/v1/community/*` | 社区与教师任务 | 39 |
| `/api/v1/immersive/*` | 沉浸式书卷 | 7 |
| `/api/v1/media/*` | 语音合成 | 1 |
| `/api/v1/ai/*` | AI 安全、Agent 与可观测性状态 | 3 |
| `/` `/health*` | 根路径与健康检查 | 4 |

API 文档在开发模式下可直接访问：**http://localhost:8000/docs**

---

## 🎨 设计系统

### 色板：研墨（INK & PAPER）

| Token | 值 | 用途 |
|-------|-----|------|
| `--color-bg` | `#F5F0E8` | 暖纸色背景 |
| `--color-card` | `#FFFDF9` | 卡片底色 |
| `--color-border` | `#E8E0D5` | 暖灰边框 |
| `--color-primary` | `#8B1A1A` | 朱砂红主色 |
| `--color-primary-light` | `#C41E1A` | 红色强调 |
| `--color-accent` | `#C4A44A` | 鎏金点缀 |
| `--color-text` | `#2C2C2C` | 墨色正文 |
| `--color-text-secondary` | `#6B5E5E` | 暖灰说明 |
| `--color-text-muted` | `#9B8E8E` | 淡灰标注 |

### 排版

- **标题**：`STKaiti`, `Noto Serif SC` 衬线字体
- **正文**：系统默认无衬线（PingFang SC / Microsoft YaHei）

### 卡片规范

- 圆角 `4px`、3px 红色左边框
- 暖色背景噪点纹理（SVG 噪点叠加）
- hover 阴影加深效果

---

## 🧠 AI 智能体

| 智能体 | 角色 | 核心逻辑 |
|--------|------|---------|
| **谈话老师** | 党委组织委员 | 引导式提问，5-6 轮后结束，生成评估报告 |
| **历史导师** | 党史讲解员 | 场景相关背景讲解 + 自由问答 |
| **研学导游** | 景点讲解员 | 红色景点历史介绍 + 问答互动 + 研学心得生成 |
| **辩论对手** | 赛手 | 持正/反方立场，结构化辩论对抗 |
| **裁判员** | 评分专家 | 5 维度评分 + 优势/不足分析 + 改进建议 |
| **检索型助手** | 知识 Agent | 自主调用检索、目录、片段与学习档案工具，证据不足如实拒答 |

**调用链路：**
```
页面 → API Router → ai_service.py → DeepSeek API（OpenAI-compatible）
                                       ↕
                              knowledge_service.py（RAG 检索）
```

---

## ✅ 测试与代码质量

### 自动化测试

后端共 **11 个测试文件、104 个测试用例，全部通过**。测试重点不在
覆盖率数字，而在**把 AI 输出当作不可信输入**来验证系统可靠性：

| 测试文件 | 用例数 | 覆盖的风险点 |
|----------|--------|--------------|
| `tests/test_api.py` | 13 | 注册登录与角色权限、AI 失败显式化、谈话全链路、辩论状态机与断点续练、超长上下文截断、非法 JSON 回退与重试 |
| `tests/test_knowledge.py` | 13 | 分块解析、引用重排/去重/校验、截断 JSON 恢复、工具选择路由、无证据拒答、向量超时降级、会话幂等 |
| `tests/test_ai_advanced.py` | 30 | 调用指标与熔断状态机、日额度与 429、模型分流、RRF 融合与重排回退、语义缓存命中/过期/作用域、引用核验与失败开放、可观测接口 |
| `tests/test_knowledge_agent.py` | 5 | Agent 工具循环、并行调用、引用编号稳定、步数上界、未知工具不崩溃 |
| `tests/test_learner_profile.py` | 7 | 跨模块档案汇总、最薄弱维度、详情归属校验、档案不参与引用、无身份兜底 |
| `tests/test_safety.py` | 8 | 中英文注入（含拆字绕过）、评分操控只记审计、超长输入、输出脱敏 |
| `tests/test_vision.py` | 8 | 图片格式/数量/体积/编码校验、多模态内容块、接口前置拒绝 |
| `tests/test_community.py` | 3 | 帖子幂等/通知/审核、任务量规防重复发分、附件校验 |
| `tests/test_immersive.py` | 3 | 分支书卷路径、错误路线回溯、报告失败不假发积分 |
| `tests/test_mcp_server.py` | 7 | MCP 三个工具的实现与参数校验 |
| `tests/test_tts.py` | 7 | 语音合成文本校验、缓存命中、上游失败降级 |
| `tests/test_env.py` | — | 测试环境隔离夹具（独立 test.db、日志、密钥） |

```bash
cd backend
python -m pytest tests/ -q          # 104 passed
```

### 工程化配置

| 范围 | 工具 | 配置位置 |
|------|------|----------|
| Python 静态检查 | **Ruff**（E/F/I/UP/B/SIM 规则集） | `backend/pyproject.toml` |
| Python 类型检查 | mypy（`check_untyped_defs`） | `backend/pyproject.toml` |
| 前端格式化 | **Prettier** | `frontend/.prettierrc.json` |
| 前端类型检查 | vue-tsc（`strict: true`） | `frontend/tsconfig.json` |
| 编辑器一致性 | EditorConfig | 根目录 `.editorconfig` |
| 持续集成 | GitHub Actions | `.github/workflows/ci.yml` |

```bash
cd backend && ruff check app/        # All checks passed!
cd frontend && npm run type-check    # 无类型错误
```

### AI 输出可信性设计

LLM 输出一律视为**不可信输入**，在后端做白盒校验：

- 分数强制钳制到 `0-100`，置信度钳制到 `0-1`，证据截断 180 字
- 明确拒绝 `bool` 冒充数值；缺失维度**抛错而非补 0**
- 后端重算总分为各维度均值，并叠加「至少 2 条有效证据才显示分数」门槛
- JSON 解析失败时回退为纯文本回复，或重试一次；仍失败则统一转 `503`
- AI 不可用时不产生残缺练习记录、不假发积分

---

## 📊 数据持久化

| 数据 | 存储方式 | 说明 |
|------|----------|------|
| 用户认证 | SQLite/PostgreSQL | JWT token + 密码 pbkdf2_sha256 |
| 对话记录 | SQLite/PostgreSQL | 谈话、辩论、研学、党史与知识问答均按用户持久化 |
| 练习统计 | SQLite/PostgreSQL | 后端按已完成记录和真实评估结果汇总 |
| 报告存档 | SQLite/PostgreSQL | 谈话、辩论、研学和模板历史统一保存 |
| 知识库文件 | 磁盘 `storage/knowledge/` + DB | 全文索引 + 向量索引 |
| 向量索引 | pgvector + HNSW | cosine 距离，512 维 |

---

## 🏗️ 架构要点

```
浏览器 (Vue 3 SPA)
    │ Vue Router (hash)
    ▼
Vite Dev Server (:5667)
    │ proxy /api → :8000
    ▼
FastAPI Backend (:8000)
    │ Pydantic + SQLAlchemy
    ├── SQLite (dev.db) / PostgreSQL
    ├── pgvector (向量检索)
    └── DeepSeek API (AI)
```

---

## 📄 参赛信息

**赛事：** 全国计算机应用能力与数字素养大赛 · 第九届传智杯 AIWEB 网页开发挑战赛  
**作品类型：** AI 赋能的 Web 应用（思政情景实训智能体）  
**目标用户：** 高校入党申请人、入党积极分子、共青团员、学生干部

### 在线演示

- 演示地址：`http://121.41.231.233:5667/`
- 评审可直接在登录页注册账号（手机号 + 密码，无需短信验证），注册后即可登录体验。

### 团队信息

| 项目 | 内容 |
|------|------|
| 团队信息 | 以大赛报名表单为准 |

### 创新亮点

| 创新点 | 说明 |
|--------|------|
| 🎭 **情景式实训** | 角色扮演 + 沉浸式演练，覆盖入党谈话、党史、研学、辩论四大场景 |
| 🤖 **自主检索 Agent** | 模型自行规划检索、查目录、读片段与回看本人练习，失败自动回退 |
| 🧠 **学习档案记忆** | AI 记住学生的历史练习与薄弱维度，谈话针对性追问、问答可个性化出题 |
| 🖼️ **图片多模态** | 五处对话支持附带图片，图片经格式/体积校验后进入模型，解读不冒充引用 |
| 🛡️ **AI 安全网关** | 抗拆字注入检测、分级拦截与输出脱敏，拦截计数可查询 |
| 📚 **权威知识库** | RAG 三级混合检索 + 逐句引用可溯源 + 无据拒答 |
| 🔒 **AI 输出可信性** | 分数钳制、防伪造、无证据拒答、超时降级，104 项自动化测试覆盖 |
| ⚙️ **工程化规范** | Ruff / Prettier / EditorConfig / GitHub Actions CI / 前端分包 全链路 |

> 项目内置可配置的易班 OAuth 适配器：学校提供应用参数与换票地址后方可启用，
> 未配置时界面明确显示不可用，不模拟登录成功。

---

## 📄 License

本项目仅供学习交流与参赛使用。代码中引用的第三方资源版权归原作者所有。

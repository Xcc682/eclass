# 🎭 思政情景工坊 — 沉浸式思政实践智能体

> 全国高校易班技术创新大会参赛作品 · AI 赋能思政 · 创新引领育人

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
| **AI 大模型** | DeepSeek API (deepseek-v4-flash) | 对话、评分、生成 |
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
3 个预设辩题 + AI 实时生成。学生可选择正方/反方与 AI 进行结构化辩论（立论→攻辩→反驳），结束后 AI 裁判从逻辑严谨性、知识运用、思辨深度、语言表达、临场反应 5 维评分。

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

## 📁 项目结构

```text
eclass/
├── frontend/                         # uni-app 前端与 H5 容器配置
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
│   │   ├── services/                   # AI、知识检索等业务服务
│   │   ├── models/                     # SQLAlchemy 数据模型
│   │   └── seed.py                     # 应用启动时使用的种子数据
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

### 小程序编译

```bash
cd frontend
npm run dev:mp-weixin   # 编译到微信开发者工具
npm run build:h5        # 生产环境 H5 构建
```

---

## 📖 API 概览

| 前缀 | 模块 | 端点数量 |
|------|------|:-------:|
| `/api/v1/auth/*` | 认证登录 | 3 |
| `/api/v1/users/*` | 用户资料 | 4 |
| `/api/v1/interviews/*` | 谈话训练 | 7 |
| `/api/v1/history/*` | 党史情景 | 4 |
| `/api/v1/tours/*` | 红色研学 | 5 |
| `/api/v1/debates/*` | 辩论赛 | 6 |
| `/api/v1/knowledge/*` | 知识库 | 15+ |
| `/api/v1/community/*` | 社区 | 7 |

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

**调用链路：**
```
页面 → API Router → ai_service.py → DeepSeek API（OpenAI-compatible）
                                       ↕
                              knowledge_service.py（RAG 检索）
```

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

**赛事：** 全国高校易班技术创新大会  
**作品类型：** 智能体应用（基于易班思政智能体平台）  
**目标用户：** 高校入党申请人、入党积极分子、共青团员、学生干部  

### 创新亮点

| 创新点 | 说明 |
|--------|------|
| 🎭 **情景式实训** | 角色扮演 + 沉浸式演练，4 大核心场景 |
| 🤖 **AI 个性化反馈** | 逐句分析 → 雷达图 → 可视化能力画像 → 改进路径 |
| 🌐 **社区化生态** | 实训 + 学习 + 交流 + 档案完整闭环 |
| 🔗 **易班适配器** | 配置状态可见；学校 OAuth 参数与换票服务就绪后可接入 |
| 📚 **权威知识库** | RAG 混合检索 + AI 问答 + 上传解析管线 |

---

## 📄 License

本项目仅供学习交流与参赛使用。代码中引用的第三方资源版权归原作者所有。

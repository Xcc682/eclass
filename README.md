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

```
f:/eclass/
├── frontend/                          # 前端项目
│   ├── src/
│   │   ├── pages/                     # 26 个页面
│   │   │   ├── index/                 # 首页工作台
│   │   │   ├── login/                 # 登录
│   │   │   ├── interview/             # 谈话模块（3页）
│   │   │   ├── history/               # 党史（2页）
│   │   │   ├── tour/                  # 研学（3页）
│   │   │   ├── debate/                # 辩论（3页）
│   │   │   ├── knowledge/             # 知识库（6页）
│   │   │   └── community/             # 社区（7页）
│   │   ├── components/                # 12 个通用组件
│   │   │   ├── common/                # Card, Badge, Avatar, Loading...
│   │   │   ├── chat/                  # ChatBubble, ChatInput
│   │   │   ├── layout/                # NavBar, TabBar, PageLayout
│   │   │   └── radar/                 # RadarChart 雷达图
│   │   ├── api/                       # API 调用层（8个模块）
│   │   ├── utils/                     # 工具函数
│   │   │   ├── uni-polyfill.ts        # uni-app H5 兼容层
│   │   │   ├── rpx-plugin.ts          # rpx→rem 转换 Vite 插件
│   │   │   └── constants.ts           # 全局常量
│   │   ├── store/                     # Pinia 状态管理
│   │   └── shims/                     # uni-app API 适配层
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
│
├── backend/                           # FastAPI 后端
│   ├── app/
│   │   ├── main.py                    # 应用入口 + 路由注册
│   │   ├── config.py                  # 配置管理（Pydantic Settings）
│   │   ├── database.py                # SQLAlchemy + SQLite/PostgreSQL
│   │   ├── security.py                # JWT 认证 + 密码哈希
│   │   ├── routers/                   # 8 个 API 路由模块
│   │   │   ├── auth.py                # 登录/注册/JWT
│   │   │   ├── users.py               # 用户资料/成长
│   │   │   ├── interviews.py          # 入党谈话（含对话上下文管理）
│   │   │   ├── history.py             # 党史情景
│   │   │   ├── tours.py               # 红色研学
│   │   │   ├── debates.py             # 辩论赛
│   │   │   ├── knowledge.py           # 知识库（上传/检索/问答/收藏/模板）
│   │   │   └── community.py           # 社区帖子/回复/点赞/任务
│   │   ├── models/                    # 8 个 SQLAlchemy 数据模型
│   │   ├── services/
│   │   │   ├── ai_service.py          # DeepSeek API 调用 + 智能体编排
│   │   │   └── knowledge_service.py   # 文档解析 + 分块 + FTS5 + 向量索引
│   │   └── seed.py                    # 种子数据
│   ├── storage/knowledge/             # 知识库上传文件存储
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml                 # pgvector + Redis 容器编排
├── .env.example                       # 环境变量模板
├── scripts/                           # 工具脚本
└── docs/                              # 文档
```

---

## 🔧 本地开发

### 前置要求

- Node.js ≥ 20、npm ≥ 10
- Python ≥ 3.11
- Docker Desktop（可选，用于向量数据库）
- DeepSeek API Key

### 快速启动

```bash
# 1. 克隆项目
cd f:/eclass

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY（DeepSeek API Key）

# 3. 启动后端
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 4. 启动前端（新开终端）
cd frontend
npm install
npm run dev:h5
```

### Docker 基础服务（默认不启动容器后端）

```bash
# 启动 pgvector、Redis 与 MinIO（Docker Desktop 需运行）
# FastAPI 仍按上面的命令在 Windows 本机运行，并读取 backend/dev.db。
cd f:/eclass
docker compose up -d

# 验证
docker ps
# 应看到 db、redis 和 minio；默认不应启动 eclass-backend-1。

# 仅在明确测试完整容器部署时才启动容器后端：
docker compose --profile container-backend up -d backend
```

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

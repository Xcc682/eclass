# 思政知识库 RAG 部署说明

默认不依赖 Docker：未配置 `VECTOR_DATABASE_URL` 时，知识库自动使用 SQLite FTS5。上传、审核、检索、问答引用、收藏、最近浏览和模板历史均可正常使用。

## 启用 pgvector 混合检索

1. 管理员终端执行 `wsl --install`，然后重启 Windows。
2. 安装 Docker Desktop，并启用 WSL2 后端。
3. 在项目根目录执行 `docker compose up -d db`。
4. 在 `backend/.env` 配置 `VECTOR_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sixiang`。
5. 在 `backend` 目录执行 `pip install -r requirements.txt` 和 `alembic upgrade head`。
6. 在资料管理页对已有文件执行“重建索引”。首次运行会下载 `BAAI/bge-small-zh-v1.5`（512 维）。

向量库连接失败时会自动回退到 SQLite FTS5。Redis 第一版不是必需组件。

## 角色配置

在 `backend/.env` 设置 `ADMIN_PHONES`、`TEACHER_PHONES`，多个手机号用逗号分隔。也可以让用户先登录一次，再在 `backend` 目录运行：

```bash
python scripts/set_role.py 13800138000 teacher
```

## 文件限制

- 支持文字版 PDF、DOCX、TXT、Markdown，单文件不超过 20MB。
- 文件保存在 `backend/storage/knowledge/`，该目录已忽略提交。
- 暂不支持扫描件 OCR、图片识别和自动网页抓取。

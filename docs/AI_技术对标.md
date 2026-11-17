# AI 技术对标：我们参考了哪些成熟开源实现

本文件说明项目中各项 AI 工程能力的参考来源、我们采纳了什么、以及为什么有些能力
按公开算法自研而不直接引入依赖。原则是：**能复用成熟库就复用，不能复用的按公开算法
做最小可信实现，并在代码里标注出处。**

## 映射表

| 本项目能力 | 实现位置 | 参考的开源项目 / 论文 | 我们采纳了什么 | 为什么没有直接引入 |
|------------|----------|----------------------|----------------|--------------------|
| 多查询检索 + RRF 融合 | `app/services/retrieval_advanced.py` | LangChain `MultiQueryRetriever` / `EnsembleRetriever`、RAG-Fusion（Rackauckas 2023）、Elasticsearch 加权 RRF | 改写条数（2）、RRF 公式与 k=60（Cormack 2009）、原始查询加权、并行检索与单路失败降级、同文档片段配额 | LangChain 会带来整套框架与版本约束，而本项目调用层已是自有 httpx 实现，引入后两套抽象并存更易出错 |
| LLM 列表重排 | `app/services/retrieval_advanced.py` | RankGPT（Sun et al. 2023）、LlamaIndex `LLMRerank` | 编号式 listwise 输出、部分编号按序前置并对未提及候选保序补全（RankGPT 的补全做法）、无效输出保持原序、片段截断 | cross-encoder 重排需额外部署模型；listwise 复用现有快模型，成本更低 |
| 语义缓存 | `app/services/semantic_cache.py` | GPTCache、LangChain `SemanticCache` | 嵌入余弦阈值（0.93）、作用域键、只缓存可信答案 | 通用库缓存的是文本，本项目缓存的是带引用的结构化答案，还需要作用域与降级标记 |
| 引用核验 | `app/services/grounding.py` | RAGAS `Faithfulness`、LlamaIndex `ResponseEvaluator` | 逐块判断"是否被所引原文支撑"、剔除后重新编号 | RAGAS 面向离线评测，线上需要可失败开放、带超时的轻量核验 |
| 熔断 / 额度 / 指标 | `app/services/circuit_breaker.py`、`ai_quota.py`、`llm_metrics.py` | pybreaker、Resilience4j、LiteLLM Router、LangSmith 观测 | 三态状态机（closed/open/half_open）、4xx 不计失败、按用户日额度、环形缓冲指标 | 单机演示部署下进程内实现足够，且指标需要与自有观测接口共用出口 |
| 检索评测 | `backend/scripts/eval_retrieval.py` | BEIR（Thakur et al. 2021）评测约定、RAGAS context recall | recall@k / MRR@k 定义、单目标判定、语料缺失题目跳过 | 评测集必须按本项目语料人工构造，指标实现只有几十行 |
| 结构化输出校验 | `app/services/ai_service.py` | Instructor / Pydantic 校验思路 | 类型白名单、范围钳制、缺失即抛错 | 项目已有 Pydantic 2，校验层按业务语义定制比通用库更直接 |
| 多模态内容块 | `app/services/vision.py` | OpenAI 多模态消息格式 | `image_url` data URL 内容块、格式/体积/数量白名单 | 协议本身即公开标准，直接按格式构造即可 |

## 直接复用的第三方库

| 库 | 用途 |
|----|------|
| `sentence-transformers`（BAAI/bge-small-zh-v1.5） | 中文嵌入：向量检索与语义缓存共用同一模型 |
| `cachetools`（`TTLCache`） | 语义缓存的 TTL + LRU 存储 |
| `httpx` | OpenAI 兼容调用的统一传输层 |
| `pypdf` / `python-docx` | 知识库文档解析 |
| `edge-tts` | 语音合成 |

## 评测结论（可复现）

```bash
cd backend
python scripts/eval_retrieval.py --mode both --k 6 --out ../output/评测报告_检索.md
```

24 题评测集（23 题语料可答）：

| 模式 | recall@1 | recall@6 | MRR@6 |
|------|----------|----------|-------|
| 基线（单查询混合检索） | 0.8696 | 0.9130 | 0.8840 |
| 增强（多查询 + RRF） | 0.8696 | 0.9130 | 0.8840 |

结论：在这组 23 题可答的语料上，增强与基线持平。基线已接近上限（2 题的相关资料不在
可检索语料内，其余题目的正确片段本来就排第一），多查询没有可提升的空间。

列表重排（`RETRIEVAL_RERANK_ENABLED`）默认关闭：开启后同一评测集在多次运行中落在
0.8261–0.8696 之间并伴随 MRR 波动，单次 LLM 排序的方差大于它带来的差异，而且每次问答
多 1–2 秒。代码、测试与开关都保留，等接入更强的重排模型（cross-encoder 或更大模型）时
再默认打开。

## 踩坑记录

- **结构化短调用必须关闭思考链**：重排与核验这类"判别型"调用如果沿用默认推理模式，
  `max_tokens` 会被推理过程吃光，返回空内容；`disable_thinking=True` 后稳定输出 JSON。
- **4xx 不应计入熔断**：一次格式错误的请求会让熔断器误判上游故障，最终把整条链路
  一起拖垮；只有 5xx 与网络异常才计入失败。
- **语义缓存键必须带作用域**：同一问题在不同分类、不同文档范围内答案不同，
  作用域参与键之后才不会串答案。
- **等权 RRF 会被近似改写淹没**：多个改写查询彼此高度相似，它们的公共候选会压过
  原始查询独有的命中；给原始查询加权后才与"用户原话优先"的直觉一致。
- **列表式重排只回部分编号是常态**：模型常只输出它认为相关的几个编号。要求完整排列
  会导致大量调用作废，按序前置 + 未提及候选保序补全（RankGPT 的做法）既保留了模型的
  判断，也不会把候选挤到任意位置。

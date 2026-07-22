"""AI Service - Real DeepSeek API integration with phase-aware prompts."""
import json
import httpx
from typing import Optional, Dict, List, AsyncIterator
from app.config import settings

DIMENSIONS = ["思想认识", "表达逻辑", "入党动机", "理论掌握", "应变能力"]
DEBATE_DIMENSIONS = ["逻辑严谨性", "知识运用", "思辨深度", "语言表达", "临场反应"]

# Talk phases (5-stage progressive structure)
INTERVIEW_PHASES = ["开场寒暄", "自我认知", "入党动机", "理论考察", "情景假设"]
# Debate phases (4-stage)
DEBATE_PHASES = ["立论", "质询", "驳论", "总结"]


class AIResponseValidationError(RuntimeError):
    """The provider responded, but the payload cannot be trusted by business code."""


def _mapping(value, label: str) -> dict:
    if not isinstance(value, dict):
        raise AIResponseValidationError(f"AI 返回的{label}不是对象")
    return value


def _text(value, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise AIResponseValidationError(f"AI 返回的{label}无效")
    return value.strip()


def _score(value, label: str) -> int:
    if isinstance(value, bool):
        raise AIResponseValidationError(f"AI 返回的{label}不是有效分数")
    try:
        score = int(value)
    except (TypeError, ValueError) as exc:
        raise AIResponseValidationError(f"AI 返回的{label}不是有效分数") from exc
    if not 0 <= score <= 100:
        raise AIResponseValidationError(f"AI 返回的{label}超出 0-100 范围")
    return score


def validate_interview_turn(value: object) -> dict:
    data = _mapping(value, "谈话内容")
    return {
        "question": _text(data.get("question"), "谈话问题"),
        "comment": _text(data.get("comment", data.get("点评", "")), "谈话点评", allow_empty=True),
        "finished": bool(data.get("finished", data.get("结束", False))),
        "phase": _text(data.get("phase", ""), "谈话阶段", allow_empty=True),
        "follow_up_type": _text(data.get("follow_up_type", ""), "追问类型", allow_empty=True),
    }


def _text_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list):
        raise AIResponseValidationError(f"AI 返回的{label}不是列表")
    return [_text(item, label) for item in value]


def validate_scored_report(value: object, dimensions: list[str], label: str) -> dict:
    data = _mapping(value, label)
    scores = _mapping(data.get("dimension_scores"), "维度评分")
    normalized_scores = {name: _score(scores.get(name), name) for name in dimensions}
    analysis = data.get("dimension_analysis", [])
    if analysis and not isinstance(analysis, list):
        raise AIResponseValidationError("AI 返回的维度分析不是列表")
    normalized_analysis = []
    for item in analysis:
        row = _mapping(item, "维度分析")
        name = _text(row.get("name"), "维度名称")
        normalized_analysis.append({
            "name": name,
            "score": _score(row.get("score"), name),
            "suggestion": _text(row.get("suggestion", ""), "改进建议", allow_empty=True),
        })
    return {
        **data,
        "overall_score": _score(data.get("overall_score"), "综合评分"),
        "dimension_scores": normalized_scores,
        "dimension_analysis": normalized_analysis,
        "strengths": _text_list(data.get("strengths", []), "优势"),
        "weaknesses": _text_list(data.get("weaknesses", []), "待改进项"),
        "suggestion": _text(data.get("suggestion"), "总体建议"),
    }


def validate_interview_report(value: object) -> dict:
    data = validate_scored_report(value, DIMENSIONS, "谈话评估报告")
    data["grade"] = _text(data.get("grade"), "评估等级")
    try:
        data["total_rounds"] = max(0, int(data.get("total_rounds", 0)))
    except (TypeError, ValueError) as exc:
        raise AIResponseValidationError("AI 返回的谈话轮次无效") from exc
    return data


def validate_debate_feedback(value: object) -> dict:
    return validate_scored_report(value, DEBATE_DIMENSIONS, "辩论评估报告")


def validate_topics(value: object) -> list[dict]:
    if not isinstance(value, list) or not 1 <= len(value) <= 3:
        raise AIResponseValidationError("AI 返回的辩题列表数量无效")
    topics = []
    for item in value:
        data = _mapping(item, "辩题")
        topics.append({
            "title": _text(data.get("title"), "辩题标题"),
            "category": _text(data.get("category"), "辩题分类"),
            "difficulty": _text(data.get("difficulty"), "辩题难度"),
            "context": _text(data.get("context"), "辩题背景"),
            "pro_hint": _text(data.get("pro_hint"), "正方提示"),
            "con_hint": _text(data.get("con_hint"), "反方提示"),
        })
    return topics


def validate_generated_text(value: object, label: str) -> str:
    return _text(value, label)

# ===== Phase-aware difficulty prompts =====
INTERVIEW_PROMPTS = {
    "beginner": """你是一位大学党委组织委员，正在对一名首次参加谈话的入党积极分子进行谈话。难度：初级。
你的风格：温暖亲切，像学长学姐聊天。多用鼓励性语言，问题偏重个人基本情况、成长经历和入党动机。
不要追问深奥理论，以引导学生敞开心扉为主。
考察阶段依次为：开场寒暄 → 自我认知 → 入党动机 → 理论考察（浅） → 情景假设（浅）。
当你认为学生已充分表达（通常是5-6轮后），将 finished 设为 true。
每轮回复JSON格式（不要输出其他内容）：
{"question": "你的下一个问题", "comment": "一句话点评刚才的回答", "finished": false, "phase": "当前阶段名", "follow_up_type": "probe|challenge|encourage"}""",

    "intermediate": """你是一位大学党委副书记，正在对一名发展对象进行预备党员接收前的谈话。难度：中级。
你的风格：严肃但不失亲切。问题要有一定深度，追问入党动机的具体内涵、对党的基本理论的理解。
当学生回答停留在表面时，用 follow_up_type=probe 追问更深层思考。
考察阶段依次为：开场寒暄 → 自我认知 → 入党动机 → 理论考察 → 情景假设。
当你认为已充分考察（通常是5-6轮后），将 finished 设为 true。
每轮回复JSON格式（不要输出其他内容）：
{"question": "你的下一个问题", "comment": "一句话点评刚才的回答", "finished": false, "phase": "当前阶段名", "follow_up_type": "probe|challenge|encourage"}""",

    "advanced": """你是一位大学党委书记，正在对预备期满的预备党员进行转正谈话。难度：高级。
你的风格：严肃深入，有压力感。考察重点放在理论深度、时政理解、复杂情景假设和自我剖析。
如果学生回答空泛或理论不足，用 challenge 指出并追问；如果答得好，用 encourage 提出更高要求。
考察阶段依次为：开场寒暄 → 自我认知 → 入党动机 → 理论考察（深） → 情景假设（难）。
当你认为已充分考察（通常是5-6轮后），将 finished 设为 true。
每轮回复JSON格式（不要输出其他内容）：
{"question": "你的下一个问题", "comment": "一句话点评刚才的回答", "finished": false, "phase": "当前阶段名", "follow_up_type": "probe|challenge|encourage"}""",
}

INTERVIEW_REPORT_PROMPT = """你是入党谈话评估专家。根据以下谈话记录，生成评估报告。
评分维度：思想认识、表达逻辑、入党动机、理论掌握、应变能力，每项0-100分。
对每个维度给出具体的改进建议（不要泛泛而谈，要结合谈话内容指出具体不足）。
同时给出总体等级（优秀85+/良好70+/需努力<70）和中肯的总体建议。
回复格式（JSON，不要输出其他内容）：
{"overall_score": 85, "grade": "良好", "dimension_scores": {"思想认识": 80, "表达逻辑": 85, "入党动机": 75, "理论掌握": 70, "应变能力": 90}, "dimension_analysis": [{"name": "思想认识", "score": 80, "suggestion": "具体改进建议"}], "strengths": ["优势1"], "weaknesses": ["不足1"], "suggestion": "总体建议", "total_rounds": 5}"""

DEBATE_STAGE_PROMPTS = {
    "opening": """你现在处于【立论】阶段——这是辩论的第一环节。你的任务：正面阐述你方的核心立场，给出2-3个有力论据。注意：你是在【立论】，不是在反驳。不要提到对方的观点，只陈述你自己的立场和理由。语气正式、自信。150-200字。""",
    "cross_exam": """你现在处于【质询】阶段——你要【提问】，不是反驳。你的任务：针对对方立论中的逻辑漏洞、证据缺失或前提假设，提出1-2个尖锐的质询问题。以问题的形式呈现，不要陈述你的观点。目的是迫使对方澄清或承认其论证的弱点。语气犀利但不失礼貌。""",
    "rebuttal": """你现在处于【驳论】阶段——这是辩论的核心环节。你的任务：逐点反驳对方的论证。指出对方在事实、逻辑或价值判断上的错误，并用反例或替代解释来论证。语气有力、逻辑严密。150-250字。""",
    "closing": """你现在处于【总结】阶段——这是辩论的最后一个环节。你的任务：总结你方全部论证，重申核心立场，将论证升华到更高价值层面。不要引入新论点，只在已有基础上做有感染力的总结。语气升华、有力，给裁判留下深刻印象。150-200字。""",
}

DEBATE_TOPICS_PROMPT = """你是一位思政辩论赛出题人。请生成3个有深度的思政类辩题，涵盖理想信念、社会热点、党史辨析、价值选择等类别。每个辩题包含正反方观点提示（提示是给本方的论点参考，不是教学说明）。
回复格式（JSON数组，不要输出其他内容）：
[{"title": "辩题", "category": "类别", "difficulty": "中级", "context": "背景说明", "pro_hint": "正方核心论点参考", "con_hint": "反方核心论点参考"}]"""

DEBATE_OPEN_PROMPT = "作为{side}方，请针对辩题'{topic}'做一段正式的开场立论，约150字。先表明你方立场，再给出2个核心论据。语气正式有力。"

DEBATE_FEEDBACK_PROMPT = """你是资深思政辩论赛裁判。从以下5个维度评分（每项0-100）：逻辑严谨性、知识运用、思辨深度、语言表达、临场反应。
注意：用户持【{stance_label}】立场，评估时应考虑该立场的论证难度。
对每个维度给出具体改进建议（结合辩论内容，不要泛泛而谈）。
回复格式（JSON，不要输出其他内容）：
{"overall_score": 80, "dimension_scores": {"逻辑严谨性": 80, "知识运用": 75, "思辨深度": 82, "语言表达": 78, "临场反应": 85}, "dimension_analysis": [{"name": "逻辑严谨性", "score": 80, "suggestion": "具体建议"}], "strengths": ["优势1"], "weaknesses": ["不足1"], "suggestion": "总体提升建议"}"""

HISTORY_TUTOR_PROMPT = "你是党史教育导师，正在带领学生沉浸式学习党史。用生动语言讲解历史背景和意义，鼓励学生深入思考。回复用口语化但严谨的中文。"

TOUR_GUIDE_PROMPT = "你是一位红色景点资深讲解员，正在带领学生在线参观红色教育基地。介绍景点的历史背景、重要事件和当代意义。语气热情、知识丰富。回复用口语化中文。"

TEMPLATE_GEN_PROMPT = "你是一位写作助手，帮助大学生撰写思政类文书。根据用户选择的模板类型和要求，生成规范、真诚、有思想深度的文书草稿。语言得体，避免空洞口号。"

KNOWLEDGE_HINT_PROMPT = "你是入党谈话辅导老师。学生正在回答一个问题，但可能不知如何表达。请根据当前问题给出一段150字以内的引导性提示，帮学生理清思路。不要给出标准答案，只提供思考方向。"


class AIService:
    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.api_base = settings.LLM_API_BASE
        self.model = settings.LLM_MODEL

    async def _call_api(self, messages: List[Dict], temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """Call DeepSeek API (OpenAI-compatible)"""
        if not self.api_key:
            raise RuntimeError("AI 服务未配置，请设置 LLM_API_KEY")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        async with httpx.AsyncClient(timeout=settings.KNOWLEDGE_LLM_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{self.api_base}/v1/chat/completions",
                headers=headers,
                json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    @staticmethod
    def _parse_json(text: str) -> dict | list:
        """Clean markdown code fences and common JSON errors from AI response"""
        import re
        text = text.strip()
        text = re.sub(r'^```(?:json)?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Remove trailing commas in arrays/objects (common AI mistake)
        text = re.sub(r',\s*}', '}', text)
        text = re.sub(r',\s*]', ']', text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Try to extract the first JSON object/array if there's extra text
        obj_match = re.search(r'\{.*\}', text, re.DOTALL)
        if obj_match:
            try:
                return json.loads(obj_match.group(0))
            except json.JSONDecodeError:
                pass
        raise

    # ===== Interview (5-phase, difficulty-aware, adaptive) =====
    def _interview_system_prompt(self, difficulty: str) -> str:
        return INTERVIEW_PROMPTS.get(difficulty, INTERVIEW_PROMPTS["intermediate"])

    async def interview_start(self, difficulty: str = "beginner") -> dict:
        system_prompt = self._interview_system_prompt(difficulty)
        msgs = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": '请开始一次入党谈话，先做简单开场寒暄并提第一个问题。phase 设为"开场寒暄"。直接回复JSON。'}
        ]
        resp = await self._call_api(msgs, temperature=0.8)
        return validate_interview_turn(self._parse_json(resp))

    async def interview_respond(self, conversation: List[Dict], difficulty: str = "intermediate") -> dict:
        system_prompt = self._interview_system_prompt(difficulty)
        msgs = [{"role": "system", "content": system_prompt}]
        for turn in conversation:
            msgs.append({"role": "user" if turn["role"] == "user" else "assistant", "content": turn["content"]})
        msgs.append({"role": "user", "content": "请评估学生刚才的回答，给出点评和下一个问题。根据回答质量选择 follow_up_type（浅答→probe，偏题→challenge，答得好→encourage）。直接回复JSON。"})
        resp = await self._call_api(msgs, temperature=0.8)
        return validate_interview_turn(self._parse_json(resp))

    async def interview_report(self, conversation: List[Dict]) -> dict:
        history = "\n".join([f"{'学生' if t['role']=='user' else '老师'}：{t['content']}" for t in conversation])
        msgs = [
            {"role": "system", "content": INTERVIEW_REPORT_PROMPT},
            {"role": "user", "content": f"请分析以下谈话记录并生成评估报告：\n{history}\n\n直接回复JSON格式，不要有任何额外内容。"}
        ]
        resp = await self._call_api(msgs, temperature=0.3, max_tokens=3000)
        return validate_interview_report(self._parse_json(resp))

    async def interview_hint(self, current_question: str) -> str:
        msgs = [
            {"role": "system", "content": KNOWLEDGE_HINT_PROMPT},
            {"role": "user", "content": f"当前谈话老师的问题是：{current_question}\n\n请给出引导性提示。"}
        ]
        return await self._call_api(msgs, temperature=0.5, max_tokens=300)

    # ===== History Learning =====
    async def history_ask(self, scenario_title: str, question: str, context: str = "") -> str:
        msgs = [
            {"role": "system", "content": HISTORY_TUTOR_PROMPT},
            {"role": "user", "content": f"我们正在学习'{scenario_title}'这段历史。可用资料：\n{context}\n\n学生问：{question}\n请只根据可用资料用200字以内回答；资料无法支持时明确说明当前情景资料没有足够依据。"}
        ]
        return await self._call_api(msgs, temperature=0.7, max_tokens=500)

    # ===== Tour Guide =====
    async def tour_intro(self, site_name: str) -> str:
        msgs = [
            {"role": "system", "content": TOUR_GUIDE_PROMPT},
            {"role": "user", "content": f"请以讲解员身份介绍红色景点'{site_name}'，包括历史背景和重要意义。200字以内。"}
        ]
        return await self._call_api(msgs, temperature=0.7, max_tokens=500)

    async def tour_ask(self, site_name: str, question: str) -> str:
        msgs = [
            {"role": "system", "content": TOUR_GUIDE_PROMPT},
            {"role": "user", "content": f"在'{site_name}'参观中，学生问：{question}\n请回答，150字以内。"}
        ]
        return await self._call_api(msgs, temperature=0.7, max_tokens=400)

    async def tour_report(self, site_name: str, qa_history: List[str]) -> str:
        history = "\n".join(qa_history)
        msgs = [
            {"role": "system", "content": "你是一位研学报告撰写助手。"},
            {"role": "user", "content": f"根据对'{site_name}'的参观学习，生成一份300字研学心得初稿。问答记录：\n{history}\n\n心得应包括：参观地点、历史背景、学习感悟、核心收获。"}
        ]
        return await self._call_api(msgs, temperature=0.7, max_tokens=800)

    # ===== Debate (4-phase, stage-aware, stance-aware) =====
    async def debate_generate_topics(self) -> List[Dict]:
        msgs = [
            {"role": "system", "content": DEBATE_TOPICS_PROMPT},
            {"role": "user", "content": "请生成3个辩论题目。直接回复JSON数组格式。"}
        ]
        resp = await self._call_api(msgs, temperature=0.9, max_tokens=2000)
        return validate_topics(self._parse_json(resp))

    async def debate_open(self, topic: str, stance: str) -> str:
        """Generate a real opening argument (not just a hint) for the opposing side."""
        side = "正" if stance == "con" else "反"
        msgs = [
            {"role": "system", "content": DEBATE_OPEN_PROMPT.format(side=side, topic=topic)},
            {"role": "user", "content": f"请开始你的立论。"}
        ]
        return await self._call_api(msgs, temperature=0.8, max_tokens=400)

    async def debate_argue(self, topic: str, stance: str, argument: str, conversation: List[Dict], stage: str = "rebuttal") -> str:
        side = "正方" if stance == "con" else "反方"
        stage_instruction = DEBATE_STAGE_PROMPTS.get(stage, DEBATE_STAGE_PROMPTS["rebuttal"])
        history = "\n".join([f"{'正方' if t.get('stance')=='pro' else '反方'}：{t['content']}" for t in conversation])
        msgs = [
            {"role": "system", "content": f"你是思政辩论赛的{side}辩手。辩题：{topic}。{stage_instruction}\n每次回复150-250字，保持礼貌但犀利。"},
            {"role": "user", "content": f"辩论历史：\n{history}\n\n对方最新观点：{argument}\n请以{side}立场回应。"}
        ]
        return await self._call_api(msgs, temperature=0.8, max_tokens=500)

    async def debate_feedback(self, topic: str, conversation: List[Dict], user_stance: str = "pro") -> Dict:
        stance_label = "正方" if user_stance == "pro" else "反方"
        history = "\n".join([
            f"{'【用户/正方】' if t.get('role') == 'user' and t.get('stance') == 'pro' else '【用户/反方】' if t.get('role') == 'user' and t.get('stance') == 'con' else '【AI对手】' if t.get('role') == 'ai' else ''}：{t['content']}"
            for t in conversation
        ])
        system_prompt = DEBATE_FEEDBACK_PROMPT.replace("{stance_label}", stance_label)
        msgs = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"辩题：{topic}\n辩论记录：\n{history}\n\n请评分。直接回复JSON。"}
        ]
        resp = await self._call_api(msgs, temperature=0.3, max_tokens=2000)
        return validate_debate_feedback(self._parse_json(resp))

    # ===== Template Generation =====
    async def generate_template(self, template_type: str, user_info: str = "") -> str:
        msgs = [
            {"role": "system", "content": TEMPLATE_GEN_PROMPT},
            {"role": "user", "content": f"请生成一份{template_type}的初稿。{user_info}。要求500-800字，格式规范，内容真诚有深度。"}
        ]
        return await self._call_api(msgs, temperature=0.7, max_tokens=2000)

    async def relevance_filter(self, question: str, contexts: List[Dict]) -> List[Dict]:
        """Batch judge relevance of each retrieved chunk via LLM. Returns chunks sorted by relevance DESC, score >= 5 only. Min 1 result."""
        if len(contexts) <= 3:
            return sorted(contexts, key=lambda c: c.get('score', 0), reverse=True)

        # Prepare candidates for batch scoring
        candidates = "\n---\n".join(
            f"[CANDIDATE {i}]\n标题: {c['title']}\n内容: {c['content'][:200]}"
            for i, c in enumerate(contexts)
        )
        msgs = [
            {"role": "system", "content": '你是一位信息检索质量审查员。对每个候选片段判断是否与问题相关。相关问题是指：该片段可以帮助回答问题、提供背景知识、或包含问题中的核心概念。评分标准：10=直接回答, 7=高度相关, 5=部分相关, 3=弱相关, 0=完全无关。回复JSON数组（不要输出其他内容）：[{"index": 0, "score": 8, "reason": "直接解释了核心概念"}]'},
            {"role": "user", "content": f"问题: {question}\n\n候选片段:\n{candidates}\n\n请评分每个候选片段，直接回复JSON数组。"}
        ]
        resp = await self._call_api(msgs, temperature=0.1, max_tokens=800)
        try:
            scores = self._parse_json(resp)
            if not isinstance(scores, list):
                raise ValueError("not a list")
        except Exception:
            # Fallback: keep all, sort by retrieval score
            return sorted(contexts, key=lambda c: c.get('score', 0), reverse=True)[:6]

        # Merge scores back into contexts
        score_map = {s.get('index', -1): s.get('score', 5) for s in scores if isinstance(s, dict)}
        for i, c in enumerate(contexts):
            c['relevance_score'] = score_map.get(i, 5)
            c['relevance_reason'] = next((s.get('reason', '') for s in scores if isinstance(s, dict) and s.get('index') == i), '')

        # Filter and sort
        filtered = [c for c in contexts if c.get('relevance_score', 5) >= 5]
        if not filtered:
            # Keep at least the highest-scoring one
            filtered = [sorted(contexts, key=lambda c: c.get('relevance_score', 0), reverse=True)[0]]

        return sorted(filtered, key=lambda c: c.get('relevance_score', 0), reverse=True)

    async def knowledge_answer(self, question: str, contexts: List[Dict]) -> str:
        evidence = "\n\n".join(
            f"[{index}] 《{item['title']}》\n{item['content']}"
            for index, item in enumerate(contexts, start=1)
        )
        messages = [
            {"role": "system", "content": '你是思政知识库助手。根据提供的资料回答问题，每个关键结论后用[1]、[2]标注。用资料中能找到的所有相关内容来回答，不要轻易说数据不足——资料即使不直接匹配主题，也可能包含相关信息。只有在所有资料都完全不相关时才能说未找到。回答应准确、简洁、使用中文。'},
            {"role": "user", "content": f"资料：\n{evidence}\n\n问题：{question}"},
        ]
        return await self._call_api(messages, temperature=0.5, max_tokens=1200)


# Global singleton
ai_service = AIService()
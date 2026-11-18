"""Idempotent development seed data used by both SQLite and PostgreSQL."""
import hashlib
import json
import logging
from pathlib import Path

from sqlalchemy import select

from app.database import SessionLocal
from app.immersive_seed import seed_immersive
from app.models.debate import DebateTopic
from app.models.domain import TeacherTask, TourSite
from app.models.history import HistoryScenario
from app.models.interview import InterviewScenario
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument, KnowledgeTemplate

logger = logging.getLogger(__name__)
CORPUS_PATH = Path(__file__).with_name("seed_data") / "knowledge_docs.json"

INTERVIEWS = [
    ("1", "入党积极分子谈话", "模拟党组织与入党积极分子的首次正式谈话", "beginner", 15, "张老师", "院党委组织委员"),
    ("2", "预备党员接收谈话", "发展对象转为预备党员前的组织谈话", "intermediate", 20, "李书记", "院党委副书记"),
    ("3", "预备党员转正谈话", "预备期满转为正式党员的组织谈话", "advanced", 25, "王书记", "院党委书记"),
    ("4", "随机模拟谈话", "随机抽取角色和难度进行综合检验", "random", 20, "AI考官", "随机角色"),
]

HISTORY = [
    ("1", "嘉兴南湖·中共一大", "新民主主义革命", 1921, "中共一大召开，宣告中国共产党正式成立。", 15),
    ("2", "遵义会议·伟大转折", "新民主主义革命", 1935, "遵义会议事实上确立了毛泽东在党中央和红军的领导地位。", 20),
    ("3", "开国大典·新中国诞生", "社会主义革命和建设", 1949, "中华人民共和国成立，中国人民从此站起来了。", 15),
    ("4", "十一届三中全会", "改革开放", 1978, "党的十一届三中全会开启改革开放和社会主义现代化建设新时期。", 15),
    ("5", "建党百年·全面小康", "新时代", 2021, "我国全面建成小康社会，实现第一个百年奋斗目标。", 15),
]

HISTORY_DETAILS = {
    "1": {
        "background": "1921年7月，来自各地的中国共产党早期组织代表在上海召开会议。会议后期因受到巡捕袭扰，转移到浙江嘉兴南湖的一艘游船上继续进行。代表们通过党的纲领和决议，确定党的名称与奋斗目标，中国共产党由此正式成立。",
        "points": [{"title": "会议成果", "content": "通过中国共产党第一个纲领，确定党的名称、奋斗目标和组织原则。"}, {"title": "历史意义", "content": "中国共产党的成立，是中华民族发展史上开天辟地的大事变。"}],
        "decision": {"text": "如果你是当时的青年代表，面对严密监视，最重要的行动原则是什么？", "options": [{"label": "立即停止会议，长期等待", "feedback": "保存力量很重要，但无限期等待会错失建立全国性政党的历史机遇。"}, {"label": "转移地点并保持组织纪律", "feedback": "这是兼顾安全与使命的选择，体现坚定理想和严密组织纪律。"}, {"label": "公开发布全部参会信息", "feedback": "在当时环境下会使代表和组织面临严重安全风险。"}]},
    },
    "2": {"background": "1935年1月，中央红军长征途中在贵州遵义召开政治局扩大会议。会议集中解决当时具有决定意义的军事和组织问题，纠正此前军事指挥上的错误，在极端危急关头挽救了党、红军和中国革命。", "points": [{"title": "核心议题", "content": "总结第五次反围剿失败和长征初期受挫的经验教训。"}, {"title": "历史意义", "content": "标志着中国共产党开始独立自主地解决中国革命的实际问题。"}], "decision": {"text": "面对连续失利，领导集体应如何作出纠偏？", "options": [{"label": "回避问题以维护表面团结", "feedback": "回避问题会让错误延续，真正的团结建立在实事求是基础上。"}, {"label": "基于事实开展批评并调整决策", "feedback": "这体现实事求是和独立自主，是遵义会议的重要启示。"}]}},
    "3": {"background": "1949年10月1日，中华人民共和国中央人民政府成立典礼在北京天安门广场举行。中华人民共和国的成立，结束了近代以来长期受侵略、受压迫的历史，开启人民当家作主的新纪元。", "points": [{"title": "国家新生", "content": "新中国成立标志着新民主主义革命取得基本胜利。"}, {"title": "人民立场", "content": "国家政权的根本性质体现人民当家作主。"}], "decision": {"text": "国家百废待兴，青年最应优先承担什么责任？", "options": [{"label": "只关注个人前途", "feedback": "个人发展与国家建设并不矛盾，但不能脱离时代责任。"}, {"label": "学习本领并投身国家建设", "feedback": "把个人理想融入国家发展，是当时青年担当的集中体现。"}]}},
    "4": {"background": "1978年12月，党的十一届三中全会在北京召开。会议把党和国家工作中心转移到经济建设上来，作出实行改革开放的历史性决策，实现新中国成立以来党的历史上具有深远意义的伟大转折。", "points": [{"title": "思想路线", "content": "重新确立解放思想、实事求是的思想路线。"}, {"title": "战略转折", "content": "开启改革开放和社会主义现代化建设新时期。"}], "decision": {"text": "面对发展中的新问题，改革最需要坚持什么？", "options": [{"label": "照搬其他国家模式", "feedback": "经验可以借鉴，但必须立足中国实际。"}, {"label": "解放思想并从实际出发", "feedback": "这是改革开放不断取得突破的重要方法。"}]}},
    "5": {"background": "2021年7月1日，庆祝中国共产党成立100周年大会在北京举行。中国向世界庄严宣告全面建成小康社会，历史性解决绝对贫困问题，实现第一个百年奋斗目标。", "points": [{"title": "百年成就", "content": "全面建成小康社会，中华民族伟大复兴进入不可逆转的历史进程。"}, {"title": "青年使命", "content": "新时代青年要把个人奋斗融入民族复兴伟业。"}], "decision": {"text": "站在新的历史起点，青年应怎样理解个人选择？", "options": [{"label": "个人发展与社会责任无关", "feedback": "个人选择始终处于社会发展之中，责任意识能赋予成长更深意义。"}, {"label": "把个人理想融入民族复兴", "feedback": "这体现新时代青年的使命意识，也能形成持久奋斗动力。"}]}},
}

TOURS = [
    ("1", "井冈山革命根据地", "江西省", "在罗霄山脉的险峻地形中，理解中国革命道路如何从实践中被探索出来。", "⛰️", ["1927年秋收起义部队向井冈山进军，开始创建革命根据地", "井冈山斗争探索了农村包围城市、武装夺取政权的道路", "土地革命、武装斗争和根据地建设在这里形成紧密联系", "坚定信念、艰苦奋斗、实事求是、敢闯新路是井冈山精神的重要内涵"]),
    ("2", "延安革命圣地", "陕西省", "走近窑洞、会址与山川，理解一个政党如何在艰苦环境中完成思想建设与力量凝聚。", "🏚️", ["1935年至1948年，延安是中共中央所在地和中国革命的指导中心", "延安整风推动全党在思想和行动上达到新的团结统一", "抗日军政大学等学校在艰苦条件下培养了大批干部和人才", "坚定正确的政治方向、解放思想实事求是、全心全意为人民服务、自力更生艰苦奋斗构成延安精神的重要内容"]),
    ("3", "西柏坡纪念馆", "河北省", "从普通山村走进“进京赶考”前夜，理解历史转折关头的清醒、纪律与人民立场。", "🏠", ["1948年中共中央移驻西柏坡，这里成为解放战争后期的指挥中心", "辽沈、淮海、平津三大战役在此期间得到战略指挥", "党的七届二中全会提出工作重心由乡村转向城市", "毛泽东提出“两个务必”，告诫全党保持谦虚谨慎和艰苦奋斗作风"]),
    ("4", "韶山毛泽东故居", "湖南省", "从成长环境与早年求索出发，观察个人志向如何在时代问题中逐渐形成。", "🌄", ["韶山是毛泽东出生和度过少年时期的地方", "早年劳动、读书与乡土生活构成其认识社会的重要经验", "青年时期对国家命运和社会问题的思考推动其走出乡关求学", "参访故居应把人物放回具体时代与社会环境中理解，避免脱离史实的简单神化"]),
    ("5", "遵义会议会址", "贵州省", "进入长征途中最关键的会议现场，理解独立自主解决中国革命实际问题的艰难转折。", "🏛️", ["1935年1月，中共中央政治局扩大会议在遵义召开", "会议集中解决当时最紧迫的军事和组织问题", "会议开始确立以毛泽东为主要代表的马克思主义正确路线在党中央的领导地位", "遵义会议是中国共产党独立自主解决中国革命实际问题的重要标志，在极端危急关头挽救了党、红军和中国革命"]),
]


def _seed_knowledge_corpus(db) -> None:
    """为全新数据库补入完整权威资料并建立分块与全文索引。

    语料文件由演示环境导出、随仓库分发；已存在同名资料时跳过，可重复执行。
    """
    if not CORPUS_PATH.is_file():
        return
    try:
        items = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("knowledge seed corpus unreadable path=%s", CORPUS_PATH, exc_info=True)
        return
    if not isinstance(items, list):
        return

    from app.services.knowledge_service import chunk_text, sync_fts

    existing = {title for (title,) in db.execute(select(KnowledgeDocument.title)).all()}
    added = 0
    for item in items:
        title = str(item.get("title") or "").strip()
        content = str(item.get("content") or "")
        if not title or not content or title in existing:
            continue
        document = KnowledgeDocument(
            title=title,
            category=item.get("category") or "党史",
            content=content,
            summary=item.get("summary") or "",
            source=item.get("source") or "",
            status="published",
        )
        db.add(document)
        db.flush()
        parts = chunk_text(content)
        chunks = [
            KnowledgeChunk(
                document_id=document.id,
                chunk_index=index,
                content=part,
                char_count=len(part),
                content_hash=hashlib.sha256(part.encode("utf-8")).hexdigest(),
            )
            for index, part in enumerate(parts)
        ]
        db.add_all(chunks)
        document.chunk_count = len(chunks)
        db.flush()
        db.commit()
        sync_fts(document.id, chunks)
        existing.add(title)
        added += 1
    if added:
        logger.info("knowledge corpus seeded documents=%s", added)


def seed_data() -> None:
    db = SessionLocal()
    try:
        if not db.scalar(select(InterviewScenario.id).limit(1)):
            for row in INTERVIEWS:
                db.add(InterviewScenario(id=row[0], title=row[1], description=row[2], difficulty=row[3], estimated_duration=row[4], ai_role_name=row[5], ai_role_title=row[6]))
        if not db.scalar(select(HistoryScenario.id).limit(1)):
            for index, row in enumerate(HISTORY):
                detail = HISTORY_DETAILS[row[0]]
                db.add(HistoryScenario(id=row[0], title=row[1], era=row[2], year_from=row[3], description=row[4], duration_estimate=row[5], order_index=index, background=detail["background"], knowledge_points_json=json.dumps(detail["points"], ensure_ascii=False), decision_points_json=json.dumps(detail["decision"], ensure_ascii=False)))
        else:
            for scenario_id, detail in HISTORY_DETAILS.items():
                scenario = db.get(HistoryScenario, scenario_id)
                if scenario:
                    scenario.background = detail["background"]
                    scenario.knowledge_points_json = json.dumps(detail["points"], ensure_ascii=False)
                    scenario.decision_points_json = json.dumps(detail["decision"], ensure_ascii=False)
        if not db.scalar(select(TourSite.id).limit(1)):
            for index, row in enumerate(TOURS):
                db.add(TourSite(id=row[0], name=row[1], location=row[2], description=row[3], emoji=row[4], facts_json=json.dumps(row[5], ensure_ascii=False), order_index=index))
        else:
            for index, row in enumerate(TOURS):
                site = db.get(TourSite, row[0])
                if site:
                    site.name = row[1]
                    site.location = row[2]
                    site.description = row[3]
                    site.emoji = row[4]
                    site.facts_json = json.dumps(row[5], ensure_ascii=False)
                    site.order_index = index
        if not db.scalar(select(DebateTopic.id).limit(1)):
            topics = [
                ("1", "理想信念比物质利益更能激励青年成长", "理想信念", "intermediate"),
                ("2", "人工智能的发展更有利于社会公平", "社会热点", "advanced"),
                ("3", "青年应该先立足本职还是先追求理想", "价值选择", "beginner"),
                ("4", "当代青年实现人生价值，更应着眼于个人奋斗还是时代机遇", "理想信念", "intermediate"),
                ("5", "人工智能的发展，是否将加剧社会治理的公平性危机", "社会热点", "intermediate"),
                ("6", "党史教育中，英雄人物的完美化塑造是否更有利于青年信仰传承", "党史辨析", "intermediate"),
                ("7", "理想主义对当代青年成长利大于弊还是弊大于利", "理想信念", "intermediate"),
                ("8", "在全球化背景下，爱国主义教育是否应更强调普世价值", "社会热点", "intermediate"),
                ("9", "中国共产党在抗日民族统一战线中的领导地位是历史选择还是策略结果", "党史辨析", "advanced"),
                ("10", "理想信念主要源于个人实践还是社会环境的塑造", "理想信念", "intermediate"),
                ("11", "面对社会热点问题，个人更应该坚持理性分析还是情感共鸣先行", "社会热点", "intermediate"),
                ("12", "在党史辨析中，历史人物的功过是否应当以当代价值观为标准来评价", "党史辨析", "intermediate"),
                ("13", "当代青年更应该追求理想的纯粹还是现实的适配", "理想信念", "intermediate"),
                ("14", "网络曝光对失德行为的监督作用是否大于其负面影响", "社会热点", "intermediate"),
                ("15", "历史评价应当以成功结果论英雄还是以过程动机论得失", "党史辨析", "advanced"),
            ]
            for topic in topics:
                db.add(DebateTopic(id=topic[0], title=topic[1], category=topic[2], difficulty=topic[3]))
        if not db.scalar(select(KnowledgeDocument.id).limit(1)):
            db.add_all([
                KnowledgeDocument(id="1", title="中国共产党章程（节选）", category="党章党规", content="中国共产党是中国工人阶级的先锋队，同时是中国人民和中华民族的先锋队，是中国特色社会主义事业的领导核心。", summary="党章总纲核心内容", source="共产党员网"),
                KnowledgeDocument(id="2", title="党的二十大报告学习要点", category="时政", content="高举中国特色社会主义伟大旗帜，全面贯彻习近平新时代中国特色社会主义思想，弘扬伟大建党精神。", summary="二十大报告学习摘要", source="新华社"),
                KnowledgeDocument(id="3", title="红船精神学习资料", category="党史", content="红船精神集中体现为开天辟地、敢为人先的首创精神，坚定理想、百折不挠的奋斗精神，立党为公、忠诚为民的奉献精神。", summary="红船精神权威学习摘要", source="中国共产党新闻网"),
            ])
        if not db.scalar(select(KnowledgeTemplate.id).limit(1)):
            db.add_all([
                KnowledgeTemplate(id="1", name="入党申请书", description="标准入党申请书格式", prompt="包含对党的认识、入党动机、个人情况和今后努力方向", order_index=1),
                KnowledgeTemplate(id="2", name="思想汇报", description="季度思想汇报", prompt="包含近期思想动态、理论学习心得、存在不足和改进措施", order_index=2),
                KnowledgeTemplate(id="3", name="心得体会", description="党史学习心得", prompt="包含学习内容、个人感悟、收获和实践计划", order_index=3),
                KnowledgeTemplate(id="4", name="个人自传", description="入党个人自传", prompt="包含成长经历、思想转变、入党动机和未来规划", order_index=4),
            ])
        if not db.scalar(select(TeacherTask.id).limit(1)):
            db.add_all([
                TeacherTask(id="1", title="完成入党谈话模拟练习", description="至少完成2次模拟练习", deadline="2026-06-25"),
                TeacherTask(id="2", title="阅读党史资料并写心得", description="提交不少于800字的学习心得", deadline="2026-06-30"),
            ])
        # Session.get() does not guarantee that the newly added legacy rows above
        # have been flushed.  The immersive seed resolves its source scenarios by
        # primary key, so a fresh database must flush those rows first.
        db.flush()
        seed_immersive(db)
        db.commit()
        _seed_knowledge_corpus(db)
    finally:
        db.close()

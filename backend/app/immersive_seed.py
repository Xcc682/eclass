"""Curated, idempotent content for the immersive historical books.

The captions deliberately avoid invented direct quotations.  Each reconstruction
is paired with a public, authoritative reference and an explicit reconstruction
label in the API payload.
"""
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import TourRecord, TourSite
from app.models.history import HistoryLearningRecord, HistoryScenario
from app.models.immersive import ImmersiveBook, ImmersiveProgress, ImmersiveSpread
from app.immersive_event_content import EVENT_TIMELINES


HISTORY_BOOKS = [
    {
        "id": "history-1", "source_id": "1", "title": "启航", "subtitle": "嘉兴南湖 · 中共一大现场纪事",
        "era": "1921", "location": "上海 · 嘉兴南湖", "image": "/static/images/immersive/history-1-01.webp",
        "arrival": "暮色压低了石库门屋檐。你随人群拐进窄巷，脚步声在潮湿的砖墙间回响。",
        "explore": "留意门窗、文件与转移路线：一次会议如何在严密环境中继续进行？",
        "person": "会场中的代表来自不同地区。画面只呈现集体讨论与谨慎转移，不虚构任何人物原话。",
        "outcome": "议程在南湖游船上继续。纲领和决议被通过，一个新的政党由此诞生。",
        "reflection": "在风险与使命同时出现时，严密组织为何成为理想落地的条件？",
        "source": {"title": "中国共产党第一次全国代表大会（1921年7月23日—闭幕）", "organization": "国家发展和改革委员会", "url": "https://www.ndrc.gov.cn/fggz/fgjh/djzc/202103/t20210324_1273303_ext.html", "excerpt": "南湖会议继续议题并通过党的第一个纲领，确定党的名称、奋斗目标和组织制度。"},
    },
    {
        "id": "history-2", "source_id": "2", "title": "转折", "subtitle": "遵义会议 · 长征危局中的选择",
        "era": "1935", "location": "贵州遵义", "image": "/static/images/immersive/history-2-01.webp",
        "arrival": "冬雨落在黔北街巷。行军地图被带进楼内，会议灯火彻夜未熄。",
        "explore": "从地图、行军路线与会议桌上的材料中，寻找危局形成的线索。",
        "person": "与会者围绕军事和组织问题展开讨论。这里呈现的是经史料确认的议题，不复刻未经证实的对白。",
        "outcome": "会议纠正此前军事指挥上的错误，开始形成更加成熟、能够独立解决实际问题的领导集体。",
        "reflection": "真正的团结，为什么需要在事实面前检验和修正决策？",
        "source": {"title": "遵义会议的伟大意义和深刻启示", "organization": "中华人民共和国财政部", "url": "https://ha.mof.gov.cn/zt/djzc/djzl/201505/t20150513_1231207.htm", "excerpt": "遵义会议在极端危急关头挽救了党、红军和中国革命，是具有伟大转折意义的会议。"},
    },
    {
        "id": "history-3", "source_id": "3", "title": "新生", "subtitle": "开国大典 · 人民成为国家主人",
        "era": "1949", "location": "北京天安门广场", "image": "/static/images/immersive/history-3-01.webp",
        "arrival": "十月的天空高远，广场上旗帜与人潮铺向视线尽头。你站在普通见证者的位置。",
        "explore": "观察城楼、广场、队伍与新国旗，理解国家新生如何进入普通人的生活。",
        "person": "画面聚焦来自不同地区和群体的群众。人物均为艺术化群像，不指认真实个体。",
        "outcome": "中华人民共和国中央人民政府成立，中国人民从此成为国家的主人。",
        "reflection": "当国家百废待兴，个人学习与劳动如何同公共建设连接起来？",
        "source": {"title": "1949年10月1日 中华人民共和国开国大典", "organization": "深圳市盐田区档案与史志信息网", "url": "https://www.yantian.gov.cn/ytdayszxxw/lsjt/content/post_11735057.html", "excerpt": "中华人民共和国成立，开启了人民当家作主的历史新纪元。"},
    },
    {
        "id": "history-4", "source_id": "4", "title": "春潮", "subtitle": "十一届三中全会 · 改革开放序章",
        "era": "1978", "location": "北京", "image": "/static/images/immersive/history-4-01.webp",
        "arrival": "冬日北京，文件翻动与铅笔记录的声音交织。讨论指向国家今后的工作重心。",
        "explore": "从报纸、生产数据和讨论提纲中，观察思想解放与现实问题如何彼此回应。",
        "person": "会议参与者围绕发展道路深入讨论。场景强调集体决策过程，不编造人物发言。",
        "outcome": "党和国家工作重心转向经济建设，改革开放和社会主义现代化建设新时期由此开启。",
        "reflection": "为什么从实际出发，往往意味着既要有勇气，也要有持续验证的耐心？",
        "source": {"title": "改革开放四十年大事记（节选）", "organization": "中国政府网", "url": "https://www.gov.cn/xinwen/2018-12/17/content_5349420.htm", "excerpt": "党的十一届三中全会作出把工作中心转移到经济建设上来、实行改革开放的历史性决策。"},
    },
    {
        "id": "history-5", "source_id": "5", "title": "山河答卷", "subtitle": "建党百年 · 全面小康纪事",
        "era": "2021", "location": "中国", "image": "/static/images/immersive/history-5-01.webp",
        "arrival": "清晨从城市站台延伸到山村公路。镜头掠过学校、诊所、工厂与新居。",
        "explore": "从家庭账本、村庄道路和公共服务变化中，寻找宏大目标落在日常生活里的证据。",
        "person": "建设者、教师、医务人员与普通家庭共同构成这幅群像；画面人物均为虚构见证者。",
        "outcome": "全面建成小康社会，第一个百年奋斗目标实现，并开启新的历史征程。",
        "reflection": "一项跨越数十年的公共目标，怎样由一代代普通人的行动共同完成？",
        "source": {"title": "全面建成小康社会的重大意义与启示", "organization": "全国哲学社会科学工作办公室", "url": "https://www.nopss.gov.cn/n1/2021/1013/c219544-32251942.html", "excerpt": "全面建成小康社会是接续奋斗的成果，也是迈向现代化强国新征程的重要里程碑。"},
    },
]


TOUR_BOOKS = [
    {
        "id": "tour-1", "source_id": "1", "title": "井冈山", "subtitle": "山路之上，寻找道路的起点",
        "era": "当代抵达 · 1927历史之窗", "location": "江西省井冈山市", "image": "/static/images/immersive/tour-1-01.webp",
        "arrival": "你从今天的山路抵达。松涛、雾气和石阶都是真实地貌信息；历史人物与行动画面为艺术化复原。",
        "explore": "沿山路、旧居与地形寻找线索，思考根据地建设为何必须回应当地实际。",
        "person": "故事以早期根据地军民群体为线索，不指定虚构人物为真实历史人物。",
        "reflection": "自然地形、群众基础和组织建设之间，形成了怎样的联系？",
        "source": {"title": "井冈山：燃起中国革命启明灯", "organization": "国家林业和草原局", "url": "https://www.forestry.gov.cn/c/www/ghlc/145656.jhtml", "excerpt": "1927年10月，秋收起义部队到达井冈山地区，开始创建农村革命根据地；1928年井冈山会师后，根据地建设进入新阶段。"},
    },
    {
        "id": "tour-2", "source_id": "2", "title": "延安", "subtitle": "窑洞灯火与思想的力量",
        "era": "当代抵达 · 1935—1948历史之窗", "location": "陕西省延安市", "image": "/static/images/immersive/tour-2-01.webp",
        "arrival": "今天的参访道路通向窑洞旧址。风吹过黄土坡，历史之窗从一盏灯缓缓亮起。",
        "explore": "留意窑洞、简朴桌椅、学校与生产工具，它们共同说明艰苦环境中的组织与学习。",
        "person": "以学习、生产和服务群众的群体经历推进场景，不制造未经来源支持的英雄故事。",
        "reflection": "物质条件有限时，思想建设和共同目标为什么格外重要？",
        "source": {"title": "延安革命纪念馆", "organization": "中央纪委国家监委网站", "url": "https://www.ccdi.gov.cn/special/kz70/201508/t20150824_61000.html", "excerpt": "延安是中共中央所在地和中国革命的指导中心，也是重要的革命纪念地。"},
    },
    {
        "id": "tour-3", "source_id": "3", "title": "西柏坡", "subtitle": "进京赶考前夜",
        "era": "当代抵达 · 1948—1949历史之窗", "location": "河北省平山县", "image": "/static/images/immersive/tour-3-01.webp",
        "arrival": "普通北方村落的院墙之后，是今天仍可辨认的旧址格局。镜头从当代院落推向历史地图。",
        "explore": "寻找作战室、地图、电报与会议旧址之间的联系，理解普通村庄何以成为历史枢纽。",
        "person": "电报员、工作人员和村民构成叙事群像，具体行为仅采用资料能够支持的范围。",
        "reflection": "从乡村走向全国执政，为什么更需要清醒、纪律与人民立场？",
        "source": {"title": "精神篇：西柏坡精神", "organization": "国家发展和改革委员会", "url": "https://www.ndrc.gov.cn/fggz/fgjh/djzc/202104/t20210429_1278666.html", "excerpt": "西柏坡见证了历史转折，也形成了以谦虚谨慎、艰苦奋斗等为重要内涵的精神传统。"},
    },
    {
        "id": "tour-4", "source_id": "4", "title": "韶山", "subtitle": "从乡土生活走向时代追问",
        "era": "当代抵达 · 少年与青年时期之窗", "location": "湖南省韶山市", "image": "/static/images/immersive/tour-4-01.webp",
        "arrival": "稻田、水塘与土木旧居构成今天可见的环境。历史之窗只复原时代生活，不替人物编写台词。",
        "explore": "从农具、书桌、私塾与乡土环境中，观察成长经历如何形成对社会问题的关切。",
        "person": "叙事聚焦乡村家庭、读书与劳动背景，避免脱离时代条件的个人神话。",
        "reflection": "理解一位历史人物，为什么既要看个人志向，也要看他所处的社会环境？",
        "source": {"title": "韶山毛泽东同志纪念馆（故居）", "organization": "湖南省人民政府", "url": "https://www.hunan.gov.cn/hnszf/c101476/202108/t20210826_20400004.html", "excerpt": "纪念馆和旧址群系统展示人物生平、成长环境与相关历史遗存。"},
    },
    {
        "id": "tour-5", "source_id": "5", "title": "遵义", "subtitle": "在危局中校准方向",
        "era": "当代抵达 · 1935历史之窗", "location": "贵州省遵义市", "image": "/static/images/immersive/tour-5-01.webp",
        "arrival": "你从今天的会址庭院进入。门窗、砖墙与街巷属于当代实景信息，室内讨论为艺术化复原。",
        "explore": "通过会址布局、行军地图与时间线，理解会议面对的紧迫军事和组织问题。",
        "person": "场景呈现集体讨论与决策纠偏，不将旁白写成任何历史人物的直接发言。",
        "reflection": "当既有方案不断受挫，独立判断应当建立在什么基础上？",
        "source": {"title": "遵义1935：早到的春天", "organization": "中华人民共和国国防部", "url": "https://www.mod.gov.cn/gfbw/gfjy_index/js_214151/16364674.html", "excerpt": "1935年1月15日至17日，中共中央政治局在遵义召开扩大会议。"},
    },
]


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _spread(book: dict, index: int, spread_type: str, narration: str, scene: dict, source_refs: list[dict] | None = None) -> dict:
    positions = ["center", "45% center", "65% center", "35% center", "55% center", "center", "center", "center"]
    # Eight spreads use six authored cinematic scenes.  Cover/arrival share the
    # establishing shot; archive/ending share the quiet closing shot.
    scene_number = (1, 1, 2, 3, 4, 5, 6, 6)[index]
    image_url = f"/static/images/immersive/{book['id']}-{scene_number:02d}.webp"
    timeline = EVENT_TIMELINES[book["id"]]
    event_indexes = (0, 0, 1, 2, 3, 4, 4, 4) if book["id"].startswith("history-") else (0, 0, 1, 2, 3, 3, 4, 4)
    event_index = event_indexes[index]
    event = timeline[event_index]
    return {
        "id": f"{book['id']}-{index + 1:02d}", "order_index": index, "spread_type": spread_type,
        "layout": "archive" if spread_type == "archive" else "cinematic",
        "image_url": image_url, "thumbnail_url": image_url, "audio_url": "", "narration": narration,
        "scene": {
            "position": positions[index], "scale": 1 + (index % 3) * 0.04,
            "reconstruction": True, "event": event, "timeline": timeline,
            "timeline_index": event_index, **scene,
        },
        "sources": source_refs or [],
    }


def _history_spreads(book: dict, scenario: HistoryScenario) -> list[dict]:
    decision = json.loads(scenario.decision_points_json or "{}")
    timeline = EVENT_TIMELINES[book["id"]]
    hotspots = [
        {"id": f"clue-{i + 1}", "x": [27, 64, 77][i], "y": [56, 36, 68][i],
         "title": item["title"], "content": f"{item['date']}，{item['place']}。{item['summary']} {item['meaning']}"}
        for i, item in enumerate(timeline[1:4])
    ]
    options = [{"id": f"choice-{i}", "label": row.get("label", "观察这一方向"), "feedback": row.get("feedback", "选择只改变观察顺序，不改变历史结果。")}
               for i, row in enumerate(decision.get("options", [])[:3])]
    source = book["source"]
    return [
        _spread(book, 0, "cover", "", {"eyebrow": f"党史现场纪事 · 卷{book['source_id']}", "title": book["title"], "caption": book["subtitle"], "cta": "推开书页"}),
        _spread(book, 1, "cinematic", book["arrival"], {"eyebrow": "抵达", "title": "成为一名现场见证者", "caption": "第一人称情景入口", "particles": "rain" if book["id"] == "history-2" else "dust"}),
        _spread(book, 2, "exploration", book["explore"], {"eyebrow": "环境探索", "title": "从现场找到证据", "caption": "点击画面中的光点", "hotspots": hotspots}),
        _spread(book, 3, "dialogue", book["person"], {"eyebrow": "人物时刻", "title": "行动比台词更接近历史", "caption": "叙事字幕 · 非历史人物原话", "dialogue": "镜头记录讨论、观察、转移与协作。"}),
        _spread(book, 4, "decision", decision.get("text", "你希望先从哪个方向观察？"), {"eyebrow": "历史抉择", "title": "选择你的观察方向", "caption": "选择不改变真实历史结果", "options": options}),
        _spread(book, 5, "cinematic", book["outcome"], {"eyebrow": "结果展开", "title": "历史向前推进", "caption": scenario.description or ""}),
        _spread(book, 6, "archive", source["excerpt"], {"eyebrow": "史料插页", "title": source["title"], "caption": source["organization"], "archive_excerpt": source["excerpt"]}, [source]),
        _spread(book, 7, "ending", book["reflection"], {"eyebrow": "余韵与归档", "title": "把这一卷收入记忆", "caption": "可向 AI 史官追问，再盖上归档印章", "prompt": book["reflection"], "cta": "完成本卷"}, [source]),
    ]


def _tour_spreads(book: dict, site: TourSite) -> list[dict]:
    timeline = EVENT_TIMELINES[book["id"]]
    hotspots = [
        {"id": f"clue-{i + 1}", "x": [24, 58, 78][i], "y": [62, 34, 56][i],
         "title": item["title"], "content": f"{item['date']}，{item['place']}。{item['summary']} {item['meaning']}"}
        for i, item in enumerate(timeline[1:4])
    ]
    source = book["source"]
    return [
        _spread(book, 0, "cover", "", {"eyebrow": f"红色山河研学图志 · 第{book['source_id']}站", "title": book["title"], "caption": book["subtitle"], "cta": "展开行装"}),
        _spread(book, 1, "cinematic", book["arrival"], {"eyebrow": "当代抵达", "title": "先看见今天的现场", "caption": book["location"], "contemporary": True}),
        _spread(book, 2, "cinematic", "画面由当代现场缓慢过渡至对应年代。建筑与环境参考公开资料，人物为艺术化群像。", {"eyebrow": "历史之窗", "title": book["era"], "caption": "AI 艺术化历史复原", "particles": "mist"}),
        _spread(book, 3, "exploration", book["explore"], {"eyebrow": "现场寻迹", "title": "让旧物与地形开口", "caption": "发现至少一处线索", "hotspots": hotspots}),
        _spread(book, 4, "dialogue", book["person"], {"eyebrow": "人物故事", "title": "从一个群体理解一段历史", "caption": "群像叙事 · 不虚构人物原话", "dialogue": "把个人经历放回时代、地理与社会关系中。"}),
        _spread(book, 5, "reflection", "你可以围绕当前场景追问。AI 导览员只根据本卷资料作答，依据不足时会明确说明。", {"eyebrow": "随行追问", "title": "向现场提出一个好问题", "caption": "问答将保存到本次研学记录", "prompt": book["reflection"]}, [source]),
        _spread(book, 6, "reflection", book["reflection"], {"eyebrow": "研学手记", "title": "写下你看见的联系", "caption": "不少于 20 字，可继续修改", "note_placeholder": "我在现场注意到……这让我重新理解了……"}, [source]),
        _spread(book, 7, "ending", source["excerpt"], {"eyebrow": "行程归档", "title": "让观察成为一份答卷", "caption": source["organization"], "cta": "生成报告并点亮印章"}, [source]),
    ]


def _upsert_book(db: Session, config: dict, module: str, spreads: list[dict]) -> None:
    book = db.get(ImmersiveBook, config["id"])
    if not book:
        book = ImmersiveBook(id=config["id"], module=module, source_id=config["source_id"], title=config["title"])
        db.add(book)
    book.module = module
    book.source_id = config["source_id"]
    book.title = config["title"]
    book.subtitle = config["subtitle"]
    book.era = config["era"]
    book.location = config["location"]
    book.cover_url = config["image"]
    book.version = 3
    book.status = "published"
    book.duration_estimate = 16 if module == "history" else 18
    book.order_index = int(config["source_id"]) - 1
    book.updated_at = datetime.utcnow()
    db.flush()
    for item in spreads:
        spread = db.get(ImmersiveSpread, item["id"])
        if not spread:
            spread = ImmersiveSpread(id=item["id"], book_id=book.id, order_index=item["order_index"], spread_type=item["spread_type"])
            db.add(spread)
        spread.book_id = book.id
        spread.order_index = item["order_index"]
        spread.spread_type = item["spread_type"]
        spread.layout = item["layout"]
        spread.image_url = item["image_url"]
        spread.thumbnail_url = item["thumbnail_url"]
        spread.audio_url = item["audio_url"]
        spread.narration = item["narration"]
        spread.scene_json = _json(item["scene"])
        spread.source_refs_json = _json(item["sources"])


def _migrate_progress(db: Session) -> None:
    for record in db.scalars(select(HistoryLearningRecord)).all():
        book_id = f"history-{record.scenario_id}"
        if not db.get(ImmersiveBook, book_id):
            continue
        progress = db.scalar(select(ImmersiveProgress).where(ImmersiveProgress.user_id == record.user_id, ImmersiveProgress.book_id == book_id))
        if not progress:
            progress = ImmersiveProgress(user_id=record.user_id, book_id=book_id)
            db.add(progress)
        progress.current_spread = 7 if record.completed else min(7, max(progress.current_spread or 0, round((record.progress or 0) * 7 / 100)))
        progress.completed = bool(record.completed)
        progress.completed_at = record.completed_at
        progress.qa_json = record.qa_json or "[]"
        if record.choice_index is not None:
            progress.choice_json = _json({"spread_id": f"{book_id}-05", "option_id": f"choice-{record.choice_index}"})

    for record in db.scalars(select(TourRecord)).all():
        book_id = f"tour-{record.site_id}"
        if not db.get(ImmersiveBook, book_id):
            continue
        progress = db.scalar(select(ImmersiveProgress).where(ImmersiveProgress.user_id == record.user_id, ImmersiveProgress.book_id == book_id))
        if not progress:
            progress = ImmersiveProgress(user_id=record.user_id, book_id=book_id)
            db.add(progress)
        progress.current_spread = 7 if record.completed else max(progress.current_spread or 0, 1)
        progress.completed = bool(record.completed)
        progress.completed_at = record.completed_at
        progress.qa_json = record.qa_json or "[]"
        progress.related_record_id = record.id


def seed_immersive(db: Session) -> None:
    for config in HISTORY_BOOKS:
        scenario = db.get(HistoryScenario, config["source_id"])
        if scenario:
            _upsert_book(db, config, "history", _history_spreads(config, scenario))
    for config in TOUR_BOOKS:
        site = db.get(TourSite, config["source_id"])
        if site:
            _upsert_book(db, config, "tour", _tour_spreads(config, site))
    db.flush()
    _migrate_progress(db)

"""Curated, idempotent content for the immersive historical books.

The captions deliberately avoid invented direct quotations.  Each reconstruction
is paired with a public, authoritative reference and an explicit reconstruction
label in the API payload.
"""
import json
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.immersive_branch_content import BRANCH_STORIES
from app.immersive_event_content import CLUE_POSITIONS, EVENT_TIMELINES, SCENE_CLUES
from app.models.domain import TourRecord, TourSite
from app.models.history import HistoryLearningRecord, HistoryScenario
from app.models.immersive import ImmersiveBook, ImmersiveProgress, ImmersiveSpread

HISTORY_BOOKS = [
    {
        "id": "history-1", "source_id": "1", "title": "启航", "subtitle": "嘉兴南湖 · 中共一大现场纪事",
        "era": "1921", "location": "上海 · 嘉兴南湖", "image": "/static/images/immersive/history-1-01.webp",
        "arrival": "暮色压低了石库门屋檐。你随人群拐进窄巷，脚步声在潮湿的砖墙间回响。",
        "explore": "留意门窗、文件与转移路线：一次会议如何在严密环境中继续进行？",
        "person": "陌生人闯入后，代表们立即停止讨论、收起材料并分散离开。短暂的沉默背后，是一次迅速而克制的集体应变。",
        "outcome": "议程在南湖游船上继续。纲领和决议被通过，一个新的政党由此诞生。",
        "reflection": "在风险与使命同时出现时，严密组织为何成为理想落地的条件？",
        "source": {"title": "中国共产党第一次全国代表大会（1921年7月23日—闭幕）", "organization": "国家发展和改革委员会", "url": "https://www.ndrc.gov.cn/fggz/fgjh/djzc/202103/t20210324_1273303_ext.html", "excerpt": "南湖会议继续议题并通过党的第一个纲领，确定党的名称、奋斗目标和组织制度。"},
    },
    {
        "id": "history-2", "source_id": "2", "title": "转折", "subtitle": "遵义会议 · 长征危局中的选择",
        "era": "1935", "location": "贵州遵义", "image": "/static/images/immersive/history-2-01.webp",
        "arrival": "冬雨落在黔北街巷。行军地图被带进楼内，会议灯火彻夜未熄。",
        "explore": "从地图、行军路线与会议桌上的材料中，寻找危局形成的线索。",
        "person": "桌上的行军图被反复展开。与会者从湘江战役的损失谈起，重新检视第五次反“围剿”以来的军事指挥。",
        "outcome": "会议纠正此前军事指挥上的错误，开始形成更加成熟、能够独立解决实际问题的领导集体。",
        "reflection": "真正的团结，为什么需要在事实面前检验和修正决策？",
        "source": {"title": "遵义会议的伟大意义和深刻启示", "organization": "中华人民共和国财政部", "url": "https://ha.mof.gov.cn/zt/djzc/djzl/201505/t20150513_1231207.htm", "excerpt": "遵义会议在极端危急关头挽救了党、红军和中国革命，是具有伟大转折意义的会议。"},
    },
    {
        "id": "history-3", "source_id": "3", "title": "新生", "subtitle": "开国大典 · 人民成为国家主人",
        "era": "1949", "location": "北京天安门广场", "image": "/static/images/immersive/history-3-01.webp",
        "arrival": "十月的天空高远，广场上旗帜与人潮铺向视线尽头。你站在普通见证者的位置。",
        "explore": "观察城楼、广场、队伍与新国旗，理解国家新生如何进入普通人的生活。",
        "person": "工人、学生、市民和来自各地的代表汇入广场。对许多人来说，这是第一次亲眼看见新国旗升起。",
        "outcome": "中华人民共和国中央人民政府成立，中国人民从此成为国家的主人。",
        "reflection": "当国家百废待兴，个人学习与劳动如何同公共建设连接起来？",
        "source": {"title": "1949年10月1日 中华人民共和国开国大典", "organization": "深圳市盐田区档案与史志信息网", "url": "https://www.yantian.gov.cn/ytdayszxxw/lsjt/content/post_11735057.html", "excerpt": "中华人民共和国成立，开启了人民当家作主的历史新纪元。"},
    },
    {
        "id": "history-4", "source_id": "4", "title": "春潮", "subtitle": "十一届三中全会 · 改革开放序章",
        "era": "1978", "location": "北京", "image": "/static/images/immersive/history-4-01.webp",
        "arrival": "冬日北京，文件翻动与铅笔记录的声音交织。讨论指向国家今后的工作重心。",
        "explore": "从报纸、生产数据和讨论提纲中，观察思想解放与现实问题如何彼此回应。",
        "person": "文件、报纸和生产数据在会场内传阅。讨论不再停留在口号，而是转向怎样解决积累已久的现实问题。",
        "outcome": "党和国家工作重心转向经济建设，改革开放和社会主义现代化建设新时期由此开启。",
        "reflection": "为什么从实际出发，往往意味着既要有勇气，也要有持续验证的耐心？",
        "source": {"title": "改革开放四十年大事记（节选）", "organization": "中国政府网", "url": "https://www.gov.cn/xinwen/2018-12/17/content_5349420.htm", "excerpt": "党的十一届三中全会作出把工作中心转移到经济建设上来、实行改革开放的历史性决策。"},
    },
    {
        "id": "history-5", "source_id": "5", "title": "山河答卷", "subtitle": "建党百年 · 全面小康纪事",
        "era": "2021", "location": "中国", "image": "/static/images/immersive/history-5-01.webp",
        "arrival": "清晨从城市站台延伸到山村公路。镜头掠过学校、诊所、工厂与新居。",
        "explore": "从家庭账本、村庄道路和公共服务变化中，寻找宏大目标落在日常生活里的证据。",
        "person": "教师走进乡村课堂，医生守在基层诊室，工人整理当天的订单。宏大的目标正由这些日常工作共同完成。",
        "outcome": "全面建成小康社会，第一个百年奋斗目标实现，并开启新的历史征程。",
        "reflection": "一项跨越数十年的公共目标，怎样由一代代普通人的行动共同完成？",
        "source": {"title": "全面建成小康社会的重大意义与启示", "organization": "全国哲学社会科学工作办公室", "url": "https://www.nopss.gov.cn/n1/2021/1013/c219544-32251942.html", "excerpt": "全面建成小康社会是接续奋斗的成果，也是迈向现代化强国新征程的重要里程碑。"},
    },
]


TOUR_BOOKS = [
    {
        "id": "tour-1", "source_id": "1", "title": "井冈山", "subtitle": "山路之上，寻找道路的起点",
        "era": "当代抵达 · 1927历史之窗", "location": "江西省井冈山市", "image": "/static/images/immersive/tour-1-01.webp",
        "arrival": "你沿着雨后的山路抵达井冈山。红土、密林和陡峭山势，正是当年队伍选择落脚地时必须面对的现实条件。",
        "explore": "沿山路、旧居与地形寻找线索，思考根据地建设为何必须回应当地实际。",
        "person": "山路上，部队与村民一同转运粮食和伤员；在茅坪、茨坪，党组织、医院和留守处逐步建立起来。",
        "reflection": "自然地形、群众基础和组织建设之间，形成了怎样的联系？",
        "source": {"title": "井冈山：燃起中国革命启明灯", "organization": "国家林业和草原局", "url": "https://www.forestry.gov.cn/c/www/ghlc/145656.jhtml", "excerpt": "1927年10月，秋收起义部队到达井冈山地区，开始创建农村革命根据地；1928年井冈山会师后，根据地建设进入新阶段。"},
    },
    {
        "id": "tour-2", "source_id": "2", "title": "延安", "subtitle": "窑洞灯火与思想的力量",
        "era": "当代抵达 · 1935—1948历史之窗", "location": "陕西省延安市", "image": "/static/images/immersive/tour-2-01.webp",
        "arrival": "今天的参访道路通向窑洞旧址。风吹过黄土坡，历史之窗从一盏灯缓缓亮起。",
        "explore": "留意窑洞、简朴桌椅、学校与生产工具，它们共同说明艰苦环境中的组织与学习。",
        "person": "窑洞里有人伏案学习，坡地上有人开荒生产。读书、讨论与劳动，共同支撑着延安时期的日常生活。",
        "reflection": "物质条件有限时，思想建设和共同目标为什么格外重要？",
        "source": {"title": "延安革命纪念馆", "organization": "中央纪委国家监委网站", "url": "https://www.ccdi.gov.cn/special/kz70/201508/t20150824_61000.html", "excerpt": "延安是中共中央所在地和中国革命的指导中心，也是重要的革命纪念地。"},
    },
    {
        "id": "tour-3", "source_id": "3", "title": "西柏坡", "subtitle": "进京赶考前夜",
        "era": "当代抵达 · 1948—1949历史之窗", "location": "河北省平山县", "image": "/static/images/immersive/tour-3-01.webp",
        "arrival": "普通北方村落的院墙之后，是今天仍可辨认的旧址格局。镜头从当代院落推向历史地图。",
        "explore": "寻找作战室、地图、电报与会议旧址之间的联系，理解普通村庄何以成为历史枢纽。",
        "person": "电报员守着机器记录指令，工作人员在地图前核对战局，村民把粮食和柴草送进院落。小村庄由此连接全国战场。",
        "reflection": "从乡村走向全国执政，为什么更需要清醒、纪律与人民立场？",
        "source": {"title": "精神篇：西柏坡精神", "organization": "国家发展和改革委员会", "url": "https://www.ndrc.gov.cn/fggz/fgjh/djzc/202104/t20210429_1278666.html", "excerpt": "西柏坡见证了历史转折，也形成了以谦虚谨慎、艰苦奋斗等为重要内涵的精神传统。"},
    },
    {
        "id": "tour-4", "source_id": "4", "title": "韶山", "subtitle": "从乡土生活走向时代追问",
        "era": "当代抵达 · 少年与青年时期之窗", "location": "湖南省韶山市", "image": "/static/images/immersive/tour-4-01.webp",
        "arrival": "稻田、水塘和土木旧居仍保留着湘中乡村的空间尺度。先从这片生活环境出发，再理解一个少年的成长。",
        "explore": "从农具、书桌、私塾与乡土环境中，观察成长经历如何形成对社会问题的关切。",
        "person": "白天参加田间劳动，夜晚继续读书。乡村生活中的劳作、见闻和疑问，逐渐把目光引向更大的世界。",
        "reflection": "理解一位历史人物，为什么既要看个人志向，也要看他所处的社会环境？",
        "source": {"title": "韶山毛泽东同志纪念馆（故居）", "organization": "湖南省人民政府", "url": "https://www.hunan.gov.cn/hnszf/c101476/202108/t20210826_20400004.html", "excerpt": "纪念馆和旧址群系统展示人物生平、成长环境与相关历史遗存。"},
    },
    {
        "id": "tour-5", "source_id": "5", "title": "遵义", "subtitle": "在危局中校准方向",
        "era": "当代抵达 · 1935历史之窗", "location": "贵州省遵义市", "image": "/static/images/immersive/tour-5-01.webp",
        "arrival": "你从今天的会址庭院进入。雨水沿灰砖和木窗落下，二楼那间不大的会议室，曾容纳一次关系全局的讨论。",
        "explore": "通过会址布局、行军地图与时间线，理解会议面对的紧迫军事和组织问题。",
        "person": "地图旁的讨论持续了三天。与会者把失败经过、敌我态势和下一步行动放在一起重新判断。",
        "reflection": "当既有方案不断受挫，独立判断应当建立在什么基础上？",
        "source": {"title": "遵义1935：早到的春天", "organization": "中华人民共和国国防部", "url": "https://www.mod.gov.cn/gfbw/gfjy_index/js_214151/16364674.html", "excerpt": "1935年1月15日至17日，中共中央政治局在遵义召开扩大会议。"},
    },
]


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _spread(book: dict, node_key: str, index: int, spread_type: str, narration: str, scene: dict,
            source_refs: list[dict] | None = None, image_url: str | None = None, scene_number: int = 1) -> dict:
    positions = ["center", "45% center", "65% center", "35% center", "55% center"]
    image_url = image_url or f"/static/images/immersive/{book['id']}-{scene_number:02d}.webp"
    timeline = EVENT_TIMELINES[book["id"]]
    event_index = min(len(timeline) - 1, max(0, scene.get("timeline_index", min(4, index // 4))))
    event = timeline[event_index]
    return {
        "id": f"{book['id']}-{node_key}", "order_index": index, "spread_type": spread_type,
        "layout": "archive" if spread_type == "archive" else "cinematic",
        "image_url": image_url, "thumbnail_url": image_url, "audio_url": "", "narration": narration,
        "scene": {
            "position": positions[index % len(positions)], "scale": 1 + (index % 3) * 0.04,
            "reconstruction": True, "event": event, "timeline": timeline,
            "timeline_index": event_index, **scene,
        },
        "sources": source_refs or [],
    }


def _branching_spreads(book: dict, module: str, description: str) -> tuple[list[dict], dict]:
    hotspots = [
        {"id": f"clue-{i + 1}", "x": CLUE_POSITIONS[book["id"]][i][0], "y": CLUE_POSITIONS[book["id"]][i][1],
         "title": item[0], "content": item[1]}
        for i, item in enumerate(SCENE_CLUES[book["id"]])
    ]
    source = book["source"]
    decisions = BRANCH_STORIES[book["id"]]
    stages = ("route", "evidence", "judgment")
    continuation = {"route": "evidence", "evidence": "dialogue", "judgment": "outcome"}
    spreads: list[dict] = []
    graph_nodes: dict[str, dict] = {}

    def add(node_key, spread_type, narration, scene, scene_number=1, refs=None, image=None, next_key=None):
        spreads.append(_spread(book, node_key, len(spreads), spread_type, narration, scene, refs, image, scene_number))
        graph_nodes[f"{book['id']}-{node_key}"] = {"next": f"{book['id']}-{next_key}" if next_key else None}

    label = f"党史现场纪事 · 卷{book['source_id']}" if module == "history" else f"红色山河研学图志 · 第{book['source_id']}站"
    add("cover", "cover", "", {"eyebrow": label, "title": book["title"], "caption": book["subtitle"], "cta": "推开书页" if module == "history" else "展开行装"}, 1, next_key="arrival")
    add("arrival", "cinematic", book["arrival"], {"eyebrow": "抵达现场" if module == "history" else "当代抵达", "title": "先辨认时间与地点", "caption": book["era"], "particles": "mist" if module == "tour" else "dust", "contemporary": module == "tour"}, 1, next_key="route-clue")
    route_hotspot = [{"id": "route-clue", "x": 54, "y": 51, "title": hotspots[0]["title"], "content": hotspots[0]["content"]}]
    add("route-clue", "exploration", "先不要急着前进。辨认现场留下的方向线索，再决定从哪里进入历史。", {"eyebrow": "方向线索", "title": "先找到第一枚路标", "caption": "点击光点，路线选择才会解锁", "hotspots": route_hotspot}, 2, next_key="decision-route")

    for stage_index, stage in enumerate(stages):
        decision = decisions[stage_index]
        decision_key = f"decision-{stage}"
        public_options = []
        option_graph = {}
        wrong_index = 0
        for option_index, option in enumerate(decision["options"], 1):
            option_id = f"{stage}-option-{option_index}"
            public_options.append({"id": option_id, "label": option["label"]})
            if option["correct"]:
                target_key = continuation[stage]
            else:
                wrong_index += 1
                target_key = f"detour-{stage}-{wrong_index}"
                image = f"/static/images/immersive/{book['id']}-detour-{stage}-{wrong_index}.webp"
                add(target_key, "detour", option["body"], {
                    "eyebrow": "路线偏离", "title": option["title"], "caption": "这里的证据无法继续闭合",
                    "detour_body": option["body"], "return_label": "回到岔路口",
                }, 2 + stage_index, [source], image=image, next_key=decision_key)
            option_graph[option_id] = {
                "target": f"{book['id']}-{target_key}", "correct": option["correct"],
                "feedback": option.get("feedback", option.get("body", "")),
            }
        add(decision_key, "decision", decision["prompt"], {
            "eyebrow": ("路线判断", "证据判断", "行动判断")[stage_index],
            "title": decision["prompt"], "caption": "依据已经发现的线索作出选择", "options": public_options,
            "milestone": stage, "required_clues": decision["required_clues"],
        }, 2 + stage_index, [source])
        graph_nodes[f"{book['id']}-{decision_key}"].update({
            "decision": True, "required_clues": decision["required_clues"], "hints": decision["hints"],
            "options": option_graph,
        })
        if stage == "route":
            add("evidence", "exploration", book["explore"], {"eyebrow": "现场寻证", "title": "让物证彼此印证", "caption": "至少发现两处证据再继续", "hotspots": hotspots}, 3, next_key="decision-evidence")
        elif stage == "evidence":
            add("dialogue", "dialogue", book["person"], {"eyebrow": "人物行动", "title": "他们怎样身处其中", "caption": "行动必须放回具体时代条件"}, 4, next_key="decision-judgment")

    outcome = book.get("outcome") or source["excerpt"]
    add("outcome", "cinematic", outcome, {"eyebrow": "结果展开", "title": "正确证据链汇入历史进程", "caption": description}, 5, [source], next_key="archive")
    add("archive", "archive", source["excerpt"], {"eyebrow": "史料插页", "title": source["title"], "caption": source["organization"], "archive_excerpt": source["excerpt"]}, 6, [source], next_key="reflection" if module == "tour" else "ending")
    if module == "tour":
        add("reflection", "reflection", "用三句话完成记录：我看见了什么？它说明了什么？我还想继续了解什么？", {"eyebrow": "研学手记", "title": "把路线与证据写成判断", "caption": "写满 20 字即可保存", "prompt": book["reflection"], "note_placeholder": "我看见了……\n这说明……\n我还想了解……"}, 6, [source], next_key="ending")
    add("ending", "ending", book["reflection"], {"eyebrow": "余韵与归档" if module == "history" else "行程归档", "title": "把正确路线收入记忆" if module == "history" else "让观察成为一份答卷", "caption": "三个判断已经形成完整证据链", "prompt": book["reflection"], "cta": "完成本卷" if module == "history" else "生成报告并点亮印章"}, 6, [source])

    graph = {
        "version": 5,
        "start": f"{book['id']}-cover",
        "ending": f"{book['id']}-ending",
        "required_decisions": [f"{book['id']}-decision-{stage}" for stage in stages],
        "milestones": [
            {"id": f"{book['id']}-decision-route", "key": "route", "label": "路线"},
            {"id": f"{book['id']}-decision-evidence", "key": "evidence", "label": "证据"},
            {"id": f"{book['id']}-decision-judgment", "key": "judgment", "label": "判断"},
        ],
        "nodes": graph_nodes,
    }
    return spreads, graph


def _upsert_book(db: Session, config: dict, module: str, spreads: list[dict], graph: dict) -> None:
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
    book.version = 5
    book.status = "published"
    book.duration_estimate = 16 if module == "history" else 18
    book.order_index = int(config["source_id"]) - 1
    book.graph_json = _json(graph)
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
    valid_ids = [item["id"] for item in spreads]
    db.execute(delete(ImmersiveSpread).where(ImmersiveSpread.book_id == book.id, ImmersiveSpread.id.notin_(valid_ids)))


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

    for progress in db.scalars(select(ImmersiveProgress)).all():
        book = db.get(ImmersiveBook, progress.book_id)
        if not book or book.version < 5:
            continue
        ending = f"{book.id}-ending"
        start = f"{book.id}-cover"
        if progress.completed:
            progress.current_spread_id = ending
            progress.route_state_json = _json({"current": ending, "visited": [ending], "unlocked": [ending], "completed_legacy": True})
        elif progress.flow_version < 5:
            progress.current_spread = 0
            progress.current_spread_id = start
            progress.route_state_json = _json({})
        progress.flow_version = 5


def seed_immersive(db: Session) -> None:
    for config in HISTORY_BOOKS:
        scenario = db.get(HistoryScenario, config["source_id"])
        if scenario:
            spreads, graph = _branching_spreads(config, "history", scenario.description or "")
            _upsert_book(db, config, "history", spreads, graph)
    for config in TOUR_BOOKS:
        site = db.get(TourSite, config["source_id"])
        if site:
            spreads, graph = _branching_spreads(config, "tour", site.description or "")
            _upsert_book(db, config, "tour", spreads, graph)
    db.flush()
    _migrate_progress(db)

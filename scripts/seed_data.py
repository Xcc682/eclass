"""数据库种子数据 - 初始化场景和知识文档"""
import json

SEED_SCENARIOS = [
    {
        "title": "入党积极分子谈话",
        "description": "模拟党组织与入党积极分子的首次正式谈话",
        "difficulty": "beginner",
        "estimated_duration": 15,
        "ai_role_name": "张老师",
        "ai_role_title": "院党委组织委员",
        "questions": [
            "同学你好，请先做个自我介绍，谈谈你的基本情况。",
            "你为什么想加入中国共产党？能谈谈你的入党动机吗？",
            "你对中国共产党的性质是如何理解的？",
            "你觉得作为一名党员，最重要的品质是什么？",
            "你在日常生活和学习中是如何向党组织靠拢的？"
        ]
    },
    {
        "title": "预备党员接收谈话",
        "description": "发展对象转为预备党员前的组织谈话",
        "difficulty": "intermediate",
        "estimated_duration": 20,
        "ai_role_name": "李书记",
        "ai_role_title": "院党委副书记",
        "questions": [
            "请谈谈你对习近平新时代中国特色社会主义思想的理解。",
            "你认为自己在思想上有哪些需要改进的地方？",
            "如果党组织交给你一项艰巨的任务，你会怎么处理？",
            "你如何理解'四个意识'、'四个自信'、'两个维护'？"
        ]
    }
]

SEED_HISTORY = [
    {
        "title": "嘉兴南湖·中共一大",
        "era": "new_demo",
        "year_from": 1921,
        "year_to": 1921,
        "description": "中国共产党诞生，红船精神永放光芒",
        "key_events": [
            {"title": "中共一大召开", "description": "1921年7月23日开幕", "year": 1921}
        ],
        "duration_estimate": 15
    }
]

if __name__ == "__main__":
    print("种子数据准备完成")
    print(f"谈话场景: {len(SEED_SCENARIOS)} 个")
    print(f"历史场景: {len(SEED_HISTORY)} 个")

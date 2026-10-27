from datetime import datetime


def render_report(plan: dict, roadmap: dict, resources: list[dict], evaluation: dict) -> str:
    resource_map = {item["id"]: item for item in resources}
    dimensions = "\n".join(
        f"- **{item['name']}**：{item['score']}/20，{item['comment']}" for item in evaluation["dimensions"]
    )
    stage_sections = []
    for index, stage in enumerate(roadmap["stages"], start=1):
        links = " ".join(f"[{resource_map[source_id]['id']}]" for source_id in stage["resource_ids"])
        topics = "、".join(stage["topics"])
        stage_sections.append(
            f"""### {index}. {stage["name"]}（第 {stage["weeks"]} 周）

- 重点：{stage["focus"]}
- 知识点：{topics}
- 练习：{stage["practice"]}
- 阶段交付：{stage["deliverable"]}
- 配套资料：{links}"""
        )
    source_lines = "\n".join(
        f"- [{item['id']}] [{item['title']}]({item['url']}) — {item['provider']}，{item['resource_type']}。{item['reason']}"
        for item in resources
    )
    return f"""# {roadmap["title"]}

> 学习目标：{plan["goal"]}  
> 学习节奏：每周 {plan["weekly_hours"]} 小时，共 {plan["duration_weeks"]} 周  
> 生成时间：{datetime.now().astimezone():%Y-%m-%d %H:%M}

## 路线概览

{roadmap["overview"]}

先修要求：{"、".join(roadmap["prerequisites"]) or "无"}

{chr(10).join(stage_sections)}

## 最终项目

{roadmap["final_project"]}

学习结束后应能够：

{chr(10).join(f"- {item}" for item in roadmap["learning_outcomes"])}

## 计划可用性评测

**总分：{evaluation["total_score"]}/100 · {"建议执行" if evaluation["verdict"] == "recommended" else "建议修订"}**

{evaluation["summary"]}

{dimensions}

### 风险与建议

{chr(10).join(f"- {item}" for item in evaluation["issues"] + evaluation["recommendations"]) or "- 未发现明显风险"}

## 参考资料

{source_lines}

---

资料链接来自 Tavily 搜索结果。学习前请再次检查页面可访问性与版本信息。
"""

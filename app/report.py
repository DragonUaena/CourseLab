from datetime import datetime


def _bullets(items: list[str], empty: str = "无") -> str:
    cleaned = [item.strip() for item in items if isinstance(item, str) and item.strip()]
    return "\n".join(f"- {item}" for item in cleaned) if cleaned else f"- {empty}"


def _format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "未记录"
    minutes, remaining = divmod(max(0, round(seconds)), 60)
    return f"{minutes} 分 {remaining} 秒" if minutes else f"{remaining} 秒"


def _source_evidence(stage: dict, resource_map: dict[str, dict]) -> str:
    lines = []
    for source_id in stage.get("resource_ids", []):
        resource = resource_map.get(source_id)
        if not resource:
            continue
        freshness = (
            f"发布于 {resource['published_date']}"
            if resource.get("published_date")
            else f"检索日期 {resource.get('retrieved_at', '未记录')}"
        )
        lines.append(
            f"- **[{source_id}]** [{resource.get('title', source_id)}]({resource.get('url', '')})"
            f"（相关度 {resource.get('relevance', '未评分')}/100，{freshness}）："
            f"{resource.get('reason', '未提供用途说明')}"
        )
    return "\n".join(lines) if lines else "- 暂无可用来源"


def _schedule_table(stage: dict) -> str:
    schedule = stage.get("schedule", [])
    if not schedule:
        return "尚未提供分步安排。"
    rows = [f"| {item.get('period', '')} | {item.get('focus', '')} | {item.get('output', '')} |" for item in schedule]
    return "\n".join(["| 时间 | 学习重点 | 可验证产出 |", "| --- | --- | --- |", *rows])


def render_report(
    plan: dict,
    roadmap: dict,
    resources: list[dict],
    evaluation: dict,
    generation_seconds: float | None = None,
    token_usage: dict | None = None,
) -> str:
    resource_map = {item["id"]: item for item in resources}
    dimensions = "\n".join(
        f"- **{item['name']}**：{item['score']}/20，{item['comment']}" for item in evaluation["dimensions"]
    )
    stage_sections = []
    for index, stage in enumerate(roadmap.get("stages", []), start=1):
        stage_sections.append(
            f"""### {index}. {stage.get("name", "未命名阶段")}（{stage.get("weeks", 0)} 周）

**预计投入：** {stage.get("weeks", 0) * plan["weekly_hours"]} 小时

**阶段重点：** {stage.get("focus", "")}

#### 学习目标

{_bullets(stage.get("objectives", []))}

#### 知识点

{", ".join(stage.get("topics", [])) or "未提供"}

#### 分步执行

{_schedule_table(stage)}

**实践任务：** {stage.get("practice", "")}

**阶段交付：** {stage.get("deliverable", "")}

#### 验收标准

{_bullets(stage.get("acceptance_criteria", []))}

#### 本阶段依据

{_source_evidence(stage, resource_map)}"""
        )

    source_lines = "\n".join(
        f"- **[{item['id']}]** [{item['title']}]({item['url']}) — {item['provider']}，"
        f"{item['resource_type']}，相关度 {item.get('relevance', '未评分')}/100，"
        f"难度 {item.get('difficulty', '未标注')}。{item['reason']}。"
        f"{'发布于 ' + item['published_date'] if item.get('published_date') else '未提供发布日期'}；"
        f"检索于 {item.get('retrieved_at', '未记录')}。"
        for item in resources
    )
    usage = token_usage or {}
    usage_line = (
        f"模型输入 {usage.get('prompt_tokens', 0):,} tokens，"
        f"输出 {usage.get('completion_tokens', 0):,} tokens，"
        f"合计 {usage.get('total_tokens', 0):,} tokens。"
        if usage.get("total_tokens")
        else "模型用量未记录。"
    )
    return f"""# {roadmap["title"]}

> 学习目标：{plan["goal"]}
>
> 学习者基础：{plan["level"]} · 资料语言：{plan["language"]}
>
> 学习节奏：每周 {plan["weekly_hours"]} 小时，共 {plan["duration_weeks"]} 周
>
> 生成耗时：{_format_duration(generation_seconds)}
>
> {usage_line}
>
> 报告生成时间：{datetime.now().astimezone():%Y-%m-%d %H:%M}

## 路线概览

{roadmap["overview"]}

### 执行策略

{_bullets(roadmap.get("study_strategy", []))}

### 开始前准备

{_bullets(roadmap.get("prerequisites", []))}

## 分阶段执行计划

{chr(10).join(stage_sections)}

## 综合项目

{roadmap["final_project"]}

### 项目要求

{_bullets(roadmap.get("project_requirements", []))}

### 完成标准

{_bullets(roadmap.get("learning_outcomes", []))}

## 计划可用性评测

**总分：{evaluation["total_score"]}/100 · {"建议执行" if evaluation["verdict"] == "recommended" else "建议修订"}**

{evaluation["summary"]}

{dimensions}

### 风险与建议

{_bullets(evaluation.get("issues", []) + evaluation.get("recommendations", []), "未发现明显风险")}

## 参考资料

{source_lines}

---

资料来自本次 Tavily 实时检索。未提供发布日期的来源不代表它是新资料；执行前应再次核对官方版本、链接可用性和安装命令。
"""

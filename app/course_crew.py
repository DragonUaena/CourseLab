import json
from dataclasses import dataclass
from typing import Any

from crewai import LLM, Agent, Crew, Process, Task
from pydantic import BaseModel, Field

from app.credentials import RuntimeCredentials
from app.schemas import EvaluationDimension, PlanEvaluation, Roadmap


class CuratedSource(BaseModel):
    source_id: str
    relevance: int = Field(ge=0, le=100)
    use_for: str
    difficulty: str


class CurationResult(BaseModel):
    summary: str
    sources: list[CuratedSource]


@dataclass(frozen=True)
class CrewResult:
    roadmap: dict
    resources: list[dict]
    evaluation: dict


class CourseCrew:
    def __init__(self, credentials: RuntimeCredentials) -> None:
        self.llm = LLM(
            model=credentials.llm_model,
            api_key=credentials.llm_api_key,
            base_url=credentials.llm_base_url or None,
            temperature=0.2,
        )

    def generate(self, profile: dict, sources: list[dict]) -> CrewResult:
        source_text = json.dumps(sources, ensure_ascii=False, indent=2)
        profile_text = json.dumps(profile, ensure_ascii=False, indent=2)
        agent_defaults = {
            "llm": self.llm,
            "verbose": False,
            "allow_delegation": False,
            "max_iter": 4,
        }
        curator = Agent(
            role="学习资料策展人",
            goal="只从提供的 Tavily 搜索资料中筛选真正相关的来源，拒绝重复和低质量页面。",
            backstory="你为大学本科生设计课程，擅长分辨官方文档、系统课程、视频和可操作项目。",
            **agent_defaults,
        )
        planner = Agent(
            role="课程路线架构师",
            goal="把资料和学习目标组织成工作量可信、顺序合理、可执行的分阶段路线。",
            backstory="你遵循从概念到练习再到交付物的学习设计方法，并严格控制周数和工作量。",
            **agent_defaults,
        )
        reviewer = Agent(
            role="学习计划审查员",
            goal="独立评估计划是否匹配学习者、资料是否支撑路线、工作量和产出是否可行。",
            backstory="你会指出空泛、不可执行或引用不足的学习计划，并给出有分数依据的审查意见。",
            **agent_defaults,
        )
        curation_task = Task(
            description=(
                f"学习者画像：\n{profile_text}\n\nTavily 原始资料：\n{source_text}\n\n"
                "筛选 5 到 10 个最有价值的来源。source_id 必须来自原始资料。"
                "relevance 为 0-100，use_for 说明它适合哪个学习环节，difficulty 描述难度。"
            ),
            expected_output="符合 CurationResult 的 JSON，只能引用已有 source_id。",
            output_pydantic=CurationResult,
            agent=curator,
        )
        planning_task = Task(
            description=(
                f"学习者画像：\n{profile_text}\n\nTavily 资料：\n{source_text}\n\n"
                f"设计一份恰好 {profile['duration_weeks']} 周、每周 {profile['weekly_hours']} 小时的路线。"
                "阶段必须覆盖先修、核心、实践和综合交付；每个阶段 resource_ids 使用策展结果中的合法 ID。"
                "不要编造资料 URL，不要安排无法在给定时间内完成的内容。"
            ),
            expected_output="符合 Roadmap JSON schema 的中文学习路线，阶段周数总和必须等于总周数。",
            output_pydantic=Roadmap,
            agent=planner,
            context=[curation_task],
        )
        review_task = Task(
            description=(
                f"学习者画像：\n{profile_text}\n\n可用资料：\n{source_text}\n\n"
                "对前一阶段生成的路线做独立审查，从目标匹配、顺序、工作量、资料质量和可执行性五个维度"
                "各给 0-20 分。总分 0-100；低于 75 分时 verdict 必须是 needs_revision。"
                "问题必须具体，建议必须能在当前周数内实施。"
            ),
            expected_output="符合 PlanEvaluation JSON schema 的审查报告。",
            output_pydantic=PlanEvaluation,
            agent=reviewer,
            context=[curation_task, planning_task],
        )
        result = Crew(
            name="CourseLab learning route crew",
            agents=[curator, planner, reviewer],
            tasks=[curation_task, planning_task, review_task],
            process=Process.sequential,
            verbose=False,
            cache=False,
        ).kickoff()
        curation: CurationResult = result.tasks_output[0].pydantic
        roadmap: Roadmap = result.tasks_output[1].pydantic
        evaluation: PlanEvaluation = result.tasks_output[2].pydantic
        selected = self._selected_resources(curation, sources)
        normalized = self._normalize_roadmap(roadmap, profile["duration_weeks"], [item["id"] for item in selected])
        return CrewResult(
            roadmap=normalized,
            resources=selected,
            evaluation=evaluation.model_dump(),
        )

    @staticmethod
    def _selected_resources(curation: CurationResult, sources: list[dict]) -> list[dict]:
        source_map = {source["id"]: source for source in sources}
        resources: list[dict] = []
        for item in sorted(curation.sources, key=lambda source: source.relevance, reverse=True):
            if item.source_id not in source_map:
                continue
            resources.append(
                {
                    **source_map[item.source_id],
                    "reason": item.use_for,
                    "difficulty": item.difficulty,
                    "relevance": item.relevance,
                }
            )
        if not resources:
            raise ValueError("资料筛选 Agent 没有返回合法引用")
        return resources

    @staticmethod
    def _normalize_roadmap(roadmap: Roadmap, total_weeks: int, resource_ids: list[str]) -> dict:
        stages = [stage.model_copy(deep=True) for stage in roadmap.stages]
        current = sum(stage.weeks for stage in stages)
        if current < total_weeks:
            stages[-1].weeks += total_weeks - current
        for stage in reversed(stages):
            if current <= total_weeks:
                break
            reducible = min(stage.weeks - 1, current - total_weeks)
            stage.weeks -= reducible
            current -= reducible
        if sum(stage.weeks for stage in stages) != total_weeks:
            raise ValueError("生成路线的阶段周数无法匹配学习周期")
        valid = set(resource_ids)
        for index, stage in enumerate(stages):
            cleaned = [source_id for source_id in stage.resource_ids if source_id in valid]
            stage.resource_ids = cleaned or [resource_ids[index % len(resource_ids)]]
        result = roadmap.model_copy(update={"stages": stages})
        return result.model_dump()

    @staticmethod
    def blend_evaluation(evaluation: dict, audit: dict) -> dict:
        merged_score = round(evaluation["total_score"] * 0.7 + audit["score"] * 0.3)
        dimensions = evaluation["dimensions"]
        if not dimensions:
            dimensions = [
                EvaluationDimension(name=name, score=12, comment="Agent 未提供该维度说明").model_dump()
                for name in ("目标匹配", "学习顺序", "工作量", "资料质量", "可执行性")
            ]
        return {
            **evaluation,
            "total_score": merged_score,
            "verdict": "recommended" if merged_score >= 75 else "needs_revision",
            "dimensions": dimensions,
            "program_checks": audit,
        }


def audit_plan(profile: dict[str, Any], roadmap: dict, resources: list[dict]) -> dict:
    stages = roadmap.get("stages", [])
    issues: list[str] = []
    checks: list[dict[str, Any]] = []
    if not stages:
        issues.append("路线没有阶段")
    if len(roadmap.get("learning_outcomes", [])) < 3:
        issues.append("学习产出少于三项")
    if not roadmap.get("final_project"):
        issues.append("缺少综合项目")
    if sum(stage.get("weeks", 0) for stage in stages) != profile["duration_weeks"]:
        issues.append("阶段周数与总周期不一致")
    covered = sum(bool(stage.get("resource_ids")) for stage in stages)
    coverage = round(covered / len(stages) * 100) if stages else 0
    if coverage < 100:
        issues.append("部分阶段没有配套资料")
    if len(resources) < 3:
        issues.append("有效资料少于三个")
    checks.extend(
        [
            {"name": "阶段资料覆盖", "passed": coverage == 100, "detail": f"{coverage}%"},
            {
                "name": "周期与工作量",
                "passed": sum(stage.get("weeks", 0) for stage in stages) == profile["duration_weeks"],
                "detail": f"{profile['weekly_hours']} 小时/周 × {profile['duration_weeks']} 周",
            },
            {"name": "学习产出", "passed": len(roadmap.get("learning_outcomes", [])) >= 3, "detail": "至少三项"},
            {"name": "资料引用", "passed": len(resources) >= 3, "detail": f"{len(resources)} 个有效来源"},
        ]
    )
    return {
        "score": max(20, 100 - len(issues) * 12),
        "coverage": coverage,
        "checks": checks,
        "issues": issues,
    }

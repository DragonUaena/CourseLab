import warnings

import pytest
from crewai import Task

from app.course_crew import (
    REVIEW_DIMENSIONS,
    CourseCrew,
    CuratedSource,
    CurationResult,
    GenerationCancelled,
    _task_cancel_check,
    audit_plan,
    model_uses_reasoning_tokens,
    raise_if_cancelled_at_task_boundary,
)
from app.credentials import RuntimeCredentials
from app.demo_data import DEMO_EVALUATION, DEMO_PROFILE, DEMO_RESOURCES, DEMO_ROADMAP
from app.research import _language_code
from app.schemas import Roadmap


def test_week_budget_and_resource_references_are_normalized():
    roadmap = Roadmap.model_validate(DEMO_ROADMAP)
    roadmap.stages[-1].weeks = 4
    normalized = CourseCrew._normalize_roadmap(roadmap, total_weeks=6, resource_ids=["S1", "S2"])
    assert sum(stage["weeks"] for stage in normalized["stages"]) == 6
    assert all(set(stage["resource_ids"]) <= {"S1", "S2"} for stage in normalized["stages"])


def test_audit_flags_missing_resources_and_wrong_week_count():
    broken = {**DEMO_ROADMAP, "stages": [{**DEMO_ROADMAP["stages"][0], "weeks": 1, "resource_ids": []}]}
    audit = audit_plan(DEMO_PROFILE, broken, DEMO_RESOURCES[:1])
    assert audit["score"] < 100
    assert audit["coverage"] == 0
    assert "部分阶段没有配套资料" in audit["issues"]
    assert "阶段周数与总周期不一致" in audit["issues"]


def test_audit_flags_incomplete_stage_content():
    broken = {
        **DEMO_ROADMAP,
        "stages": [{**DEMO_ROADMAP["stages"][0], "practice": "", "resource_ids": ["missing"]}],
    }
    audit = audit_plan(DEMO_PROFILE, broken, DEMO_RESOURCES[:3])
    assert "部分阶段缺少目标、计划、知识点、练习、验收标准或交付物" in audit["issues"]
    assert "部分阶段引用了不存在的资料" in audit["issues"]
    assert audit["coverage"] == 0


def test_resource_curation_deduplicates_and_caps_sources():
    sources = [{**DEMO_RESOURCES[0], "id": f"S{index}"} for index in range(1, 13)]
    curation = CurationResult(
        summary="test",
        sources=[
            CuratedSource(source_id=f"S{index}", relevance=100 - index, use_for="学习", difficulty="入门")
            for index in range(1, 13)
        ]
        + [CuratedSource(source_id="S1", relevance=50, use_for="复习", difficulty="入门")],
    )
    selected = CourseCrew._selected_resources(curation, sources)
    assert len(selected) == 10
    assert len({item["id"] for item in selected}) == 10


def test_resource_curation_requires_three_valid_sources():
    curation = CurationResult(
        summary="test",
        sources=[
            CuratedSource(source_id="S1", relevance=99, use_for="学习", difficulty="入门"),
            CuratedSource(source_id="S1", relevance=98, use_for="复习", difficulty="入门"),
            CuratedSource(source_id="missing", relevance=97, use_for="学习", difficulty="入门"),
        ],
    )
    with pytest.raises(ValueError, match="至少需要 3 个"):
        CourseCrew._selected_resources(curation, DEMO_RESOURCES[:3])


def test_evaluation_dimensions_are_complete_and_deduplicated():
    evaluation = {
        **DEMO_EVALUATION,
        "dimensions": [
            {"name": "目标匹配", "score": 18, "comment": "第一次"},
            {"name": "目标匹配", "score": 16, "comment": "第二次"},
            {"name": "学习顺序", "score": 19, "comment": "顺序合理"},
            {"name": "未知维度", "score": 20, "comment": "应被忽略"},
        ],
    }
    merged = CourseCrew.blend_evaluation(evaluation, {"score": 90})
    assert [item["name"] for item in merged["dimensions"]] == list(REVIEW_DIMENSIONS)
    target_match = merged["dimensions"][0]
    assert target_match["score"] == 17
    assert target_match["comment"] == "第一次；第二次"
    assert all(item["comment"] for item in merged["dimensions"])


def test_prompt_sources_are_compacted_for_token_budget():
    crew = CourseCrew(
        RuntimeCredentials(
            tavily_api_key="",
            llm_api_key="test",
            llm_model="openai/gpt-4o-mini",
            llm_base_url="",
        ),
        prompt_source_chars=50,
    )
    compact = crew._compact_sources([{**DEMO_RESOURCES[0], "snippet": "x" * 1000}])
    assert compact[0]["snippet"] == "x" * 50
    assert compact[0]["id"] == "S1"
    assert "reason" not in compact[0]


def test_crew_task_boundary_honors_cancellation():
    context_token = _task_cancel_check.set(lambda: True)
    try:
        with pytest.raises(GenerationCancelled):
            raise_if_cancelled_at_task_boundary(None)
    finally:
        _task_cancel_check.reset(context_token)


def test_crew_callback_is_module_level_and_serializable():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        Task(
            description="test",
            expected_output="test",
            callback=raise_if_cancelled_at_task_boundary,
        )
    assert not any("method callbacks cannot be serialized" in str(item.message) for item in caught)


def test_reasoning_models_receive_low_effort_and_larger_output_budget(monkeypatch: pytest.MonkeyPatch):
    class FakeLLM:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr("app.course_crew.LLM", FakeLLM)
    crew = CourseCrew(
        RuntimeCredentials(
            tavily_api_key="",
            llm_api_key="test",
            llm_model="openai/deepseek-v4.1-flash-1017",
            llm_base_url="https://example.com/v1",
        ),
        max_tokens=12000,
        reasoning_effort="low",
    )
    assert model_uses_reasoning_tokens("openai/deepseek-v4.1-flash-1017") is True
    assert model_uses_reasoning_tokens("openai/gpt-4o-mini") is False
    assert crew.llm.kwargs["max_tokens"] == 12000
    assert crew.llm.kwargs["reasoning_effort"] == "low"


def test_tavily_language_aliases_are_normalized():
    assert _language_code("中文") == "zh-cn"
    assert _language_code("english") == "en"
    assert _language_code("中英混合") is None

from app.course_crew import CourseCrew, audit_plan
from app.demo_data import DEMO_PROFILE, DEMO_RESOURCES, DEMO_ROADMAP
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

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import desc, select

from app.auth import CurrentUser, DbSession, create_access_token, hash_password, verify_password
from app.credentials import InvalidCredentialsError, MissingCredentialsError, resolve_credentials, stored_credentials
from app.demo_data import get_demo
from app.models import LearningPlan, User, UserCredential, utcnow
from app.schemas import (
    CredentialsStatus,
    CredentialsUpdate,
    LoginRequest,
    PlanCreate,
    PlanResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "CourseLab"}


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, session: DbSession):
    email = payload.email.lower()
    if session.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="这个邮箱已经注册")
    user = User(
        email=email,
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    session.commit()
    return TokenResponse(access_token=create_access_token(user.id, request), user=UserResponse.model_validate(user))


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, session: DbSession):
    user = session.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码不正确")
    return TokenResponse(access_token=create_access_token(user.id, request), user=UserResponse.model_validate(user))


@router.get("/auth/me", response_model=UserResponse)
def me(user: CurrentUser):
    return user


@router.get("/settings/credentials", response_model=CredentialsStatus)
def credential_status(user: CurrentUser, request: Request, session: DbSession):
    stored = stored_credentials(session, user.id, request.app.state.cipher)
    settings = request.app.state.settings
    return CredentialsStatus(
        configured=bool(
            (stored.get("tavily_api_key") or settings.tavily_api_key)
            and (stored.get("llm_api_key") or settings.openai_api_key)
        ),
        tavily_configured=bool(stored.get("tavily_api_key") or settings.tavily_api_key),
        llm_configured=bool(stored.get("llm_api_key") or settings.openai_api_key),
        llm_model=stored.get("llm_model") or settings.llm_model,
        llm_base_url=stored.get("llm_base_url") or settings.openai_api_base,
    )


@router.put("/settings/credentials", response_model=CredentialsStatus)
def save_credentials(payload: CredentialsUpdate, user: CurrentUser, request: Request, session: DbSession):
    cipher = request.app.state.cipher
    current = stored_credentials(session, user.id, cipher)
    if payload.clear_tavily_api_key:
        current.pop("tavily_api_key", None)
    elif payload.tavily_api_key:
        current["tavily_api_key"] = payload.tavily_api_key.strip()
    if payload.clear_llm_api_key:
        current.pop("llm_api_key", None)
    elif payload.llm_api_key:
        current["llm_api_key"] = payload.llm_api_key.strip()
    current["llm_model"] = payload.llm_model.strip()
    current["llm_base_url"] = payload.llm_base_url.strip()
    record = session.scalar(select(UserCredential).where(UserCredential.user_id == user.id))
    if record is None:
        session.add(UserCredential(user_id=user.id, encrypted_payload=cipher.encrypt(current)))
    else:
        record.encrypted_payload = cipher.encrypt(current)
    session.commit()
    return credential_status(user, request, session)


@router.post("/plans", response_model=PlanResponse, status_code=status.HTTP_202_ACCEPTED)
def create_plan(payload: PlanCreate, user: CurrentUser, request: Request, session: DbSession):
    try:
        resolve_credentials(session, request.app.state.settings, request.app.state.cipher, user.id)
    except (InvalidCredentialsError, MissingCredentialsError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    plan = LearningPlan(user_id=user.id, **payload.model_dump())
    session.add(plan)
    session.commit()
    request.app.state.worker.enqueue(plan.id)
    return plan


@router.get("/plans", response_model=list[PlanResponse])
def list_plans(user: CurrentUser, session: DbSession):
    return list(
        session.scalars(
            select(LearningPlan).where(LearningPlan.user_id == user.id).order_by(desc(LearningPlan.created_at))
        )
    )


@router.get("/plans/{plan_id}", response_model=PlanResponse)
def get_plan(plan_id: str, user: CurrentUser, session: DbSession):
    plan = session.scalar(select(LearningPlan).where(LearningPlan.id == plan_id, LearningPlan.user_id == user.id))
    if plan is None:
        raise HTTPException(status_code=404, detail="学习计划不存在")
    return plan


@router.post("/plans/{plan_id}/retry", response_model=PlanResponse, status_code=status.HTTP_202_ACCEPTED)
def retry_plan(plan_id: str, user: CurrentUser, request: Request, session: DbSession):
    plan = session.scalar(select(LearningPlan).where(LearningPlan.id == plan_id, LearningPlan.user_id == user.id))
    if plan is None:
        raise HTTPException(status_code=404, detail="学习计划不存在")
    if plan.status in {"queued", "running"}:
        raise HTTPException(status_code=409, detail="计划正在生成")
    plan.status = "queued"
    plan.stage = "等待生成"
    plan.progress = 0
    plan.error = None
    plan.roadmap = None
    plan.resources = None
    plan.evaluation = None
    plan.report_markdown = None
    plan.model_name = None
    plan.cost_usd = None
    plan.token_usage = None
    plan.started_at = None
    plan.completed_at = None
    session.commit()
    request.app.state.worker.enqueue(plan.id)
    return plan


@router.post("/plans/{plan_id}/stop", response_model=PlanResponse)
def stop_plan(plan_id: str, user: CurrentUser, session: DbSession):
    plan = session.scalar(select(LearningPlan).where(LearningPlan.id == plan_id, LearningPlan.user_id == user.id))
    if plan is None:
        raise HTTPException(status_code=404, detail="学习计划不存在")
    if plan.status not in {"queued", "running"}:
        raise HTTPException(status_code=409, detail="计划已经结束，无需停止")
    interrupted_stage = plan.stage
    plan.status = "cancelled"
    plan.stage = "已停止生成"
    plan.error = f"生成已由用户停止（停止于：{interrupted_stage}）"
    plan.completed_at = utcnow()
    session.commit()
    return plan


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(plan_id: str, user: CurrentUser, session: DbSession):
    plan = session.scalar(select(LearningPlan).where(LearningPlan.id == plan_id, LearningPlan.user_id == user.id))
    if plan is None:
        raise HTTPException(status_code=404, detail="学习计划不存在")
    if plan.status in {"queued", "running"}:
        raise HTTPException(status_code=409, detail="请先停止正在生成的计划")
    session.delete(plan)
    session.commit()


@router.get("/plans/{plan_id}/report", response_class=PlainTextResponse)
def plan_report(plan_id: str, user: CurrentUser, session: DbSession):
    plan = session.scalar(select(LearningPlan).where(LearningPlan.id == plan_id, LearningPlan.user_id == user.id))
    if plan is None or not plan.report_markdown:
        raise HTTPException(status_code=404, detail="报告尚未生成")
    return PlainTextResponse(
        plan.report_markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="courselab-{plan.id}.md"'},
    )


@router.get("/demo")
def demo():
    return get_demo()

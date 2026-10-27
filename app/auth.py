from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Database
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
password_hasher = PasswordHasher()


def get_session(request: Request):
    database: Database = request.app.state.database
    with database.sessions() as session:
        yield session


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def create_access_token(user_id: str, request: Request) -> str:
    settings = request.app.state.settings
    expires = datetime.now(UTC) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub": user_id, "exp": expires}, settings.secret_key, algorithm="HS256")


def get_current_user(
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_session)],
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="登录状态已失效，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, request.app.state.settings.secret_key, algorithms=["HS256"])
        user_id = payload.get("sub")
    except jwt.PyJWTError as exc:
        raise credentials_error from exc
    user = session.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_session)]

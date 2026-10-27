import base64
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import UserCredential


@dataclass(frozen=True)
class RuntimeCredentials:
    tavily_api_key: str
    llm_api_key: str
    llm_model: str
    llm_base_url: str


class MissingCredentialsError(RuntimeError):
    pass


class CredentialCipher:
    def __init__(self, configured_key: str, fallback_path: Path) -> None:
        if configured_key:
            raw_key = hashlib.sha256(configured_key.encode()).digest()
        else:
            fallback_path.parent.mkdir(parents=True, exist_ok=True)
            if not fallback_path.exists():
                fallback_path.write_bytes(Fernet.generate_key())
            raw_key = base64.urlsafe_b64decode(fallback_path.read_bytes())
            raw_key = hashlib.sha256(raw_key).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(raw_key))

    def encrypt(self, payload: dict[str, str]) -> str:
        return self._fernet.encrypt(json.dumps(payload, ensure_ascii=False).encode()).decode()

    def decrypt(self, token: str) -> dict[str, str]:
        return json.loads(self._fernet.decrypt(token.encode()))


def stored_credentials(session: Session, user_id: str, cipher: CredentialCipher) -> dict[str, str]:
    record = session.scalar(select(UserCredential).where(UserCredential.user_id == user_id))
    return cipher.decrypt(record.encrypted_payload) if record else {}


def resolve_credentials(
    session: Session,
    settings: Settings,
    cipher: CredentialCipher,
    user_id: str,
) -> RuntimeCredentials:
    stored = stored_credentials(session, user_id, cipher)
    values = RuntimeCredentials(
        tavily_api_key=stored.get("tavily_api_key", "") or settings.tavily_api_key,
        llm_api_key=stored.get("llm_api_key", "") or settings.openai_api_key,
        llm_model=stored.get("llm_model", "") or settings.llm_model,
        llm_base_url=stored.get("llm_base_url", "") or settings.openai_api_base,
    )
    missing = []
    if not values.tavily_api_key:
        missing.append("Tavily API Key")
    if not values.llm_api_key:
        missing.append("大模型 API Key")
    if missing:
        raise MissingCredentialsError(f"请先在设置中填写：{'、'.join(missing)}")
    return values

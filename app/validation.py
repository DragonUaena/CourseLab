from pydantic import AnyHttpUrl, TypeAdapter, ValidationError

_http_url_adapter = TypeAdapter(AnyHttpUrl)


def normalize_http_url(value: str, field_name: str = "URL") -> str:
    normalized = value.strip()
    if not normalized:
        return ""
    try:
        return str(_http_url_adapter.validate_python(normalized)).rstrip("/")
    except ValidationError as exc:
        raise ValueError(f"{field_name}必须是有效的 HTTP 或 HTTPS 地址") from exc

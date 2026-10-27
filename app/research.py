from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from tavily import TavilyClient


def _resource_type(title: str, url: str) -> str:
    haystack = f"{title} {url}".lower()
    if any(part in haystack for part in ("youtube", "bilibili", "video", "视频")):
        return "视频"
    if "github" in haystack:
        return "代码库"
    if any(part in haystack for part in ("docs", "documentation", "官方")):
        return "文档"
    if any(part in haystack for part in ("course", "tutorial", "教程", "课程")):
        return "课程"
    return "文章"


def _language_code(language: str) -> str | None:
    normalized = language.strip().lower().replace("_", "-")
    aliases = {
        "中文": "zh-cn",
        "汉语": "zh-cn",
        "简体中文": "zh-cn",
        "chinese": "zh-cn",
        "zh": "zh-cn",
        "zh-cn": "zh-cn",
        "英文": "en",
        "英语": "en",
        "english": "en",
        "en": "en",
        "中英混合": None,
        "双语": None,
        "mixed": None,
    }
    return aliases.get(normalized, normalized)


def _search_one(client: TavilyClient, query: str, language: str) -> list[dict]:
    language_code = _language_code(language)
    parameters = {
        "query": query,
        "search_depth": "advanced",
        "max_results": 5,
        "include_answer": False,
        "include_raw_content": False,
        "include_favicon": True,
    }
    if language_code:
        parameters["language"] = language_code
    response = client.search(
        **parameters,
    )
    return response.get("results", [])


class TavilyResearcher:
    def __init__(self, api_key: str) -> None:
        self.client = TavilyClient(api_key=api_key)

    def search(self, topic: str, goal: str, language: str) -> list[dict]:
        queries = [
            f"{topic} 官方文档 official documentation",
            f"{topic} 入门教程 系统课程",
            f"{topic} 项目实战 hands-on project",
            f"{topic} {goal} learning path",
        ]
        with ThreadPoolExecutor(max_workers=4) as executor:
            batches = list(executor.map(lambda query: _search_one(self.client, query, language), queries))
        sources: list[dict] = []
        seen: set[str] = set()
        for result in (item for batch in batches for item in batch):
            url = result.get("url", "")
            if not url.startswith(("http://", "https://")) or url in seen:
                continue
            seen.add(url)
            title = result.get("title", urlparse(url).netloc)
            sources.append(
                {
                    "id": f"S{len(sources) + 1}",
                    "title": title[:240],
                    "url": url,
                    "snippet": result.get("content", "")[:1400],
                    "provider": urlparse(url).netloc,
                    "score": float(result.get("score", 0)),
                    "resource_type": _resource_type(title, url),
                }
            )
        if not sources:
            raise RuntimeError("Tavily 没有返回可用资料，请调整学习主题后重试")
        return sources[:16]

import logging
import os

import httpx

from deerflow.config import get_proxy_config

logger = logging.getLogger(__name__)

_api_key_warned = False


def _get_proxies() -> dict[str, str] | None:
    """Get proxy configuration for requests library.

    Returns:
        Dict with proxy URLs if configured, None otherwise.
    """
    proxy_config = get_proxy_config()
    if proxy_config and proxy_config.is_enabled():
        return proxy_config.get_proxies_dict()
    return None


class JinaClient:
    async def crawl(self, url: str, return_format: str = "html", timeout: int = 10) -> str:
        global _api_key_warned
        headers = {
            "Content-Type": "application/json",
            "X-Return-Format": return_format,
            "X-Timeout": str(timeout),
        }
        if os.getenv("JINA_API_KEY"):
            headers["Authorization"] = f"Bearer {os.getenv('JINA_API_KEY')}"
        elif not _api_key_warned:
            _api_key_warned = True
            logger.warning("Jina API key is not set. Provide your own key to access a higher rate limit. See https://jina.ai/reader for more information.")
        data = {"url": url}
        proxies = _get_proxies()
        try:
            proxy = None
            if proxies:
                # httpx uses a single proxy URL or a dict with http/https keys
                proxy = proxies.get("https") or proxies.get("http")
            async with httpx.AsyncClient(proxy=proxy) as client:
                response = await client.post("https://r.jina.ai/", headers=headers, json=data, timeout=timeout)

            if response.status_code != 200:
                error_message = f"Jina API returned status {response.status_code}: {response.text}"
                logger.error(error_message)
                return f"Error: {error_message}"

            if not response.text or not response.text.strip():
                error_message = "Jina API returned empty response"
                logger.error(error_message)
                return f"Error: {error_message}"

            return response.text
        except Exception as e:
            error_message = f"Request to Jina API failed: {str(e)}"
            logger.exception(error_message)
            return f"Error: {error_message}"

"""Web Fetch tool using Crawl4AI for JavaScript-heavy pages."""

import logging

from langchain.tools import tool

from deerflow.config import get_app_config, get_proxy_config

logger = logging.getLogger(__name__)

# Lazy import to avoid loading crawl4ai at startup
_crawl4ai = None


def _get_crawl4ai():
    """Lazy load Crawl4AI to avoid startup overhead."""
    global _crawl4ai
    if _crawl4ai is None:
        try:
            from crawl4ai import AsyncWebCrawler

            # Check for proxy configuration
            proxy_config = get_proxy_config()
            proxy_settings = None
            if proxy_config and proxy_config.is_enabled():
                proxies = proxy_config.get_proxies_dict()
                # Crawl4AI uses a single proxy URL
                proxy_url = proxies.get("https") or proxies.get("http")
                if proxy_url:
                    proxy_settings = proxy_url
                    logger.info(f"Crawl4AI using proxy: {proxy_url}")

            _crawl4ai = AsyncWebCrawler(proxy=proxy_settings)
        except ImportError:
            logger.error("crawl4ai not installed. Run: pip install crawl4ai")
            return None
    return _crawl4ai


@tool("crawl4ai_fetch", parse_docstring=True)
def crawl4ai_fetch_tool(url: str) -> str:
    """Fetch and extract content from web pages using Crawl4AI.

    Use this tool as a fallback when web_fetch fails or for JavaScript-heavy pages
    that require browser rendering. This tool is slower but more powerful than
    Jina Reader or Tavily.

    Args:
        url: The URL to fetch. Must include the schema (https://example.com).
    """
    import asyncio

    crawler = _get_crawl4ai()
    if crawler is None:
        return "Error: crawl4ai not installed. Run: pip install crawl4ai"

    async def _fetch():
        try:
            result = await crawler.arun(url=url)

            if result.success and result.markdown:
                content = result.markdown
                title = result.metadata.get("title", "Untitled") if result.metadata else "Untitled"
                return f"# {title}\n\n{content[:8192]}"
            else:
                error_msg = result.error_message if hasattr(result, "error_message") and result.error_message else "Unknown error"
                return f"Error: Crawl4AI failed: {error_msg}"

        except Exception as e:
            logger.error(f"Crawl4AI fetch failed: {e}")
            return f"Error: {str(e)}"

    # Run async function in event loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # If we're already in an async context, create a new loop
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _fetch())
            return future.result()
    else:
        return asyncio.run(_fetch())
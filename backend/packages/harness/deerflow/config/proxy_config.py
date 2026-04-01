"""Proxy configuration for HTTP clients."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field


class ProxyConfig(BaseModel):
    """Configuration for HTTP proxy settings.

    This configuration is used by web tools (web_search, web_fetch, image_search)
    to route HTTP requests through a proxy server.
    """

    model_config = ConfigDict(extra="allow", frozen=False)

    http: str | None = Field(default=None, description="HTTP proxy URL (e.g., http://proxy.example.com:8080)")
    https: str | None = Field(default=None, description="HTTPS proxy URL (e.g., http://proxy.example.com:8080)")

    # Proxy authentication (optional)
    username: str | None = Field(default=None, description="Proxy authentication username")
    password: str | None = Field(default=None, description="Proxy authentication password")

    def is_enabled(self) -> bool:
        """Check if proxy is configured."""
        return self.http is not None or self.https is not None

    def get_proxies_dict(self) -> dict[str, str]:
        """Get a proxies dictionary compatible with requests library.

        Returns:
            Dict with 'http' and 'https' keys pointing to proxy URLs.
            If authentication is configured, URLs will include credentials.

        Example:
            >>> config = ProxyConfig(http="http://proxy.example.com:8080", https="http://proxy.example.com:8080")
            >>> config.get_proxies_dict()
            {'http': 'http://proxy.example.com:8080', 'https': 'http://proxy.example.com:8080'}
        """
        proxies = {}

        if self.http:
            proxies["http"] = self._build_proxy_url(self.http)

        if self.https:
            proxies["https"] = self._build_proxy_url(self.https)

        return proxies

    def _build_proxy_url(self, base_url: str) -> str:
        """Build proxy URL with authentication if configured.

        Args:
            base_url: The base proxy URL.

        Returns:
            Proxy URL with embedded authentication if username/password are set.
        """
        if not self.username or not self.password:
            return base_url

        # Parse the URL and inject authentication
        # Format: http://username:password@proxy.example.com:8080
        import re

        # Match URL pattern: protocol://host:port or protocol://host
        match = re.match(r"(https?://)(.+)", base_url)
        if match:
            protocol = match.group(1)
            host_port = match.group(2)
            return f"{protocol}{self.username}:{self.password}@{host_port}"

        return base_url


# Module-level cached config
_proxy_config: ProxyConfig | None = None


def load_proxy_config_from_dict(config_data: dict) -> ProxyConfig:
    """Load proxy configuration from a dictionary.

    Args:
        config_data: Dictionary containing proxy configuration.

    Returns:
        ProxyConfig instance.
    """
    global _proxy_config
    _proxy_config = ProxyConfig.model_validate(config_data)
    return _proxy_config


def get_proxy_config() -> ProxyConfig | None:
    """Get the cached proxy configuration.

    Returns:
        ProxyConfig instance if configured, None otherwise.
    """
    return _proxy_config
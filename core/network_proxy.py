"""统一管理应用网络请求的代理策略。"""

import os
import re
import urllib.request
from urllib.parse import urlparse

import requests


PROXY_MODE_DIRECT = "direct"
PROXY_MODE_SYSTEM = "system"
PROXY_MODE_CUSTOM = "custom"
PROXY_MODES = (PROXY_MODE_DIRECT, PROXY_MODE_SYSTEM, PROXY_MODE_CUSTOM)

PROXY_SCOPE_AI = "ai"
PROXY_SCOPE_FOFA = "fofa"
PROXY_SCOPE_ASSET_SEARCH = "asset_search"
PROXY_SCOPE_SCAN = "scan"
PROXY_SCOPE_ONLINE_RESOURCES = "online_resources"
PROXY_SCOPE_UPDATE = "update"
PROXY_SCOPES = (
    PROXY_SCOPE_AI,
    PROXY_SCOPE_FOFA,
    PROXY_SCOPE_ASSET_SEARCH,
    PROXY_SCOPE_SCAN,
    PROXY_SCOPE_ONLINE_RESOURCES,
    PROXY_SCOPE_UPDATE,
)

DEFAULT_PROXY_MODES = {
    PROXY_SCOPE_AI: PROXY_MODE_DIRECT,
    PROXY_SCOPE_FOFA: PROXY_MODE_DIRECT,
    PROXY_SCOPE_ASSET_SEARCH: PROXY_MODE_DIRECT,
    PROXY_SCOPE_SCAN: PROXY_MODE_DIRECT,
    PROXY_SCOPE_ONLINE_RESOURCES: PROXY_MODE_SYSTEM,
    PROXY_SCOPE_UPDATE: PROXY_MODE_SYSTEM,
}

_PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
)

_URL_CREDENTIAL_PATTERN = re.compile(r"(?P<scheme>https?://)[^/@\s]+@", re.IGNORECASE)


def normalize_proxy_scope(scope):
    scope = str(scope or "").strip()
    if scope not in PROXY_SCOPES:
        raise ValueError(f"Unsupported proxy scope: {scope}")
    return scope


def normalize_proxy_mode(mode):
    mode = str(mode or PROXY_MODE_DIRECT).strip().lower()
    return mode if mode in PROXY_MODES else PROXY_MODE_DIRECT


def normalize_proxy_url(proxy_url):
    """Validate and normalize an HTTP(S) proxy URL without logging credentials."""
    value = str(proxy_url or "").strip()
    if not value:
        return ""
    if any(char.isspace() for char in value):
        raise ValueError("Proxy URL must not contain whitespace")

    parsed = urlparse(value if "://" in value else f"http://{value}")
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError("Proxy URL must use http:// or https://")
    if not parsed.hostname:
        raise ValueError("Proxy URL must include a host")
    try:
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError("Proxy URL port must be between 1 and 65535")
    except ValueError as error:
        raise ValueError("Proxy URL contains an invalid port") from error
    if parsed.path not in ("", "/") or parsed.params or parsed.query or parsed.fragment:
        raise ValueError("Proxy URL must contain only scheme, credentials, host and port")

    normalized = value if "://" in value else f"http://{value}"
    return normalized.rstrip("/")


def proxy_mapping(proxy_url):
    proxy_url = normalize_proxy_url(proxy_url)
    if not proxy_url:
        return {}
    return {"http": proxy_url, "https": proxy_url}


def redact_proxy_credentials(value):
    """Remove URL user information before an error reaches UI or logs."""
    return _URL_CREDENTIAL_PATTERN.sub(r"\g<scheme>***:***@", str(value))


def get_proxy_config(scope, settings=None):
    """Load one proxy configuration from SettingsManager."""
    scope = normalize_proxy_scope(scope)
    if settings is None:
        from core.settings_manager import get_settings

        settings = get_settings()
    return settings.get_proxy_config(scope)


def create_session(scope, settings=None, headers=None):
    """Create a Requests session with explicit proxy inheritance semantics."""
    config = get_proxy_config(scope, settings=settings)
    session = requests.Session()
    session.trust_env = config["mode"] == PROXY_MODE_SYSTEM
    if config["mode"] == PROXY_MODE_CUSTOM:
        session.proxies.update(proxy_mapping(config["url"]))
    if headers:
        session.headers.update(headers)
    return session


def _system_proxy_environment():
    """Read environment/OS proxy settings before sanitizing a child environment."""
    try:
        discovered = urllib.request.getproxies()
    except Exception:
        discovered = {}

    system_env = {}
    for scheme in ("http", "https"):
        value = discovered.get(scheme) or discovered.get("all")
        if value:
            system_env[f"{scheme.upper()}_PROXY"] = value
    no_proxy = discovered.get("no") or discovered.get("no_proxy")
    if no_proxy:
        system_env["NO_PROXY"] = no_proxy
    return system_env


def build_subprocess_environment(scope, settings=None, base_env=None):
    """Build a child-process environment that follows the selected proxy mode."""
    config = get_proxy_config(scope, settings=settings)
    environment = dict(os.environ if base_env is None else base_env)

    system_environment = _system_proxy_environment()
    for key in _PROXY_ENV_KEYS:
        environment.pop(key, None)

    if config["mode"] == PROXY_MODE_SYSTEM:
        environment.update(system_environment)
    elif config["mode"] == PROXY_MODE_CUSTOM:
        custom = proxy_mapping(config["url"])
        environment["HTTP_PROXY"] = custom["http"]
        environment["HTTPS_PROXY"] = custom["https"]
    else:
        # Some HTTP libraries only honor NO_PROXY when they are given an env proxy.
        environment["NO_PROXY"] = "*"
        environment["no_proxy"] = "*"

    return environment

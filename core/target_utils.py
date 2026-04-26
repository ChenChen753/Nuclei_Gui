from urllib.parse import urlsplit, urlunsplit


def normalize_target(target):
    """Return a stable target URL used for display, queueing, and scanning."""
    if not isinstance(target, str):
        return ""

    target = target.strip()
    if not target:
        return ""

    if not target.lower().startswith(("http://", "https://")):
        target = "http://" + target

    parts = urlsplit(target)
    if not parts.scheme or not parts.netloc:
        return target

    scheme = parts.scheme.lower()
    hostname = parts.hostname
    if not hostname:
        return target

    try:
        port = parts.port
    except ValueError:
        return target

    host = hostname.lower()
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"

    userinfo = ""
    if parts.username:
        userinfo = parts.username
        if parts.password is not None:
            userinfo += f":{parts.password}"
        userinfo += "@"

    is_default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    port_suffix = "" if port is None or is_default_port else f":{port}"
    netloc = f"{userinfo}{host}{port_suffix}"
    path = "" if parts.path == "/" else parts.path

    return urlunsplit((scheme, netloc, path, parts.query, parts.fragment))


def dedupe_targets(targets):
    """Normalize targets and remove duplicates while preserving input order."""
    unique_targets = []
    seen = set()

    for target in targets or []:
        normalized = normalize_target(target)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_targets.append(normalized)

    return unique_targets


def parse_targets_text(text):
    """Parse multiline target text into normalized, deduplicated targets."""
    return dedupe_targets((text or "").splitlines())
